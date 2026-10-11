#!/usr/bin/env python3
"""为单个 Starcat `.xcloc` 生成可续跑的 AI 翻译初稿。

脚本刻意只写入 `needs-review-translation`，不会把 AI 输出标成已审核。默认
dry-run；显式传入 `--apply` 后才调用 OpenAI-compatible API 并修改 XLIFF。

示例：

    python3 scripts/translate_draft.py --locale zh-Hant
    python3 scripts/translate_draft.py --locale zh-Hant --limit 40 --apply
    python3 scripts/translate_draft.py --locale zh-Hant --apply
    python3 scripts/translate_draft.py --locale zh-Hant \
      --repair-protected-literals --apply

API Key 只从指定环境变量读取，不写入仓库、日志或请求正文。
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


XLIFF_NAMESPACE = "urn:oasis:names:tc:xliff:document:1.2"
NONTRANSLATABLE_NAME = "nontranslatable-keys.json"
APPROVED_STATES = frozenset({"translated", "final", "signed-off"})
TRANSLATABLE_STATES = frozenset(
    {"needs-translation", "new", "needs-review-translation"}
)
PRINTF_TOKEN_RE = re.compile(r"%%|%(?:\d+\$)?(?:lld|ld|@|d|f)")
BRACE_TOKEN_RE = re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
FENCED_CODE_RE = re.compile(
    r"^```([^\n]*)\n.*?^```[ \t]*$",
    re.DOTALL | re.MULTILINE,
)
INLINE_CODE_RE = re.compile(r"(?<!`)`[^`\n]+`(?!`)")
INLINE_MASK_RE = re.compile(r"⟦SC_INLINE_\d{4}⟧")
URL_TOKEN_RE = re.compile(
    r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]*"
)

LOCALE_NAMES = {
    "zh-Hant": "Traditional Chinese (繁體中文)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "de": "German (Deutsch)",
    "fr": "French (Français)",
    "es": "Spanish (Español)",
    "pt-BR": "Brazilian Portuguese (Português do Brasil)",
    "it": "Italian (Italiano)",
    "ru": "Russian (Русский)",
    "nl": "Dutch (Nederlands)",
    "pl": "Polish (Polski)",
    "uk": "Ukrainian (Українська)",
    "tr": "Turkish (Türkçe)",
    "vi": "Vietnamese (Tiếng Việt)",
    "id": "Indonesian (Bahasa Indonesia)",
    "ar": "Arabic (العربية)",
}


class TranslationError(RuntimeError):
    """表示 AI 响应不满足 XLIFF 安全写入契约。"""


class TranslationUnit:
    """保留 XLIFF 节点引用，验证通过后才原位写入 target。"""

    def __init__(
        self,
        *,
        key: str,
        source: str,
        note: str,
        reference: str,
        target_node: ET.Element,
    ) -> None:
        self.key = key
        self.source = source
        self.note = note
        self.reference = reference
        self.target_node = target_node


class TranslationDocument:
    """一个 locale 的 XLIFF 树、候选单元和原子保存路径。"""

    def __init__(
        self,
        *,
        locale: str,
        path: Path,
        tree: ET.ElementTree,
        units: dict[str, TranslationUnit],
        pending_units: list[TranslationUnit],
    ) -> None:
        self.locale = locale
        self.path = path
        self.tree = tree
        self.units = units
        self.pending_units = pending_units


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise TranslationError(f"缺少文件：{path}") from error
    except json.JSONDecodeError as error:
        raise TranslationError(f"JSON 无效：{path}: {error}") from error
    if not isinstance(payload, dict):
        raise TranslationError(f"JSON 顶层必须是 object：{path}")
    return payload


def load_exclusions(root: Path) -> set[str]:
    payload = load_json(root / NONTRANSLATABLE_NAME)
    keys = payload.get("keys")
    if not isinstance(keys, dict):
        raise TranslationError(f"{NONTRANSLATABLE_NAME} 缺少 keys object")
    return {key for key in keys if isinstance(key, str)}


def load_reference_values(package: Path, locale: str) -> dict[str, str]:
    """繁中优先参考已有简中译文；其他语言只使用英文 source 和 note。"""

    if locale != "zh-Hant":
        return {}
    catalog_path = (
        package
        / "Source Contents"
        / "Starcat"
        / "Localizable"
        / "Localizable.xcstrings"
    )
    catalog = load_json(catalog_path)
    strings = catalog.get("strings")
    if not isinstance(strings, dict):
        raise TranslationError(f"source snapshot 缺少 strings：{catalog_path}")
    references: dict[str, str] = {}
    for key, entry in strings.items():
        if not isinstance(entry, dict):
            continue
        localizations = entry.get("localizations")
        if not isinstance(localizations, dict):
            continue
        simplified = localizations.get("zh-Hans")
        if not isinstance(simplified, dict):
            continue
        string_unit = simplified.get("stringUnit")
        if not isinstance(string_unit, dict):
            continue
        value = string_unit.get("value")
        if isinstance(value, str) and value:
            references[key] = value
    return references


def load_document(
    root: Path,
    locale: str,
    *,
    limit: int | None = None,
    repair_protected_literals: bool = False,
    requested_keys: set[str] | None = None,
) -> TranslationDocument:
    """读取 locale 包，按普通初稿或受保护字面量修复模式筛选候选。"""

    package = root / "Translation Packages" / f"{locale}.xcloc"
    path = package / "Localized Contents" / f"{locale}.xliff"
    try:
        tree = ET.parse(path)
    except FileNotFoundError as error:
        raise TranslationError(f"缺少 XLIFF：{path}") from error
    except ET.ParseError as error:
        raise TranslationError(f"XLIFF 无效：{path}: {error}") from error

    exclusions = load_exclusions(root)
    references = load_reference_values(package, locale)
    namespace = {"x": XLIFF_NAMESPACE}
    file_node = tree.find(".//x:file", namespace)
    if file_node is None:
        raise TranslationError(f"{locale} XLIFF 缺少 file 节点")
    if file_node.get("target-language") != locale:
        raise TranslationError(
            f"{locale} XLIFF target-language 不一致："
            f"{file_node.get('target-language')!r}"
        )

    units: dict[str, TranslationUnit] = {}
    pending: list[TranslationUnit] = []
    for node in tree.findall(".//x:trans-unit", namespace):
        key = node.get("id")
        source_node = node.find("x:source", namespace)
        target_node = node.find("x:target", namespace)
        note_node = node.find("x:note", namespace)
        if not key or source_node is None or target_node is None:
            raise TranslationError(f"{locale} XLIFF 存在不完整 trans-unit")
        if key in units:
            raise TranslationError(f"{locale} XLIFF 重复 key：{key}")
        unit = TranslationUnit(
            key=key,
            source=source_node.text or "",
            note=note_node.text or "" if note_node is not None else "",
            reference=references.get(key, ""),
            target_node=target_node,
        )
        units[key] = unit

        state = target_node.get("state", "needs-translation")
        target = target_node.text or ""
        is_ai_review_target = (
            key not in exclusions
            and bool(target)
            and state == "needs-review-translation"
            and protected_literal_error(unit.source, target) is not None
        )
        is_empty_draft_target = (
            key not in exclusions
            and not target
            and state in TRANSLATABLE_STATES
            and state not in APPROVED_STATES
        )
        is_requested_target = (
            requested_keys is not None
            and key in requested_keys
            and key not in exclusions
            and (
                is_empty_draft_target
                or (bool(target) and state == "needs-review-translation")
            )
        )
        if requested_keys is not None:
            # 定向重跑既用于修订 AI 初稿，也用于把超长单元从普通批次中隔离出来。
            is_pending = is_requested_target
        elif repair_protected_literals:
            is_pending = is_ai_review_target
        else:
            is_pending = is_empty_draft_target
        if is_pending:
            pending.append(unit)

    if requested_keys is not None:
        selected_keys = {unit.key for unit in pending}
        unavailable = sorted(requested_keys - selected_keys)
        if unavailable:
            raise TranslationError(
                "指定 key 不存在、已审核或不可生成 AI 初稿："
                + ", ".join(unavailable)
            )
    if limit is not None:
        pending = pending[:limit]
    return TranslationDocument(
        locale=locale,
        path=path,
        tree=tree,
        units=units,
        pending_units=pending,
    )


def token_signature(text: str) -> tuple[list[str], collections.Counter[str]]:
    printf_tokens = PRINTF_TOKEN_RE.findall(text)
    brace_tokens = BRACE_TOKEN_RE.findall(text)
    non_positional = [token for token in printf_tokens if "$" not in token]
    return non_positional, collections.Counter(printf_tokens + brace_tokens)


def placeholder_error(source: str, target: str) -> str | None:
    """允许位置参数重排，但普通 printf 参数的顺序也必须保持。"""

    source_order, source_tokens = token_signature(source)
    target_order, target_tokens = token_signature(target)
    if source_tokens != target_tokens:
        return f"token 集合不一致：source={dict(source_tokens)} target={dict(target_tokens)}"
    if source_order != target_order:
        return f"非位置参数顺序不一致：source={source_order} target={target_order}"
    return None


def url_tokens(text: str) -> list[str]:
    """提取 ASCII URL，避免把紧随其后的中日韩文字误当成 URL 路径。"""

    return [
        token.rstrip(".,;!?)]}")
        for token in URL_TOKEN_RE.findall(text)
    ]


def executable_fenced_code_blocks(text: str) -> list[str]:
    """先配对完整 fence，再排除允许翻译说明文字的 ```text 块。"""

    return [
        match.group(0)
        for match in FENCED_CODE_RE.finditer(text)
        if match.group(1).strip().lower() != "text"
    ]


def protected_literal_signature(
    text: str,
) -> tuple[list[str], list[str], list[str]]:
    """可执行代码块、行内代码和 URL 必须逐项原样保留。"""

    return (
        executable_fenced_code_blocks(text),
        INLINE_CODE_RE.findall(text),
        url_tokens(text),
    )


def protected_literal_error(source: str, target: str) -> str | None:
    """返回首个受保护字面量差异；列表比较同时约束内容、数量和顺序。"""

    source_signature = protected_literal_signature(source)
    target_signature = protected_literal_signature(target)
    labels = ("Markdown 代码块", "行内代码", "URL")
    for label, source_tokens, target_tokens in zip(
        labels,
        source_signature,
        target_signature,
    ):
        if source_tokens != target_tokens:
            shared_count = min(len(source_tokens), len(target_tokens))
            first_difference = next(
                (
                    index
                    for index in range(shared_count)
                    if source_tokens[index] != target_tokens[index]
                ),
                shared_count,
            )
            source_value = (
                source_tokens[first_difference]
                if first_difference < len(source_tokens)
                else "<missing>"
            )
            target_value = (
                target_tokens[first_difference]
                if first_difference < len(target_tokens)
                else "<missing>"
            )
            return (
                f"{label} 不一致：source_count={len(source_tokens)} "
                f"target_count={len(target_tokens)} first_diff[{first_difference}]="
                f"source:{source_value!r} target:{target_value!r}"
            )
    return None


def strip_unexpected_inline_code(source: str, target: str) -> str:
    """剥除目标语言额外添加的行内代码标记，保留源文案要求的字面量。

    AI 有时会把普通技术词或占位符自行包进反引号。这里只移除源文案中不存在的
    包装；若源字面量缺失、改写或乱序，规范化后的签名仍不相等，后续硬校验会拒绝。
    """

    source_tokens = INLINE_CODE_RE.findall(source)
    remaining = collections.Counter(source_tokens)
    parts: list[str] = []
    cursor = 0
    for match in INLINE_CODE_RE.finditer(target):
        token = match.group(0)
        parts.append(target[cursor : match.start()])
        if remaining[token] > 0:
            parts.append(token)
            remaining[token] -= 1
        else:
            parts.append(token[1:-1])
        cursor = match.end()
    parts.append(target[cursor:])
    normalized = "".join(parts)

    # 数量相同但顺序错误也不能猜测；返回原文，让严格校验给出明确错误。
    if INLINE_CODE_RE.findall(normalized) != source_tokens:
        return target
    return normalized


def mask_inline_code(text: str) -> tuple[str, tuple[str, ...]]:
    """发送给模型前隐藏行内代码，避免模型改写大小写、变量名或命令参数。"""

    if INLINE_MASK_RE.search(text):
        raise TranslationError("源文案包含保留的行内代码掩码格式")
    literals = tuple(INLINE_CODE_RE.findall(text))
    replacements = iter(
        f"⟦SC_INLINE_{index:04d}⟧" for index in range(len(literals))
    )
    return INLINE_CODE_RE.sub(lambda _: next(replacements), text), literals


def restore_inline_code_mask(text: str, literals: tuple[str, ...]) -> str:
    """仅在掩码数量与顺序完全一致时还原源字面量，不对缺失或乱序做猜测。"""

    expected = [
        f"⟦SC_INLINE_{index:04d}⟧" for index in range(len(literals))
    ]
    actual = INLINE_MASK_RE.findall(text)
    if actual != expected:
        raise TranslationError(
            "AI 响应行内代码掩码不一致："
            f"expected={expected[:3]} actual={actual[:3]} "
            f"expected_count={len(expected)} actual_count={len(actual)}"
        )
    restored = text
    for marker, literal in zip(expected, literals):
        restored = restored.replace(marker, literal, 1)
    return restored


def replace_matches_by_order(
    target: str,
    pattern: re.Pattern[str],
    source_matches: list[str],
    *,
    label: str,
) -> str:
    """按出现顺序恢复字面量；数量不一致时拒绝猜测对应关系。"""

    target_matches = pattern.findall(target)
    if len(target_matches) != len(source_matches):
        raise TranslationError(
            f"{label} 数量不一致，无法自动修复："
            f"source={len(source_matches)} target={len(target_matches)}"
        )
    replacements = iter(source_matches)
    return pattern.sub(lambda _: next(replacements), target)


def replace_executable_fences_by_order(
    target: str,
    source_matches: list[str],
) -> str:
    """恢复可执行 fence，同时保留已经本地化的 ```text 说明块。"""

    target_matches = executable_fenced_code_blocks(target)
    if len(target_matches) != len(source_matches):
        raise TranslationError(
            "Markdown 代码块数量不一致，无法自动修复："
            f"source={len(source_matches)} target={len(target_matches)}"
        )
    replacements = iter(source_matches)

    def replace(match: re.Match[str]) -> str:
        if match.group(1).strip().lower() == "text":
            return match.group(0)
        return next(replacements)

    return FENCED_CODE_RE.sub(replace, target)


def restore_protected_literals(source: str, target: str) -> str:
    """只恢复技术字面量，不重写已经生成的自然语言翻译。"""

    source_fences, source_inline, source_urls = protected_literal_signature(source)
    restored = replace_executable_fences_by_order(
        target,
        source_fences,
    )
    restored = replace_matches_by_order(
        restored,
        INLINE_CODE_RE,
        source_inline,
        label="行内代码",
    )

    # URL 的尾随标点不属于 URL，替换时只覆盖 URL 本体，保留目标语言标点。
    target_urls = url_tokens(restored)
    if len(target_urls) != len(source_urls):
        raise TranslationError(
            "URL 数量不一致，无法自动修复："
            f"source={len(source_urls)} target={len(target_urls)}"
        )
    for target_url, source_url in zip(target_urls, source_urls):
        restored = restored.replace(target_url, source_url, 1)

    error = protected_literal_error(source, restored)
    if error:
        raise TranslationError(f"受保护字面量修复失败：{error}")
    return restored


def apply_translations(
    document: TranslationDocument,
    translations: dict[str, str],
    *,
    expected_units: list[TranslationUnit] | None = None,
) -> None:
    """先验证整批，再写节点，确保坏响应不会留下半批修改。"""

    expected_units = expected_units or document.pending_units
    expected_keys = {unit.key for unit in expected_units}
    if set(translations) != expected_keys:
        missing = sorted(expected_keys - set(translations))
        unknown = sorted(set(translations) - expected_keys)
        raise TranslationError(
            f"AI 响应 key 集合不一致：missing={missing[:5]} unknown={unknown[:5]}"
        )

    normalized: dict[str, str] = {}
    for unit in expected_units:
        target = translations[unit.key]
        if not isinstance(target, str) or not target.strip():
            raise TranslationError(f"{document.locale}:{unit.key} AI target 为空")
        target = target.strip()
        target = strip_unexpected_inline_code(unit.source, target)
        error = placeholder_error(unit.source, target)
        if error:
            raise TranslationError(
                f"{document.locale}:{unit.key} 占位符错误：{error}"
            )
        error = protected_literal_error(unit.source, target)
        if error:
            raise TranslationError(
                f"{document.locale}:{unit.key} 受保护字面量错误：{error}"
            )
        normalized[unit.key] = target

    for unit in expected_units:
        unit.target_node.text = normalized[unit.key]
        # AI 只能生成待审核初稿；人工复核后才能改为 translated/final。
        unit.target_node.set("state", "needs-review-translation")


def save_document(document: TranslationDocument) -> None:
    """同目录原子替换 XLIFF，进程中断不会留下半个 XML。"""

    ET.indent(document.tree.getroot(), space="  ")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{document.path.name}.",
        suffix=".tmp",
        dir=document.path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        os.close(descriptor)
        document.tree.write(
            temporary_path,
            encoding="utf-8",
            xml_declaration=True,
        )
        os.replace(temporary_path, document.path)
    finally:
        temporary_path.unlink(missing_ok=True)


def batch_prompt(locale: str, units: list[TranslationUnit]) -> tuple[str, str]:
    """构造包含 key、source、comment 和繁中参考译文的结构化任务。"""

    language = LOCALE_NAMES.get(locale)
    if language is None:
        raise TranslationError(f"不支持 AI 初稿 locale：{locale}")
    system = f"""
