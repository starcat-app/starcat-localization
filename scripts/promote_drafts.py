#!/usr/bin/env python3
"""把已通过自动校验的 AI 初稿提升为可导入翻译。

默认只做 dry-run。`--apply` 必须同时提供 `--approval-method` 和
`--approved-by`；脚本只修改 draft locale 的 `needs-review-translation` state，
并在 `locales.json.translationApproval` 记录可校验的批准来源。它不会导入主
Catalog、修改 `releaseStatus` 或开放 `AppLocale`。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, NamedTuple


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_packages as validator


APPROVAL_METHOD = "maintainer-ai-accepted"


class PromotionError(RuntimeError):
    """表示当前语言包不能安全执行维护者 AI 放行。"""


class LocalePromotion(NamedTuple):
    """单个 locale 的内存修改结果，全部验证后才允许落盘。"""

    locale: str
    xliff_path: Path
    tree: ET.ElementTree
    promoted: int
    already_approved: int
    approval: dict[str, Any]


class PromotionBatch(NamedTuple):
    """一次全量事务所需的 manifest 与全部 locale 修改。"""

    root: Path
    manifest: dict[str, Any]
    promotions: list[LocalePromotion]


def utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """同目录临时文件替换，保证单个 JSON/XML 不会被写成半文件。"""

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def xliff_bytes(tree: ET.ElementTree) -> bytes:
    ET.indent(tree.getroot(), space="  ")
    return ET.tostring(
        tree.getroot(),
        encoding="utf-8",
        xml_declaration=True,
    )


def selected_items(
    manifest: dict[str, Any],
    *,
    select_all: bool,
    locales: list[str],
) -> list[dict[str, Any]]:
    items = manifest.get("locales")
    if not isinstance(items, list):
        raise PromotionError("locales.json 缺少 locales")
    by_id = {
        item.get("id"): item
        for item in items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if select_all:
        selected = [
            item
            for item in items
            if isinstance(item, dict) and item.get("releaseStatus") == "draft"
        ]
    else:
        unknown = [locale for locale in locales if locale not in by_id]
        if unknown:
            raise PromotionError("未知 locale：" + ", ".join(unknown))
        selected = [by_id[locale] for locale in locales]

    if not selected:
        raise PromotionError("没有可处理的 draft locale")
    released = [
        item["id"]
        for item in selected
        if item.get("releaseStatus") != "draft"
    ]
    if released:
        raise PromotionError(
            "只允许提升 draft locale：" + ", ".join(released)
        )
    return selected


def prepare_batch(
    root: Path,
    *,
    select_all: bool,
    locales: list[str],
    approved_by: str,
    approved_at: str,
    enforce_confirmed_locales: bool,
) -> PromotionBatch:
    """先验证整仓和全部目标，再在内存中构造状态提升。"""

    validation = validator.validate_repository(
        root,
        enforce_confirmed_locales=enforce_confirmed_locales,
    )
    if validation.errors:
        raise PromotionError(
            "放行前 validator 未通过：\n- "
            + "\n- ".join(validation.errors)
        )

    manifest = validator.load_json(root / validator.MANIFEST_NAME)
    items = selected_items(
        manifest,
        select_all=select_all,
        locales=locales,
    )
    exclusions = set(validator.load_exclusions(root))
    promotions: list[LocalePromotion] = []
    namespace = {"x": validator.XLIFF_NAMESPACE}

    for item in items:
        locale = item["id"]
        report = validation.reports.get(locale)
        if report is None:
            raise PromotionError(f"{locale} 缺少 validator report")
        if report.missing:
            raise PromotionError(
                f"{locale} 仍有 missing={report.missing}，不能放行"
            )

        package = (
            root
            / validator.PACKAGE_DIR_NAME
            / f"{locale}.xcloc"
        )
        xliff_path = package / "Localized Contents" / f"{locale}.xliff"
        try:
            tree = ET.parse(xliff_path)
        except (OSError, ET.ParseError) as error:
            raise PromotionError(f"{locale} XLIFF 无法读取：{error}") from error

        promoted = 0
        already_approved = 0
        for node in tree.findall(".//x:trans-unit", namespace):
            key = node.get("id")
            target = node.find("x:target", namespace)
            if not key or target is None:
                raise PromotionError(f"{locale} 存在不完整 trans-unit")
            if key in exclusions:
                continue
            state = target.get("state", "needs-translation")
            if not (target.text or ""):
                raise PromotionError(f"{locale}:{key} target 为空")
            if state == "needs-review-translation":
                target.set("state", "translated")
                promoted += 1
            elif state in validator.APPROVED_STATES:
                already_approved += 1
            else:
                raise PromotionError(
                    f"{locale}:{key} state={state} 不能放行"
                )

        _, _, units, duplicates = validator.read_units(package, locale)
        if duplicates:
            raise PromotionError(f"{locale} 存在重复 key")
        unit_count, target_digest = validator.translation_digest(
            locale,
            units,
            exclusions,
        )
        approval = {
            "method": APPROVAL_METHOD,
            "humanReviewed": False,
            "approvedBy": approved_by,
            "approvedAt": approved_at,
            "unitCount": unit_count,
            "sourceDigest": validator.source_digest(package),
            "translationDigest": target_digest,
        }
        item["translationApproval"] = approval
        promotions.append(
            LocalePromotion(
                locale=locale,
                xliff_path=xliff_path,
                tree=tree,
                promoted=promoted,
                already_approved=already_approved,
                approval=approval,
            )
        )

    return PromotionBatch(root=root, manifest=manifest, promotions=promotions)


def commit_batch(
    batch: PromotionBatch,
    *,
    enforce_confirmed_locales: bool,
    writer: Callable[[Path, bytes], None] = atomic_write_bytes,
) -> None:
    """写入失败或写后校验失败时恢复全部原文件。"""

    changes = [
        (promotion.xliff_path, xliff_bytes(promotion.tree))
        for promotion in batch.promotions
    ]
    changes.append(
        (
            batch.root / validator.MANIFEST_NAME,
            manifest_bytes(batch.manifest),
        )
    )
    originals = {path: path.read_bytes() for path, _ in changes}
    written: list[Path] = []
    try:
        for path, content in changes:
            writer(path, content)
            written.append(path)
        result = validator.validate_repository(
            batch.root,
            enforce_confirmed_locales=enforce_confirmed_locales,
        )
        if result.errors:
            raise PromotionError(
                "放行后 validator 未通过：\n- "
                + "\n- ".join(result.errors)
            )
    except BaseException:
        for path in reversed(written):
            atomic_write_bytes(path, originals[path])
        raise


def print_batch(batch: PromotionBatch, *, apply: bool) -> None:
    print(
        f"mode={'apply' if apply else 'dry-run'} "
        f"locales={len(batch.promotions)}"
    )
    for promotion in batch.promotions:
        print(
            f"{promotion.locale}: promote={promotion.promoted} "
            f"already-approved={promotion.already_approved} "
            f"sourceDigest={promotion.approval['sourceDigest']} "
            f"translationDigest={promotion.approval['translationDigest']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="starcat-localization 仓库根目录",
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--all",
        action="store_true",
        help="动态选择 locales.json 中全部 draft locale",
    )
    selection.add_argument(
        "--locale",
        action="append",
        dest="locales",
        help="只处理指定 locale，可重复",
    )
    parser.add_argument(
        "--approval-method",
        choices=[APPROVAL_METHOD],
        help="写入时必须显式声明 maintainer-ai-accepted",
    )
    parser.add_argument(
        "--approved-by",
        help="写入批准记录的维护者标识；脚本不会猜测",
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.apply and args.approval_method != APPROVAL_METHOD:
        raise PromotionError(
            "--apply 必须显式提供 "
            "--approval-method maintainer-ai-accepted"
        )
    if args.apply and (
        not isinstance(args.approved_by, str)
        or not args.approved_by.strip()
    ):
        raise PromotionError("--apply 必须提供非空 --approved-by")

    approved_by = (
        args.approved_by.strip()
        if isinstance(args.approved_by, str) and args.approved_by.strip()
        else "<required-on-apply>"
    )
    batch = prepare_batch(
        args.root.resolve(),
        select_all=args.all,
        locales=args.locales or [],
        approved_by=approved_by,
        approved_at=utc_timestamp(),
        enforce_confirmed_locales=True,
    )
    print_batch(batch, apply=args.apply)
    if not args.apply:
        print(
            "dry-run only; pass --apply, --approval-method and "
            "--approved-by to write"
        )
        return 0

    commit_batch(batch, enforce_confirmed_locales=True)
    print(
        f"completed locales={len(batch.promotions)} "
        f"promoted={sum(item.promoted for item in batch.promotions)} "
        "releaseStatus remains draft"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PromotionError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
