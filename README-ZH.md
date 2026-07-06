# Starcat 本地化

这个仓库用于公开维护 Starcat 的本地化资源。

Starcat 是一款原生 macOS 应用，可以把 GitHub Stars 变成可搜索的 AI 知识库。这个仓库让翻译贡献者和用户可以改进 Starcat 的界面文案，而不需要访问私有应用源码。

## 包含内容

```text
Starcat Localizations/
└── Localizable.xcstrings

Glossary/
├── en.md
└── zh-Hans.md
```

- `Starcat Localizations/Localizable.xcstrings` 是 Starcat 使用的 Xcode String Catalog。
- `Glossary/` 记录产品术语和推荐译法。

## 当前语言

- `en`：源语言。
- `zh-Hans`：简体中文。

未完成或尚未审核的语言可以先保留在这个仓库中，达到质量要求后再进入 Starcat 稳定版。

## 如何参与

1. 从 Mac App Store 安装 Xcode。
2. 用 Xcode 打开 `Starcat Localizations/Localizable.xcstrings`。
3. 修改对应语言的翻译。
4. 改产品术语前先查看 glossary。
5. 通过 Pull Request 提交修改。

如果你不熟悉 Git，也可以创建 issue，并附上修改后的 `.xcstrings` 文件。

## 翻译规则

- 占位符必须原样保留，例如 `%@`、`%1$@`、`%d`、`%%`。
- `Starcat`、`GitHub`、`OpenSSF`、`CodeFlow`、`CodebaseMemory` 等产品名和技术名不要随意翻译。
- UI 文案要尽量简洁。Starcat 是信息密度较高的 macOS 应用，过长文案容易撑坏布局。
- 不要机械翻译技术术语，优先参考 glossary。
- 不要修改 key，只修改本地化 value。

## 校验

提交前运行：

```bash
jq empty "Starcat Localizations/Localizable.xcstrings"
```

这个命令可以确认 String Catalog 仍然是合法 JSON。

## 相关链接

- Starcat 官网：https://starcat.ink
- 公开支持仓库：https://github.com/dong4j/starcat-pro
- 问题反馈：https://github.com/dong4j/starcat-localization/issues
