"""公开本地化仓库 validator 的独立回归测试。

测试用极小的临时 `.xcloc` 构造结构错误和发布门禁错误，确保 GitHub Actions
与维护者本地运行时得到同一结论，不依赖 Starcat 私有主仓库。
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_packages.py"
SPEC = importlib.util.spec_from_file_location("validate_packages", SCRIPT_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class ValidatePackagesTests(unittest.TestCase):
    """验证 manifest、包结构、key、状态和占位符门禁。"""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "Translation Packages").mkdir()
        self.write_manifest(ja_status="draft")
        self.write_allowlist({})
        self.catalog = {
            "sourceLanguage": "en",
            "strings": {
                "greeting": {
                    "localizations": {
                        "en": {
                            "stringUnit": {
                                "state": "translated",
                                "value": "Hello %@",
                            }
                        }
                    }
                },
                "count": {
                    "localizations": {
                        "en": {
                            "stringUnit": {
                                "state": "translated",
                                "value": "%1$@ has %2$d items",
                            }
                        }
                    }
                },
            },
            "version": "1.0",
        }
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
                "greeting": ("Hello %@", "", "needs-translation"),
                "count": ("%1$@ has %2$d items", "", "needs-translation"),
            },
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_manifest(self, *, ja_status: str) -> None:
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
                    "releaseStatus": ja_status,
                },
            ],
        }
        (self.root / "locales.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_allowlist(self, keys: dict[str, str]) -> None:
        payload = {"schemaVersion": 1, "keys": keys}
        (self.root / "nontranslatable-keys.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_package(
        self,
        locale: str,
        units: dict[str, tuple[str, str, str]],
        *,
        contents_locale: str | None = None,
        embedded_catalog: dict[str, object] | None = None,
    ) -> Path:
        package = self.root / "Translation Packages" / f"{locale}.xcloc"
        localized = package / "Localized Contents"
        source = package / "Source Contents" / "Starcat" / "Localizable"
        localized.mkdir(parents=True, exist_ok=True)
        source.mkdir(parents=True, exist_ok=True)
        (package / "contents.json").write_text(
            json.dumps(
                {
                    "developmentRegion": "en",
                    "project": "Starcat.xcodeproj",
                    "targetLocale": contents_locale or locale,
                    "version": "1.0",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (source / "Localizable.xcstrings").write_text(
            json.dumps(embedded_catalog or self.catalog, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        ET.register_namespace("", validator.XLIFF_NAMESPACE)
        root = ET.Element(f"{{{validator.XLIFF_NAMESPACE}}}xliff", {"version": "1.2"})
        file_node = ET.SubElement(
            root,
            f"{{{validator.XLIFF_NAMESPACE}}}file",
            {
                "source-language": "en",
                "target-language": locale,
                "datatype": "plaintext",
            },
        )
        body = ET.SubElement(file_node, f"{{{validator.XLIFF_NAMESPACE}}}body")
        for key, (source_text, target_text, state) in units.items():
            unit = ET.SubElement(body, f"{{{validator.XLIFF_NAMESPACE}}}trans-unit", {"id": key})
            ET.SubElement(unit, f"{{{validator.XLIFF_NAMESPACE}}}source").text = source_text
            target = ET.SubElement(
                unit,
                f"{{{validator.XLIFF_NAMESPACE}}}target",
                {"state": state},
            )
            target.text = target_text
        ET.ElementTree(root).write(
            localized / f"{locale}.xliff",
            encoding="utf-8",
            xml_declaration=True,
        )
        return package

    def validate(self) -> validator.ValidationResult:
        return validator.validate_repository(self.root)

    def test_draft_language_may_be_incomplete(self) -> None:
        result = self.validate()
        self.assertEqual(result.errors, [])
        self.assertEqual(result.reports["ja"].missing, 2)

    def test_released_language_must_have_no_missing_or_review_units(self) -> None:
        self.write_manifest(ja_status="released")
        result = self.validate()
        self.assertTrue(any("released locale ja" in error for error in result.errors))

    def test_missing_and_extra_packages_are_rejected(self) -> None:
        shutil.rmtree(self.root / "Translation Packages" / "ja.xcloc")
        shutil.copytree(
            self.root / "Translation Packages" / "en.xcloc",
            self.root / "Translation Packages" / "de.xcloc",
        )
        result = self.validate()
        self.assertTrue(any("缺少语言包" in error for error in result.errors))
        self.assertTrue(any("manifest 外语言包" in error for error in result.errors))

    def test_package_name_must_match_target_locale(self) -> None:
        shutil.rmtree(self.root / "Translation Packages" / "ja.xcloc")
        self.write_package(
            "ja",
            {
                "greeting": ("Hello %@", "", "needs-translation"),
                "count": ("%1$@ has %2$d items", "", "needs-translation"),
            },
            contents_locale="ko",
        )
        result = self.validate()
        self.assertTrue(any("targetLocale" in error for error in result.errors))

    def test_source_snapshots_must_match(self) -> None:
        altered = json.loads(json.dumps(self.catalog))
        altered["strings"]["extra"] = {}
        shutil.rmtree(self.root / "Translation Packages" / "ja.xcloc")
        self.write_package(
            "ja",
            {
                "greeting": ("Hello %@", "", "needs-translation"),
                "count": ("%1$@ has %2$d items", "", "needs-translation"),
            },
            embedded_catalog=altered,
        )
        result = self.validate()
        self.assertTrue(any("source snapshot" in error for error in result.errors))

    def test_key_set_and_duplicates_are_rejected(self) -> None:
        xliff = self.root / "Translation Packages" / "ja.xcloc" / "Localized Contents" / "ja.xliff"
        tree = ET.parse(xliff)
        namespace = {"x": validator.XLIFF_NAMESPACE}
        body = tree.find(".//x:body", namespace)
        assert body is not None
        duplicate = ET.SubElement(
            body,
            f"{{{validator.XLIFF_NAMESPACE}}}trans-unit",
            {"id": "greeting"},
        )
        ET.SubElement(duplicate, f"{{{validator.XLIFF_NAMESPACE}}}source").text = "Hello %@"
        ET.SubElement(
            duplicate,
            f"{{{validator.XLIFF_NAMESPACE}}}target",
            {"state": "translated"},
        ).text = "こんにちは %@"
        tree.write(xliff, encoding="utf-8", xml_declaration=True)
        result = self.validate()
        self.assertTrue(any("重复 key" in error for error in result.errors))

    def test_placeholder_loss_is_rejected_but_positional_reorder_is_allowed(self) -> None:
        shutil.rmtree(self.root / "Translation Packages" / "ja.xcloc")
        self.write_package(
            "ja",
            {
                "greeting": ("Hello %@", "こんにちは", "translated"),
                "count": ("%1$@ has %2$d items", "%2$d 個の項目：%1$@", "translated"),
            },
        )
        result = self.validate()
        self.assertTrue(any("greeting" in error and "占位符" in error for error in result.errors))
        self.assertFalse(any("count" in error and "占位符" in error for error in result.errors))

    def test_code_and_url_changes_are_rejected(self) -> None:
        shutil.rmtree(self.root / "Translation Packages" / "ja.xcloc")
        self.write_package(
            "ja",
            {
                "greeting": (
                    "Run `starcat doctor` at https://starcat.ink/docs.",
                    "実行 `starcat 診断`：https://starcat.ink/ドキュメント。",
                    "needs-review-translation",
                ),
                "count": (
                    "%1$@ has %2$d items",
                    "%2$d 個の項目：%1$@",
                    "translated",
                ),
            },
        )
        result = self.validate()
        self.assertTrue(
            any(
                "greeting" in error and "受保护字面量" in error
                for error in result.errors
            )
        )

    def test_stale_allowlist_is_rejected(self) -> None:
        self.write_allowlist({"deleted.key": "历史遗留"})
        result = self.validate()
        self.assertTrue(any("stale nontranslatable" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
