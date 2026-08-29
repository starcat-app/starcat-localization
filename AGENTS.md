# AGENTS.md

本文档是 `starcat-localization` 的 AI 协作规则唯一维护源。

## 仓库边界

- 本目录是公开本地化资源的独立 Git 仓库，不包含 Starcat 私有应用源码，也不能直接
  改写主工程 `Localizable.xcstrings`。
- 本仓库拥有独立分支、remote、提交和发布边界；不得把改动并入外层 Starcat 主仓库
  或顺带修改相邻 `supports/*` 项目。
- 开工前核对 `git status --short` 与当前分支，保留用户已有改动；未经明确要求不
  commit、push、切分支或修改 remote。

## 用途、技术栈与目录

- `Translation Packages/<locale>.xcloc/` 保存 Xcode 导出的独立语言包；包内 XLIFF
  是翻译协作载体，嵌入的 String Catalog 是统一 source snapshot，不得各包自行分叉。
- `locales.json` 是 locale 清单、书写方向和 `releaseStatus` 的单一来源；
  `nontranslatable-keys.json` 记录有理由的不可翻译 key。
- `Glossary/` 保存产品术语；`scripts/` 使用 Python 3 标准库校验、生成 AI 初稿和执行
  受控放行；`tests/` 覆盖这些契约。

## `.xcloc` 与发布状态规则

- 只修改目标 locale 的翻译 value/state，不改 key、source 文本、占位符、代码、URL
  或其他语言包；所有语言包必须继续携带一致的 source snapshot。
- `%@`、`%1$@`、`%d`、`%%`、`{name}` 等占位符必须保持数量、类型与合法顺序；
  可执行代码块、行内代码和 URL 必须原样保留。
- `draft` 表示可协作，不表示已随 App 发布；`released` 必须通过完整度、审核记录、
  自动校验、应用内布局以及适用时的 RTL 验收。
- 不得自行修改 `locales.json` 的 `releaseStatus`。只有 dong4j 明确批准某个 locale
  发布后，才能由维护者完成状态提升和主工程导入。
- `scripts/promote_drafts.py` 默认只做 dry-run；`--apply` 会改写 XLIFF 与批准记录，
  仍不会修改 `releaseStatus`，未经明确授权不得执行。

## 验证命令

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/validate_packages.py
git diff --check
```

## 外部副作用禁令

- 未经 dong4j 明确授权，不得运行主工程本地化导入、批量 AI 翻译放行、发布状态提升、
  push 或 Release；也不得把公开包同步回私有应用仓库。
- 不得提交真实用户内容、凭据或来源不明的机器翻译；AI 初稿必须保持待复核状态，不能
  冒充人工审核结果。
