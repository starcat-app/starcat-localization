"""维护者 AI 初稿放行脚本的独立回归测试。

测试只写临时 `.xcloc`，确保动态选择、dry-run、批准记录、digest 与事务回滚
都不会触碰真实语言包。
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "promote_drafts.py"
SPEC = importlib.util.spec_from_file_location("promote_drafts", SCRIPT_PATH)
assert SPEC and SPEC.loader
promoter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(promoter)
validator = promoter.validator


class PromoteDraftsTests(unittest.TestCase):
    """验证 promotion 只提升 draft review target，并可追踪和回滚。"""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "Translation Packages").mkdir()
        self.catalog = {
            "sourceLanguage": "en",
            "strings": {"greeting": {}, "count": {}},
            "version": "1.0",
        }
        self.write_manifest()
        (self.root / "nontranslatable-keys.json").write_text(
            '{"schemaVersion":1,"keys":{}}\n',
            encoding="utf-8",
        )
        self.write_package(
            "en",
            {
                "greeting": ("Hello %@", "Hello %@", "translated"),
                "count": ("%1$@ has %2$d items", "%1$@ has %2$d items", "translated"),
            },
        )
        self.write_package(
            "ja",
            {
                "greeting": ("Hello %@", "こんにちは %@", "needs-review-translation"),
                "count": (
                    "%1$@ has %2$d items",
                    "%2$d 個の項目：%1$@",
                    "needs-review-translation",
                ),
            },
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_manifest(self) -> None:
        payload = {
            "schemaVersion": 1,
            "sourceLocale": "en",
            "locales": [
                {
                    "id": "en",
                    "englishName": "English",
                    "nativeName": "English",
                    "direction": "ltr",
                    "releaseStatus": "released",
                },
                {
                    "id": "ja",
                    "englishName": "Japanese",
                    "nativeName": "日本語",
                    "direction": "ltr",
                    "releaseStatus": "draft",
                },
            ],
        }
        (self.root / "locales.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_package(
        self,
        locale: str,
        units: dict[str, tuple[str, str, str]],
    ) -> None:
        package = self.root / "Translation Packages" / f"{locale}.xcloc"
        localized = package / "Localized Contents"
        source = package / "Source Contents" / "Starcat" / "Localizable"
        localized.mkdir(parents=True)
        source.mkdir(parents=True)
        (package / "contents.json").write_text(
            json.dumps(
                {
                    "developmentRegion": "en",
                    "project": "Starcat.xcodeproj",
                    "targetLocale": locale,
                    "version": "1.0",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (source / "Localizable.xcstrings").write_text(
            json.dumps(self.catalog, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        ET.register_namespace("", validator.XLIFF_NAMESPACE)
        root = ET.Element(
            f"{{{validator.XLIFF_NAMESPACE}}}xliff",
            {"version": "1.2"},
        )
        file_node = ET.SubElement(
            root,
            f"{{{validator.XLIFF_NAMESPACE}}}file",
            {
                "source-language": "en",
                "target-language": locale,
            },
        )
        body = ET.SubElement(
            file_node,
            f"{{{validator.XLIFF_NAMESPACE}}}body",
        )
        for key, (source_text, target_text, state) in units.items():
            unit = ET.SubElement(
                body,
                f"{{{validator.XLIFF_NAMESPACE}}}trans-unit",
                {"id": key},
            )
            ET.SubElement(
                unit,
                f"{{{validator.XLIFF_NAMESPACE}}}source",
            ).text = source_text
            ET.SubElement(
                unit,
                f"{{{validator.XLIFF_NAMESPACE}}}target",
                {"state": state},
            ).text = target_text
        ET.ElementTree(root).write(
            localized / f"{locale}.xliff",
            encoding="utf-8",
            xml_declaration=True,
        )

    def prepare(self) -> promoter.PromotionBatch:
        return promoter.prepare_batch(
            self.root,
            select_all=True,
            locales=[],
            approved_by="dong4j",
            approved_at="2026-07-24T12:00:00Z",
            enforce_confirmed_locales=False,
        )

    def target_states(self, locale: str) -> list[str]:
        package = self.root / "Translation Packages" / f"{locale}.xcloc"
        _, _, units, _ = validator.read_units(package, locale)
        return [unit.state for unit in units.values()]

    def test_all_selects_only_draft_and_dry_run_does_not_write(self) -> None:
        original_manifest = (self.root / "locales.json").read_bytes()
        original_xliff = (
            self.root
            / "Translation Packages"
            / "ja.xcloc"
            / "Localized Contents"
            / "ja.xliff"
        ).read_bytes()

        batch = self.prepare()

        self.assertEqual([item.locale for item in batch.promotions], ["ja"])
        self.assertEqual(batch.promotions[0].promoted, 2)
        self.assertEqual((self.root / "locales.json").read_bytes(), original_manifest)
        self.assertEqual(
            (
                self.root
                / "Translation Packages"
                / "ja.xcloc"
                / "Localized Contents"
                / "ja.xliff"
            ).read_bytes(),
            original_xliff,
        )

    def test_explicit_released_locale_is_rejected(self) -> None:
        manifest = validator.load_json(self.root / "locales.json")

        with self.assertRaisesRegex(
            promoter.PromotionError,
            "只允许提升 draft locale：en",
        ):
            promoter.selected_items(
                manifest,
                select_all=False,
                locales=["en"],
            )

    def test_apply_promotes_review_and_records_valid_approval(self) -> None:
        batch = self.prepare()

        promoter.commit_batch(batch, enforce_confirmed_locales=False)

        self.assertEqual(self.target_states("ja"), ["translated", "translated"])
        manifest = validator.load_json(self.root / "locales.json")
        ja = next(item for item in manifest["locales"] if item["id"] == "ja")
        approval = ja["translationApproval"]
        self.assertEqual(approval["method"], "maintainer-ai-accepted")
        self.assertFalse(approval["humanReviewed"])
        self.assertEqual(approval["approvedBy"], "dong4j")
        self.assertEqual(ja["releaseStatus"], "draft")
        self.assertEqual(validator.validate_repository(self.root).errors, [])

    def test_missing_target_rejects_whole_batch_without_writing(self) -> None:
        package = self.root / "Translation Packages" / "ja.xcloc"
        path = package / "Localized Contents" / "ja.xliff"
        tree = ET.parse(path)
        namespace = {"x": validator.XLIFF_NAMESPACE}
        target = tree.find(".//x:target", namespace)
        assert target is not None
        target.text = ""
        tree.write(path, encoding="utf-8", xml_declaration=True)
        original_manifest = (self.root / "locales.json").read_bytes()

        with self.assertRaisesRegex(promoter.PromotionError, "missing=1"):
            self.prepare()

        self.assertEqual((self.root / "locales.json").read_bytes(), original_manifest)

    def test_write_failure_rolls_back_previous_files(self) -> None:
        batch = self.prepare()
        originals = {
            item.xliff_path: item.xliff_path.read_bytes()
            for item in batch.promotions
        }
        calls = 0

        def failing_writer(path: Path, content: bytes) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated failure")
            promoter.atomic_write_bytes(path, content)

        with self.assertRaisesRegex(OSError, "simulated failure"):
            promoter.commit_batch(
                batch,
                enforce_confirmed_locales=False,
                writer=failing_writer,
            )

        for path, content in originals.items():
            self.assertEqual(path.read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
