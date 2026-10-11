"""AI 本地化初稿脚本的独立回归测试。

测试只使用临时 XLIFF 和假翻译函数，不访问网络，重点保证续跑、状态和占位符
约束。AI 初稿只能写成 `needs-review-translation`。
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "translate_draft.py"
SPEC = importlib.util.spec_from_file_location("translate_draft", SCRIPT_PATH)
assert SPEC and SPEC.loader
translator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(translator)


class TranslateDraftTests(unittest.TestCase):
    """验证候选筛选、AI 初稿状态、续跑和失败不写盘。"""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.package = self.root / "Translation Packages" / "ja.xcloc"
        localized = self.package / "Localized Contents"
        localized.mkdir(parents=True)
        self.xliff = localized / "ja.xliff"
        self.write_xliff(
            {
                "greeting": ("Hello %@", "", "needs-translation", "Greeting"),
                "danger.delete": ("Delete", "", "needs-translation", "Destructive button"),
                "existing": ("Existing", "既存", "needs-review-translation", ""),
                "approved": ("Approved", "承認済み", "translated", ""),
                "Starcat": ("Starcat", "", "needs-translation", "Product name"),
            }
        )
        (self.root / "nontranslatable-keys.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "keys": {"Starcat": "产品名称"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_xliff(
        self,
        units: dict[str, tuple[str, str, str, str]],
    ) -> None:
        ET.register_namespace("", translator.XLIFF_NAMESPACE)
        root = ET.Element(
            f"{{{translator.XLIFF_NAMESPACE}}}xliff",
            {"version": "1.2"},
        )
        file_node = ET.SubElement(
            root,
            f"{{{translator.XLIFF_NAMESPACE}}}file",
            {"source-language": "en", "target-language": "ja"},
        )
        body = ET.SubElement(file_node, f"{{{translator.XLIFF_NAMESPACE}}}body")
        for key, (source, target, state, note) in units.items():
            unit = ET.SubElement(
                body,
                f"{{{translator.XLIFF_NAMESPACE}}}trans-unit",
                {"id": key},
            )
            ET.SubElement(
                unit,
                f"{{{translator.XLIFF_NAMESPACE}}}source",
            ).text = source
            ET.SubElement(
                unit,
                f"{{{translator.XLIFF_NAMESPACE}}}target",
                {"state": state},
            ).text = target
            if note:
                ET.SubElement(
                    unit,
                    f"{{{translator.XLIFF_NAMESPACE}}}note",
                ).text = note
        ET.indent(root, space="  ")
        ET.ElementTree(root).write(self.xliff, encoding="utf-8", xml_declaration=True)

    def read_targets(self) -> dict[str, tuple[str, str]]:
        tree = ET.parse(self.xliff)
        namespace = {"x": translator.XLIFF_NAMESPACE}
        result: dict[str, tuple[str, str]] = {}
        for unit in tree.findall(".//x:trans-unit", namespace):
            target = unit.find("x:target", namespace)
            assert target is not None
            result[unit.get("id", "")] = (
                target.text or "",
                target.get("state", ""),
            )
        return result

    def test_candidates_skip_allowlist_existing_and_approved_units(self) -> None:
        document = translator.load_document(self.root, "ja")

        self.assertEqual(
            [unit.key for unit in document.pending_units],
            ["greeting", "danger.delete"],
        )

    def test_apply_batch_writes_only_review_state(self) -> None:
        document = translator.load_document(self.root, "ja")
        translations = {
            "greeting": "こんにちは %@",
            "danger.delete": "削除",
        }

        translator.apply_translations(document, translations)
        translator.save_document(document)

        targets = self.read_targets()
        self.assertEqual(
            targets["greeting"],
            ("こんにちは %@", "needs-review-translation"),
        )
        self.assertEqual(
            targets["danger.delete"],
            ("削除", "needs-review-translation"),
        )
        self.assertEqual(
            targets["existing"],
            ("既存", "needs-review-translation"),
        )
        self.assertEqual(targets["approved"], ("承認済み", "translated"))
        self.assertEqual(targets["Starcat"], ("", "needs-translation"))

    def test_placeholder_loss_rejects_batch_without_mutating_tree(self) -> None:
        document = translator.load_document(self.root, "ja")

        with self.assertRaisesRegex(translator.TranslationError, "占位符"):
            translator.apply_translations(
                document,
                {
                    "greeting": "こんにちは",
                    "danger.delete": "削除",
                },
            )

        targets = {
            unit.key: unit.target_node.text or ""
            for unit in document.units.values()
        }
        self.assertEqual(targets["greeting"], "")
        self.assertEqual(targets["danger.delete"], "")

    def test_protected_literal_change_rejects_batch(self) -> None:
        document = translator.load_document(self.root, "ja")
        document.units["greeting"].source = (
            "Run `starcat doctor` and open https://starcat.ink/docs."
        )

        with self.assertRaisesRegex(
            translator.TranslationError,
            "受保护字面量",
        ):
            translator.apply_translations(
                document,
                {
                    "greeting": (
                        "「starcat doctor」を実行して "
                        "https://starcat.ink/ドキュメント を開きます。"
                    ),
                    "danger.delete": "削除",
                },
            )

    def test_extra_inline_code_markers_are_stripped_before_validation(self) -> None:
        document = translator.load_document(self.root, "ja")
        document.units["greeting"].source = (
            "Verify MCP initialization and `tools/list` for %@."
        )

        translator.apply_translations(
            document,
            {
                "greeting": (
                    "MCP の `initialize` と `tools/list` を %@ 向けに確認します。"
                ),
                "danger.delete": "削除",
            },
        )

        self.assertEqual(
            document.units["greeting"].target_node.text,
            "MCP の initialize と `tools/list` を %@ 向けに確認します。",
        )

    def test_extra_inline_code_markers_around_placeholder_are_stripped(self) -> None:
        self.assertEqual(
            translator.strip_unexpected_inline_code("Unread %@", "未読 `%@` 件"),
            "未読 %@ 件",
        )

    def test_inline_code_is_masked_for_ai_and_restored_exactly(self) -> None:
        source = "Run `starcat doctor`, then use `$cliPath`."
        masked, literals = translator.mask_inline_code(source)

        self.assertEqual(
            masked,
            "Run ⟦SC_INLINE_0000⟧, then use ⟦SC_INLINE_0001⟧.",
        )
        self.assertEqual(literals, ("`starcat doctor`", "`$cliPath`"))
        self.assertEqual(
            translator.restore_inline_code_mask(
                "⟦SC_INLINE_0000⟧ を実行し、⟦SC_INLINE_0001⟧ を使用します。",
                literals,
            ),
            "`starcat doctor` を実行し、`$cliPath` を使用します。",
        )

    def test_inline_code_mask_reorder_is_rejected(self) -> None:
        with self.assertRaisesRegex(translator.TranslationError, "掩码不一致"):
            translator.restore_inline_code_mask(
                "⟦SC_INLINE_0001⟧ then ⟦SC_INLINE_0000⟧",
                ("`first`", "`second`"),
            )

    def test_parse_response_restores_masked_inline_code(self) -> None:
        document = translator.load_document(self.root, "ja", limit=1)
        unit = document.pending_units[0]
        unit.source = "Verify `tools/list`."
        content = json.dumps(
            {
                "translations": [
                    {"id": 0, "text": "⟦SC_INLINE_0000⟧ を確認します。"}
                ]
            },
            ensure_ascii=False,
        )

        self.assertEqual(
            translator.parse_response(content, [unit]),
            {"greeting": "`tools/list` を確認します。"},
        )

    def test_segmented_translation_never_exposes_or_reorders_inline_code(self) -> None:
        class FakeClient:
            def translate(self, locale, units):
                self.locale = locale
                self.sources = [unit.source for unit in units]
                return (
                    {unit.key: f"訳[{unit.source}]" for unit in units},
                    {"total_tokens": 12},
                )

        target = ET.Element("target", {"state": "needs-translation"})
        unit = translator.TranslationUnit(
            key="long.prompt",
            source="Run `first`, then use `$cliPath`.",
            note="",
            reference="",
            target_node=target,
        )
        client = FakeClient()

        translated, usage = translator.translate_inline_segments(
            "ja",
            unit,
            client,
        )

        self.assertEqual(client.locale, "ja")
        self.assertTrue(all("`" not in source for source in client.sources))
        self.assertEqual(
            translator.INLINE_CODE_RE.findall(translated),
            ["`first`", "`$cliPath`"],
        )
        self.assertEqual(usage, {"total_tokens": 12})

    def test_text_fence_may_translate_but_executable_fence_must_not(self) -> None:
        text_source = (
            "```text\nCommand: absolute path\n```\n\n"
            "```bash\nstarcat doctor\n```"
        )
        text_target = (
            "```text\nコマンド: 絶対パス\n```\n\n"
            "```bash\nstarcat doctor\n```"
        )
        bash_target = (
            "```text\nコマンド: 絶対パス\n```\n\n"
            "```bash\nstarcat 診断\n```"
        )

        self.assertIsNone(
            translator.protected_literal_error(text_source, text_target)
        )
        self.assertIsNotNone(
            translator.protected_literal_error(text_source, bash_target)
        )

    def test_protected_literal_error_reports_first_difference(self) -> None:
        error = translator.protected_literal_error(
            "Run `first` then `second`.",
            "実行 `first`、次に `changed`。",
        )

        self.assertEqual(
            error,
            "行内代码 不一致：source_count=2 target_count=2 "
            "first_diff[1]=source:'`second`' target:'`changed`'",
        )

    def test_repair_mode_only_restores_ai_review_literals(self) -> None:
        self.write_xliff(
            {
                "code": (
                    "Run `git -C <skill-path> pull --ff-only`.",
                    "実行 `git -C <スキルパス> pull --ff-only`。",
                    "needs-review-translation",
                    "",
                ),
                "url": (
                    "Open https://api.openai.com/v1.",
                    "https://api.openai.com/v2 を開きます。",
                    "needs-review-translation",
                    "",
                ),
                "approved": (
                    "Run `starcat doctor`.",
                    "実行 `starcat 診断`。",
                    "translated",
                    "",
                ),
            }
        )

        document = translator.load_document(
            self.root,
            "ja",
            repair_protected_literals=True,
        )

        self.assertEqual(
            [unit.key for unit in document.pending_units],
            ["code", "url"],
        )
        repaired = {
            unit.key: translator.restore_protected_literals(
                unit.source,
                unit.target_node.text or "",
            )
            for unit in document.pending_units
        }
        translator.apply_translations(document, repaired)
        self.assertEqual(
            repaired["code"],
            "実行 `git -C <skill-path> pull --ff-only`。",
        )
        self.assertEqual(
            repaired["url"],
            "https://api.openai.com/v1 を開きます。",
        )

    def test_requested_key_selects_existing_review_but_not_approved(self) -> None:
        document = translator.load_document(
            self.root,
            "ja",
            requested_keys={"existing"},
        )
        self.assertEqual(
            [unit.key for unit in document.pending_units],
            ["existing"],
        )

        empty_document = translator.load_document(
            self.root,
            "ja",
            requested_keys={"greeting"},
        )
        self.assertEqual(
            [unit.key for unit in empty_document.pending_units],
            ["greeting"],
        )

        with self.assertRaisesRegex(
            translator.TranslationError,
            "已审核或不可生成 AI 初稿",
        ):
            translator.load_document(
                self.root,
                "ja",
                requested_keys={"approved"},
            )

    def test_missing_or_unknown_response_key_rejects_batch(self) -> None:
        document = translator.load_document(self.root, "ja")

        with self.assertRaisesRegex(translator.TranslationError, "key 集合"):
            translator.apply_translations(
                document,
                {
                    "greeting": "こんにちは %@",
                    "unexpected": "不明",
                },
            )

    def test_limit_keeps_deterministic_xliff_order(self) -> None:
        document = translator.load_document(self.root, "ja", limit=1)

        self.assertEqual([unit.key for unit in document.pending_units], ["greeting"])


if __name__ == "__main__":
    unittest.main()