You are a senior macOS localization translator.
Translate Starcat UI strings from English into {language}.
Return only one valid JSON object in this exact shape:
{{"translations":[{{"id":0,"text":"..."}}]}}

Rules:
- Return exactly one item for every input id, with no extra ids.
- Preserve every printf/brace placeholder exactly, including %@, %1$@, %d, %% and {{name}}.
- Inline code is replaced with ordered ⟦SC_INLINE_0000⟧ markers. Preserve every marker exactly and in order; never add a marker.
- Preserve every executable fenced code block and URL byte-for-byte.
- In ```text blocks, translate descriptive prose but preserve identifiers, placeholders and values.
- Keep product names, locale identifiers and technical literals unchanged when appropriate.
- Use natural, concise macOS UI language, not word-for-word translation.
- Use key and note as context; never translate the localization key itself.
- Do not add explanations, Markdown or comments.
- For destructive, privacy, credential and purchase text, preserve the precise safety meaning.
- All output is an AI draft awaiting human review.
""".strip()
    payload: list[dict[str, Any]] = []
    for index, unit in enumerate(units):
        masked_source, source_literals = mask_inline_code(unit.source)
        item: dict[str, Any] = {
            "id": index,
            "key": unit.key,
            "source": masked_source,
        }
        if unit.note:
            item["note"] = unit.note
        if unit.reference:
            masked_reference, reference_literals = mask_inline_code(unit.reference)
            # 已校验的简中参考应与英文拥有同一组技术字面量；不一致时宁可不提供参考。
            if reference_literals == source_literals:
                item["simplifiedChineseReference"] = masked_reference
        payload.append(item)
    user = (
        "Translate the following JSON array. Respond with a JSON object only.\n"
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )
    return system, user


def parse_response(content: str, units: list[TranslationUnit]) -> dict[str, str]:
    """把模型的数字 id 响应还原到真实 key，并拒绝重复/缺失 id。"""

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as error:
        raise TranslationError(f"AI 响应不是有效 JSON：{error}") from error
    if not isinstance(payload, dict) or not isinstance(
        payload.get("translations"), list
    ):
        raise TranslationError("AI 响应缺少 translations array")

    by_id: dict[int, str] = {}
    for item in payload["translations"]:
        if not isinstance(item, dict):
            raise TranslationError("AI translations 项必须是 object")
        identifier = item.get("id")
        text = item.get("text")
        if not isinstance(identifier, int) or not isinstance(text, str):
            raise TranslationError("AI translations 项缺少整数 id 或字符串 text")
        if identifier in by_id:
            raise TranslationError(f"AI 响应重复 id：{identifier}")
        by_id[identifier] = text
    expected_ids = set(range(len(units)))
    if set(by_id) != expected_ids:
        raise TranslationError(
            "AI 响应 id 集合不一致："
            f"missing={sorted(expected_ids - set(by_id))[:5]} "
            f"unknown={sorted(set(by_id) - expected_ids)[:5]}"
        )
    translations: dict[str, str] = {}
    for index, unit in enumerate(units):
        _, literals = mask_inline_code(unit.source)
        translations[unit.key] = restore_inline_code_mask(by_id[index], literals)
    return translations


class DeepSeekClient:
    """最小 OpenAI-compatible HTTP client，不引入额外 Python 依赖。"""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float,
    ) -> None:
        self.api_key = api_key
        self.endpoint = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.timeout = timeout

    def translate(
        self,
        locale: str,
        units: list[TranslationUnit],
    ) -> tuple[dict[str, str], dict[str, int]]:
        system, user = batch_prompt(locale, units)
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "thinking": {"type": "disabled"},
                "temperature": 0.1,
                "max_tokens": 8192,
                "stream": False,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise TranslationError(f"API HTTP {error.code}：{detail}") from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise TranslationError(f"API 请求失败：{error}") from error

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise TranslationError("API 响应缺少 choices")
        message = choices[0].get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content:
            raise TranslationError("API 响应缺少 message.content")
        finish_reason = choices[0].get("finish_reason")
        if finish_reason not in {None, "stop"}:
            raise TranslationError(f"API 输出未完整结束：{finish_reason}")
        usage = payload.get("usage")
        normalized_usage = (
            {
                key: int(value)
                for key, value in usage.items()
                if key in {"prompt_tokens", "completion_tokens", "total_tokens"}
                and isinstance(value, int)
            }
            if isinstance(usage, dict)
            else {}
        )
        return parse_response(content, units), normalized_usage


def split_boundary_whitespace(text: str) -> tuple[str, str, str]:
    """分离片段边界空白，分段翻译后仍保持原有换行和代码邻接间距。"""

    match = re.fullmatch(r"(\s*)(.*?)(\s*)", text, re.DOTALL)
    if match is None:
        return "", text, ""
    return match.group(1), match.group(2), match.group(3)


def translate_inline_segments(
    locale: str,
    unit: TranslationUnit,
    client: DeepSeekClient,
) -> tuple[str, dict[str, int]]:
    """把行内代码当作固定分隔符，只让模型翻译其间的自然语言片段。

    该路径用于含大量技术字面量的长文案。模型从未接触真实字面量，最终按源顺序
    拼回，因此不存在事后猜测“哪个被改写 token 对应哪个源 token”的风险。
    """

    literals = INLINE_CODE_RE.findall(unit.source)
    if not literals:
        raise TranslationError(f"{unit.key} 不含可分段的行内代码")
    source_segments = INLINE_CODE_RE.split(unit.source)

    reference_segments: list[str] | None = None
    if unit.reference and INLINE_CODE_RE.findall(unit.reference) == literals:
        candidate = INLINE_CODE_RE.split(unit.reference)
        if len(candidate) == len(source_segments):
            reference_segments = candidate

    translated_segments = list(source_segments)
    pseudo_units: list[TranslationUnit] = []
    bindings: list[tuple[int, str, str, TranslationUnit]] = []
    for index, segment in enumerate(source_segments):
        leading, core, trailing = split_boundary_whitespace(segment)
        if not core:
            continue
        reference = ""
        if reference_segments is not None:
            _, reference, _ = split_boundary_whitespace(reference_segments[index])
        pseudo = TranslationUnit(
            key=f"{unit.key}.inline-segment.{index}",
            source=core,
            note=(
                f"{unit.note}\n" if unit.note else ""
            ) + (
                f"Natural-language segment {index + 1}/{len(source_segments)} "
                "around protected inline code; translate only this segment."
            ),
            reference=reference,
            target_node=ET.Element("target", {"state": "needs-translation"}),
        )
        pseudo_units.append(pseudo)
        bindings.append((index, leading, trailing, pseudo))

    translations, usage = client.translate(locale, pseudo_units)
    temporary_document = TranslationDocument(
        locale=locale,
        path=Path(),
        tree=ET.ElementTree(ET.Element("xliff")),
        units={pseudo.key: pseudo for pseudo in pseudo_units},
        pending_units=pseudo_units,
    )
    apply_translations(temporary_document, translations)
    for index, leading, trailing, pseudo in bindings:
        translated_segments[index] = (
            leading + (pseudo.target_node.text or "") + trailing
        )

    assembled: list[str] = []
    for index, segment in enumerate(translated_segments):
        assembled.append(segment)
        if index < len(literals):
            assembled.append(literals[index])
    return "".join(assembled), usage


def translate_segmented_document(
    document: TranslationDocument,
    client: DeepSeekClient,
    *,
    retries: int,
) -> dict[str, int]:
    """定向翻译一个超长行内代码单元，并沿用普通写入的原子校验。"""

    if len(document.pending_units) != 1:
        raise TranslationError("分段翻译要求通过 --key 精确选择一个单元")
    unit = document.pending_units[0]
    last_error: TranslationError | None = None
    for attempt in range(1, retries + 1):
        try:
            target, usage = translate_inline_segments(document.locale, unit, client)
            apply_translations(
                document,
                {unit.key: target},
                expected_units=[unit],
            )
            save_document(document)
            return usage
        except TranslationError as error:
            last_error = error
            if attempt == retries:
                break
            delay = min(2 ** (attempt - 1), 15)
            print(
                f"[{document.locale}] segmented attempt {attempt}/{retries} "
                f"failed: {error}; retry in {delay}s",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(delay)
    assert last_error is not None
    raise last_error


def chunks(
    units: list[TranslationUnit],
    size: int,
) -> list[list[TranslationUnit]]:
    return [units[index : index + size] for index in range(0, len(units), size)]


def translate_document(
    document: TranslationDocument,
    client: DeepSeekClient,
    *,
    batch_size: int,
    retries: int,
) -> dict[str, int]:
    """逐批原子落盘；重启脚本会自动跳过已有 target，天然支持续跑。"""

    batches = chunks(document.pending_units, batch_size)
    usage_total = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    for batch_index, batch in enumerate(batches, start=1):
        last_error: TranslationError | None = None
        for attempt in range(1, retries + 1):
            try:
                translations, usage = client.translate(document.locale, batch)
                apply_translations(
                    document,
                    translations,
                    expected_units=batch,
                )
                save_document(document)
                for key in usage_total:
                    usage_total[key] += usage.get(key, 0)
                print(
                    f"[{document.locale}] batch {batch_index}/{len(batches)} "
                    f"written ({len(batch)} units, total_tokens="
                    f"{usage.get('total_tokens', 0)})",
                    flush=True,
                )
                last_error = None
                break
            except TranslationError as error:
                last_error = error
                if attempt == retries:
                    break
                delay = min(2 ** (attempt - 1), 15)
                print(
                    f"[{document.locale}] batch {batch_index} attempt "
                    f"{attempt}/{retries} failed: {error}; retry in {delay}s",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(delay)
        if last_error is not None:
            raise last_error
    return usage_total


def ensure_draft_locale(root: Path, locale: str) -> None:
    manifest = load_json(root / "locales.json")
    locales = manifest.get("locales")
    if not isinstance(locales, list):
        raise TranslationError("locales.json 缺少 locales")
    match = next(
        (
            item
            for item in locales
            if isinstance(item, dict) and item.get("id") == locale
        ),
        None,
    )
    if match is None:
        raise TranslationError(f"locale 不在 locales.json：{locale}")
    if match.get("releaseStatus") != "draft":
        raise TranslationError(f"只允许为 draft locale 生成 AI 初稿：{locale}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locale", required=True, choices=sorted(LOCALE_NAMES))
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="starcat-localization 仓库根目录",
    )
    parser.add_argument("--limit", type=int, help="只处理前 N 个待翻译单元")
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--repair-protected-literals",
        action="store_true",
        help="只修复已有 AI 初稿中被改写的代码块、行内代码和 URL",
    )
    parser.add_argument(
        "--key",
        action="append",
        dest="keys",
        help="定向生成或重译指定的 AI 初稿 key，可重复传入",
    )
    parser.add_argument(
        "--segment-inline-code",
        action="store_true",
        help="把单个 --key 的行内代码作为固定边界，分段翻译自然语言",
    )
    parser.add_argument(
        "--api-key-env",
        default="DEEPSEEK_API_KEY",
        help="API Key 环境变量名",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get(
            "STARCAT_TRANSLATION_BASE_URL",
            "https://api.deepseek.com",
        ),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("STARCAT_TRANSLATION_MODEL", "deepseek-v4-flash"),
    )
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        raise TranslationError("--limit 必须大于 0")
    if args.batch_size <= 0:
        raise TranslationError("--batch-size 必须大于 0")
    if args.retries <= 0:
        raise TranslationError("--retries 必须大于 0")
    if args.repair_protected_literals and args.keys:
        raise TranslationError("--repair-protected-literals 不能与 --key 同时使用")
    if args.segment_inline_code and (
        args.repair_protected_literals
        or not args.keys
        or len(args.keys) != 1
    ):
        raise TranslationError("--segment-inline-code 要求且只允许一个 --key")

    ensure_draft_locale(args.root, args.locale)
    document = load_document(
        args.root,
        args.locale,
        limit=args.limit,
        repair_protected_literals=args.repair_protected_literals,
        requested_keys=set(args.keys) if args.keys else None,
    )
    print(
        f"locale={args.locale} pending={len(document.pending_units)} "
        f"batch_size={args.batch_size} apply={args.apply} "
        f"repair_protected_literals={args.repair_protected_literals} "
        f"segment_inline_code={args.segment_inline_code}"
    )
    if not document.pending_units:
        return 0
    if not args.apply:
        action = (
            "repair protected literals"
            if args.repair_protected_literals
            else "call the API and write AI drafts"
        )
        print(f"dry-run only; pass --apply to {action}")
        return 0

    if args.repair_protected_literals:
        translations = {
            unit.key: restore_protected_literals(
                unit.source,
                unit.target_node.text or "",
            )
            for unit in document.pending_units
        }
        apply_translations(document, translations)
        save_document(document)
        print(
            f"completed locale={args.locale} repaired="
            f"{len(document.pending_units)}"
        )
        return 0

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise TranslationError(f"环境变量不存在：{args.api_key_env}")
    client = DeepSeekClient(
        api_key=api_key,
        base_url=args.base_url,
        model=args.model,
        timeout=args.timeout,
    )
    if args.segment_inline_code:
        usage = translate_segmented_document(
            document,
            client,
            retries=args.retries,
        )
    else:
        usage = translate_document(
            document,
            client,
            batch_size=args.batch_size,
            retries=args.retries,
        )
    print(
        f"completed locale={args.locale} units={len(document.pending_units)} "
        f"usage={json.dumps(usage, ensure_ascii=False)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TranslationError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
