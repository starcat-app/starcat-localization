# Starcat Localization

<!-- starcat-promo:start -->
<div align="center">
<a href="https://starcat.ink"><img src="https://raw.githubusercontent.com/starcat-app/starcat-pro/main/banner.webp" width="100%" alt="Starcat" /></a>

<p><strong>Public localization collaboration repository for Starcat.</strong></p>
<p>Starcat is a native macOS app that turns GitHub Stars into a searchable, organized and AI-assisted knowledge base. It supports README rendering, tags, private notes, release tracking, repository health signals, AI summaries, semantic search, browser plugin workflows and self-hostable support APIs.</p>

<a href="https://github.com/starcat-app/homebrew-starcat"><img src="https://img.shields.io/badge/Install%20with-Homebrew-FBBF24?style=for-the-badge&logo=homebrew&logoColor=white" width="220" alt="Install with Homebrew"/></a>
<br/>
<sub><a href="./README-ZH.md">中文说明</a></sub>
</div>

<div align="center">
<a href="https://starcat.ink"><img src="https://img.shields.io/badge/website-starcat.ink-38BDF8?style=flat&color=blue" alt="website"/></a>
<a href="https://github.com/starcat-app/starcat-pro"><img src="https://img.shields.io/badge/support-starcat--pro-lightgrey.svg?style=flat&color=blue" alt="support"/></a>
<a href="https://github.com/starcat-app/homebrew-starcat"><img src="https://img.shields.io/badge/install-homebrew-lightgrey.svg?style=flat&color=blue" alt="homebrew"/></a>
<a href="https://github.com/starcat-app/starcat-localization"><img src="https://img.shields.io/badge/localization-open-lightgrey.svg?style=flat&color=blue" alt="localization"/></a>
</div>

<div align="center">
<img width="900" src="https://raw.githubusercontent.com/starcat-app/starcat-pro/main/main.webp" alt="Starcat main window"/>
</div>

**Preferred install method:**

```bash
brew tap starcat-app/starcat
brew trust starcat-app/starcat
brew install --cask starcat
```

**Useful links:**

- Home: https://starcat.ink
- Download: https://starcat.ink/downloads/Starcat-1.1.0-arm64.dmg
- Public support and release notes: https://github.com/starcat-app/starcat-pro
- Homebrew tap: https://github.com/starcat-app/homebrew-starcat
- Browser plugins: [Chrome](https://github.com/starcat-app/starcat-chrome-plugin) / [Safari](https://github.com/starcat-app/starcat-safari-plugin)
- Localization: https://github.com/starcat-app/starcat-localization

**Starcat ecosystem:**

- [starcat-sharing-api](https://github.com/starcat-app/starcat-sharing-api)
- [starcat-trending-api](https://github.com/starcat-app/starcat-trending-api)
- [starcat-weekly-api](https://github.com/starcat-app/starcat-weekly-api)
- [starcat-wiki-api](https://github.com/starcat-app/starcat-wiki-api)
- [starcat-recommend-api](https://github.com/starcat-app/starcat-recommend-api)
- [starcat-discovery-api](https://github.com/starcat-app/starcat-discovery-api)
<!-- starcat-promo:end -->

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

If you want to help with Starcat localization either once or regularly, just join the conversation in the [Starcat localization issues](https://github.com/starcat-app/starcat-localization/issues). If your language is not listed yet, feel free to create a new issue for that language.

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
- Public support repository: https://github.com/starcat-app/starcat-pro
- Issue tracker: https://github.com/starcat-app/starcat-localization/issues
