# Starcat 本地化

这个仓库用于公开维护 Starcat 的本地化资源。

Starcat 是一款原生 macOS 应用，可以把 GitHub Stars 变成可搜索的 AI 知识库。这个仓库让翻译贡献者和用户可以改进 Starcat 的界面文案，而不需要访问私有应用源码。

## 包含内容

```text
Translation Packages/
├── en.xcloc
└── zh-Hans.xcloc

Glossary/
├── en.md
└── zh-Hans.md
```

- `Translation Packages/` 按语言存放 Xcode 本地化包，每种语言一个 `.xcloc`。
- `Glossary/` 记录产品术语和推荐译法。

## 当前语言

- `en`：源语言。
- `zh-Hans`：简体中文。

未完成或尚未审核的语言可以先保留在这个仓库中，达到质量要求后再进入 Starcat 稳定版。

## 如何参与？

如果你想一次性或长期参与 Starcat 本地化，直接加入 [Starcat localization issues](https://github.com/dong4j/starcat-localization/issues) 里的讨论即可。如果你的语言还没有对应 issue，也可以为这个语言新建一个 issue。

本地化流程很简单：

1. 从 Mac App Store 安装免费的 Xcode。
2. 从 `Translation Packages/` 下载你的语言对应的 `.xcloc` 包。
3. 用 Xcode 打开这个 `.xcloc` 包。
4. 不确定产品术语怎么翻译时，先查看 `Glossary/`。
5. 把修改后的 `.xcloc` 包附在 issue 评论里；如果你熟悉 Git，也可以提交 pull request。

你不需要理解 Starcat 的代码。过程中可以随时在 issue 里提问，不用担心技术细节。

熟悉 Git 的高级贡献者可以 fork 仓库并提交 PR，但这不是必须的。直接在 issue 评论里附上修改后的文件也可以。

## 翻译规则

- 占位符必须原样保留，例如 `%@`、`%1$@`、`%d`、`%%`。
- `Starcat`、`GitHub`、`OpenSSF`、`CodeFlow`、`CodebaseMemory` 等产品名和技术名不要随意翻译。
- UI 文案要尽量简洁。Starcat 是信息密度较高的 macOS 应用，过长文案容易撑坏布局。
- 不要机械翻译技术术语，优先参考 glossary。
- 不要修改 key，只修改本地化 value。
- 每种语言只维护自己的 `.xcloc` 包，不要在这个仓库提交完整的 `Localizable.xcstrings`。

## 词汇表

部分本地化已有 Starcat 词汇表：

- [English](Glossary/en.md)
- [简体中文](Glossary/zh-Hans.md)

## Apple Localization Terms Glossary

标准 macOS 和 Apple 平台术语也可以参考 [Kishikawa Katsumi](https://github.com/kishikawakatsumi) 维护的非官方词汇表：

- [Apple Localization Terms Glossary](https://applelocalization.com/macos)

## 维护者导入流程

Starcat 维护者在主工程里使用支持脚本把贡献者提交的 `.xcloc` 倒回应用：

```bash
supports/scripts/starcat-localization.py import \
  --package "supports/starcat-localization/Translation Packages/zh-Hans.xcloc"

supports/scripts/starcat-localization.py import-all
```

脚本会把 `.xcloc` 中的翻译写回 `Starcat/Resources/Localizable.xcstrings`。公开本地化仓库继续保持“每种语言一个包”的结构。

## 相关链接

- Starcat 官网：https://starcat.ink
- 公开支持仓库：https://github.com/dong4j/starcat-pro
- 问题反馈：https://github.com/dong4j/starcat-localization/issues
