# Starcat Localization

This repository contains the public localization resources for Starcat.

Starcat is a native macOS app that turns GitHub Stars into a searchable AI knowledge base. This repository lets translators and users improve Starcat's interface text without requiring access to the private application source code.

## What Is Included

```text
Translation Packages/
├── en.xcloc
└── zh-Hans.xcloc

Glossary/
├── en.md
└── zh-Hans.md
```

- `Translation Packages/` contains one Xcode localization package per language.
- `Glossary/` records product terms and preferred translations.

## Current Languages

- `en` — source language.
- `zh-Hans` — Simplified Chinese.

Localizations that are incomplete or not yet reviewed may stay in this repository before they are included in stable Starcat releases.

## How to help?

If you want to help with Starcat localization either once or regularly, just join the conversation in the [Starcat localization issues](https://github.com/dong4j/starcat-localization/issues). If your language is not listed yet, feel free to create a new issue for that language.

The localization process is simple:

1. Install the free Xcode from the Mac App Store.
2. Download the `.xcloc` package for your language from `Translation Packages/`.
3. Open the `.xcloc` package with Xcode.
4. Check `Glossary/` when you are not sure how a product term should be translated.
5. Attach your edited `.xcloc` package in an issue comment, or open a pull request if you are comfortable with Git.

You do not need to understand the Starcat codebase. You will receive help along the way, so do not worry about the technical details.

Advanced contributors can fork this repository and submit pull requests, but this is optional. Issue comments with edited files are welcome.

## Translation Guidelines

- Keep placeholders exactly as they are, such as `%@`, `%1$@`, `%d`, and `%%`.
- Preserve product names such as `Starcat`, `GitHub`, `OpenSSF`, `CodeFlow`, and `CodebaseMemory`.
- Keep UI text concise. Starcat is a dense macOS app, and long text can break layouts.
- Do not translate technical terms blindly. Prefer the glossary when available.
- Avoid changing keys. Only edit localization values.
- Keep each language in its own `.xcloc` package. Do not add a full `Localizable.xcstrings` file to this repository.

## Glossaries

For some localizations, a Starcat glossary is available:

- [English](Glossary/en.md)
- [Simplified Chinese](Glossary/zh-Hans.md)

## Apple Localization Terms Glossary

For standard macOS and Apple platform terms, also check the non-official glossary site by [Kishikawa Katsumi](https://github.com/kishikawakatsumi):

- [Apple Localization Terms Glossary](https://applelocalization.com/macos)

## Maintainer Import Workflow

Starcat maintainers import contributed packages back into the app with the support script in the main Starcat workspace:

```bash
supports/scripts/starcat-localization.py import \
  --package "supports/starcat-localization/Translation Packages/zh-Hans.xcloc"

supports/scripts/starcat-localization.py import-all
```

The script updates `Starcat/Resources/Localizable.xcstrings` from the submitted `.xcloc` package. The public localization repository should stay package-based.

## Useful Links

- Starcat website: https://starcat.ink
- Public support repository: https://github.com/dong4j/starcat-pro
- Issue tracker: https://github.com/dong4j/starcat-localization/issues
