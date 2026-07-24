#!/usr/bin/env python3
"""独立校验 Starcat 公开 `.xcloc` 语言包。

这个脚本只依赖 Python 标准库，因此 GitHub Actions 和贡献者本机可以得到
同一份结论。它验证的不只是 JSON/XML 能否解析，还包括 manifest、source
snapshot、key 集合、翻译状态、占位符与发布门禁。

`draft` 语言允许不完整，`released` 语言必须没有缺失或待复核文案。这样可以
提前创建 18 个协作入口，同时避免把尚未审核的机器翻译误标为正式支持。
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, NamedTuple


PACKAGE_DIR_NAME = "Translation Packages"
MANIFEST_NAME = "locales.json"
NONTRANSLATABLE_NAME = "nontranslatable-keys.json"
XLIFF_NAMESPACE = "urn:oasis:names:tc:xliff:document:1.2"

CONFIRMED_LOCALES = (
    "en",
    "zh-Hans",
    "zh-Hant",
    "ja",
    "ko",
    "de",
    "fr",
    "es",
    "pt-BR",
    "it",
    "ru",
    "nl",
    "pl",
    "uk",
    "tr",
    "vi",
    "id",
    "ar",
)
APPROVED_STATES = frozenset({"translated", "final", "signed-off"})
KNOWN_STATES = frozenset(
    {
        "needs-translation",
        "new",
        "needs-review-translation",
        "translated",
        "final",
        "signed-off",
    }
)
PRINTF_TOKEN_RE = re.compile(r"%%|%(?:\d+\$)?(?:lld|ld|@|d|f)")
BRACE_TOKEN_RE = re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
FENCED_CODE_RE = re.compile(
    r"^```([^\n]*)\n.*?^```[ \t]*$",
    re.DOTALL | re.MULTILINE,
)
INLINE_CODE_RE = re.compile(r"(?<!`)`[^`\n]+`(?!`)")
URL_TOKEN_RE = re.compile(
    r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]*"
)


class TranslationUnit(NamedTuple):
    """一个 XLIFF trans-unit 的最小校验数据。"""

    source: str
    target: str
    state: str


class LocaleReport(NamedTuple):
    """单个语言包的完成度与发布状态。"""

    locale: str
    total: int
    translated: int
    review: int
    missing: int
    excluded: int
    completion: float
    release_status: str


class ValidationResult(NamedTuple):
    """整仓校验结果；errors 非空时 CLI 以失败状态退出。"""

    reports: dict[str, LocaleReport]
    errors: list[str]


def load_json(path: Path) -> dict[str, Any]:
    """读取 JSON object，并把格式错误转换为可操作的校验消息。"""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"缺少文件：{path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON 无效：{path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"JSON 顶层必须是 object：{path}")
    return payload


def load_manifest(root: Path) -> tuple[str, list[dict[str, Any]]]:
    """读取并验证 locale manifest 的最小交换契约。"""

    manifest = load_json(root / MANIFEST_NAME)
    source_locale = manifest.get("sourceLocale")
    locales = manifest.get("locales")
    if not isinstance(source_locale, str) or not source_locale:
        raise ValueError(f"{MANIFEST_NAME} 缺少 sourceLocale")
    if not isinstance(locales, list) or not locales:
        raise ValueError(f"{MANIFEST_NAME} 缺少 locales")

    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for item in locales:
        if not isinstance(item, dict):
            raise ValueError(f"{MANIFEST_NAME} locales 项必须是 object")
        locale = item.get("id")
        release_status = item.get("releaseStatus")
        direction = item.get("direction")
        if not isinstance(locale, str) or not locale:
            raise ValueError(f"{MANIFEST_NAME} locale 缺少 id")
        if locale in seen:
            raise ValueError(f"{MANIFEST_NAME} locale 重复：{locale}")
        if release_status not in {"draft", "released"}:
            raise ValueError(f"{locale} releaseStatus 必须是 draft 或 released")
        if direction not in {"ltr", "rtl"}:
            raise ValueError(f"{locale} direction 必须是 ltr 或 rtl")
        seen.add(locale)
        normalized.append(item)
    if source_locale not in seen:
        raise ValueError(f"sourceLocale {source_locale} 不在 locales 中")
    return source_locale, normalized


def load_exclusions(root: Path) -> dict[str, str]:
    """读取不可翻译 key；无理由的条目会削弱审计可信度，因此直接拒绝。"""

    payload = load_json(root / NONTRANSLATABLE_NAME)
    keys = payload.get("keys")
    if not isinstance(keys, dict):
        raise ValueError(f"{NONTRANSLATABLE_NAME} 缺少 keys object")
    exclusions: dict[str, str] = {}
    for key, reason in keys.items():
        if not isinstance(key, str) or not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{NONTRANSLATABLE_NAME} 每个 key 都必须有非空理由")
        exclusions[key] = reason
    return exclusions


def package_paths(root: Path) -> dict[str, Path]:
    """按目录名提取 locale，避免悄悄接纳嵌套或非 `.xcloc` 目录。"""

    package_root = root / PACKAGE_DIR_NAME
    if not package_root.is_dir():
        return {}
    return {
        path.name[: -len(".xcloc")]: path
        for path in package_root.iterdir()
        if path.is_dir() and path.name.endswith(".xcloc")
    }


def read_units(path: Path, locale: str) -> tuple[str, str, dict[str, TranslationUnit], list[str]]:
    """读取 XLIFF，并单独返回重复 key，避免 dict 覆盖掩盖结构损坏。"""

    xliff_path = path / "Localized Contents" / f"{locale}.xliff"
    try:
        tree = ET.parse(xliff_path)
    except FileNotFoundError as error:
        raise ValueError(f"缺少文件：{xliff_path}") from error
    except ET.ParseError as error:
        raise ValueError(f"XLIFF 无效：{xliff_path}: {error}") from error

    namespace = {"x": XLIFF_NAMESPACE}
    file_node = tree.find(".//x:file", namespace)
    if file_node is None:
        raise ValueError(f"{locale} XLIFF 缺少 file 节点")

    units: dict[str, TranslationUnit] = {}
    duplicates: list[str] = []
    for node in tree.findall(".//x:trans-unit", namespace):
        key = node.get("id")
        if not key:
            raise ValueError(f"{locale} XLIFF 存在无 id 的 trans-unit")
        if key in units:
            duplicates.append(key)
            continue
        source = node.find("x:source", namespace)
        target = node.find("x:target", namespace)
        state = target.get("state", "") if target is not None else ""
        if state not in KNOWN_STATES:
            raise ValueError(f"{locale}:{key} 翻译状态无效：{state or '<empty>'}")
        units[key] = TranslationUnit(
            source=source.text or "" if source is not None else "",
            target=target.text or "" if target is not None else "",
            state=state,
        )
    return (
        file_node.get("source-language", ""),
        file_node.get("target-language", ""),
        units,
        duplicates,
    )


def token_signature(text: str) -> tuple[list[str], collections.Counter[str]]:
    """比较占位符集合，并保留非位置参数顺序以防翻译后崩溃。"""

    printf_tokens = PRINTF_TOKEN_RE.findall(text)
    brace_tokens = BRACE_TOKEN_RE.findall(text)
    non_positional = [token for token in printf_tokens if "$" not in token]
    return non_positional, collections.Counter(printf_tokens + brace_tokens)


def placeholder_error(source: str, target: str) -> str | None:
    """允许位置参数重排，但不允许丢失、增加或重排普通 printf 参数。"""

    source_order, source_tokens = token_signature(source)
    target_order, target_tokens = token_signature(target)
    if source_tokens != target_tokens:
        return f"token 集合不一致：source={dict(source_tokens)} target={dict(target_tokens)}"
    if source_order != target_order:
        return f"非位置参数顺序不一致：source={source_order} target={target_order}"
    return None


def protected_literal_signature(
    text: str,
) -> tuple[list[str], list[str], list[str]]:
    """提取必须原样保留的可执行代码块、行内代码和 ASCII URL。"""

    return (
        [
            match.group(0)
            for match in FENCED_CODE_RE.finditer(text)
            if match.group(1).strip().lower() != "text"
        ],
        INLINE_CODE_RE.findall(text),
        [
            token.rstrip(".,;!?)]}")
            for token in URL_TOKEN_RE.findall(text)
        ],
    )


def protected_literal_error(source: str, target: str) -> str | None:
    """技术字面量必须保持内容、数量和出现顺序一致。"""

    source_signature = protected_literal_signature(source)
    target_signature = protected_literal_signature(target)
    labels = ("Markdown 代码块", "行内代码", "URL")
    for label, source_tokens, target_tokens in zip(
        labels,
        source_signature,
        target_signature,
    ):
        if source_tokens != target_tokens:
            return (
                f"{label} 不一致：source={source_tokens[:3]} "
                f"target={target_tokens[:3]}"
            )
    return None


def validate_repository(
    root: Path,
    *,
    enforce_confirmed_locales: bool = False,
) -> ValidationResult:
    """校验仓库；单元测试可使用小 manifest，CLI 则强制产品确认的 18 种语言。"""

    errors: list[str] = []
    reports: dict[str, LocaleReport] = {}
    try:
        source_locale, locales = load_manifest(root)
        exclusions = load_exclusions(root)
    except (OSError, ValueError) as error:
        return ValidationResult(reports, [str(error)])

    manifest_ids = [item["id"] for item in locales]
    if enforce_confirmed_locales and tuple(manifest_ids) != CONFIRMED_LOCALES:
        errors.append(
            "locales.json 必须按确认顺序包含 18 种语言："
            + ", ".join(CONFIRMED_LOCALES)
        )

    packages = package_paths(root)
    missing_packages = sorted(set(manifest_ids) - set(packages))
    extra_packages = sorted(set(packages) - set(manifest_ids))
    if missing_packages:
        errors.append("缺少语言包：" + ", ".join(missing_packages))
    if extra_packages:
        errors.append("存在 manifest 外语言包：" + ", ".join(extra_packages))

    source_snapshot: str | None = None
    catalog_keys: set[str] | None = None
    for item in locales:
        locale = item["id"]
        package = packages.get(locale)
        if package is None:
            continue
        try:
            contents = load_json(package / "contents.json")
            if contents.get("targetLocale") != locale:
                errors.append(
                    f"{locale} contents.json targetLocale 不一致："
                    f"{contents.get('targetLocale')!r}"
                )

            catalog_path = (
                package
                / "Source Contents"
                / "Starcat"
                / "Localizable"
                / "Localizable.xcstrings"
            )
            embedded_text = catalog_path.read_text(encoding="utf-8")
            catalog = load_json(catalog_path)
            strings = catalog.get("strings")
            if not isinstance(strings, dict):
                raise ValueError(f"{locale} source snapshot 缺少 strings object")
            if catalog.get("sourceLanguage") != source_locale:
                errors.append(
                    f"{locale} source snapshot sourceLanguage 与 manifest 不一致"
                )
            if source_snapshot is None:
                source_snapshot = embedded_text
                catalog_keys = set(strings)
            elif embedded_text != source_snapshot:
                errors.append(f"{locale} source snapshot 与其他语言包不一致")

            xliff_source, xliff_target, units, duplicates = read_units(package, locale)
            if xliff_source != source_locale:
                errors.append(
                    f"{locale} XLIFF source-language 不一致：{xliff_source!r}"
                )
            if xliff_target != locale:
                errors.append(
                    f"{locale} XLIFF target-language 不一致：{xliff_target!r}"
                )
            if duplicates:
                errors.append(f"{locale} XLIFF 重复 key：" + ", ".join(sorted(duplicates)))
            expected_keys = catalog_keys or set()
            missing_keys = sorted(expected_keys - set(units))
            unknown_keys = sorted(set(units) - expected_keys)
            if missing_keys:
                errors.append(
                    f"{locale} XLIFF 缺少 key："
                    + ", ".join(missing_keys[:10])
                    + (" ..." if len(missing_keys) > 10 else "")
                )
            if unknown_keys:
                errors.append(
                    f"{locale} XLIFF 存在未知 key："
                    + ", ".join(unknown_keys[:10])
                    + (" ..." if len(unknown_keys) > 10 else "")
                )
        except (OSError, ValueError) as error:
            errors.append(str(error))
            continue

        translated = 0
        review = 0
        missing = 0
        excluded = 0
        for key in sorted(expected_keys):
            if key in exclusions:
                excluded += 1
                continue
            unit = units.get(key)
            if unit is None or not unit.target or unit.state in {"needs-translation", "new"}:
                missing += 1
                continue
            if unit.state == "needs-review-translation":
                review += 1
            elif unit.state in APPROVED_STATES:
                translated += 1
            else:
                review += 1
            token_error = placeholder_error(unit.source, unit.target)
            if token_error:
                errors.append(f"{locale}:{key} 占位符错误：{token_error}")
            literal_error = protected_literal_error(unit.source, unit.target)
            if literal_error:
                errors.append(
                    f"{locale}:{key} 受保护字面量错误：{literal_error}"
                )

        denominator = max(1, len(expected_keys) - excluded)
        report = LocaleReport(
            locale=locale,
            total=len(expected_keys),
            translated=translated,
            review=review,
            missing=missing,
            excluded=excluded,
            completion=translated / denominator * 100,
            release_status=item["releaseStatus"],
        )
        reports[locale] = report
        if item["releaseStatus"] == "released" and (review or missing):
            errors.append(
                f"released locale {locale} 仍有 review={review}, missing={missing}"
            )

    if catalog_keys is not None:
        stale_exclusions = sorted(set(exclusions) - catalog_keys)
        if stale_exclusions:
            errors.append(
                "stale nontranslatable key："
                + ", ".join(stale_exclusions[:10])
                + (" ..." if len(stale_exclusions) > 10 else "")
            )
    return ValidationResult(reports, errors)


def print_result(result: ValidationResult) -> None:
    """输出适合本地终端和 GitHub Actions 日志阅读的紧凑表格。"""

    print(
        f"{'locale':<9} {'status':<8} {'translated':>10} "
        f"{'review':>7} {'missing':>8} {'excluded':>9} {'completion':>11}"
    )
    for report in result.reports.values():
        print(
            f"{report.locale:<9} {report.release_status:<8} "
            f"{report.translated:>10} {report.review:>7} "
            f"{report.missing:>8} {report.excluded:>9} "
            f"{report.completion:>10.2f}%"
        )
    if result.errors:
        print("\n校验失败：", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
    else:
        print(f"\n校验通过：{len(result.reports)} 个语言包")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="starcat-localization 仓库根目录",
    )
    args = parser.parse_args()
    result = validate_repository(args.root, enforce_confirmed_locales=True)
    print_result(result)
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
