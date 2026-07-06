# Starcat Localization

This repository contains the public localization resources for Starcat.

Starcat is a native macOS app that turns GitHub Stars into a searchable AI knowledge base. This repository lets translators and users improve Starcat's interface text without requiring access to the private application source code.

## What Is Included

```text
Starcat Localizations/
└── Localizable.xcstrings

Glossary/
├── en.md
└── zh-Hans.md
```

- `Starcat Localizations/Localizable.xcstrings` is the Xcode String Catalog used by Starcat.
- `Glossary/` records product terms and preferred translations.

## Current Languages

- `en` — source language.
- `zh-Hans` — Simplified Chinese.

Localizations that are incomplete or not yet reviewed may stay in this repository before they are included in stable Starcat releases.

## How to help?

If you want to help with Starcat localization either once or regularly, just join the conversation in the [Starcat localization issues](https://github.com/dong4j/starcat-localization/issues). If your language is not listed yet, feel free to create a new issue for that language.

The localization process is simple:

1. Install the free Xcode from the Mac App Store.
2. Open `Starcat Localizations/Localizable.xcstrings` with Xcode.
3. Enter or improve translations for each item in your language.
4. Check `Glossary/` when you are not sure how a product term should be translated.
5. Attach your edited `.xcstrings` file in an issue comment, or open a pull request if you are comfortable with Git.

You do not need to understand the Starcat codebase. You will receive help along the way, so do not worry about the technical details.

Advanced contributors can fork this repository and submit pull requests, but this is optional. Issue comments with edited files are welcome.

## Translation Guidelines

- Keep placeholders exactly as they are, such as `%@`, `%1$@`, `%d`, and `%%`.
- Preserve product names such as `Starcat`, `GitHub`, `OpenSSF`, `CodeFlow`, and `CodebaseMemory`.
- Keep UI text concise. Starcat is a dense macOS app, and long text can break layouts.
- Do not translate technical terms blindly. Prefer the glossary when available.
- Avoid changing keys. Only edit localization values.

## Validation

Before submitting, run:

```bash
jq empty "Starcat Localizations/Localizable.xcstrings"
```

This confirms the String Catalog is still valid JSON.

## Useful Links

- Starcat website: https://starcat.ink
- Public support repository: https://github.com/dong4j/starcat-pro
- Issue tracker: https://github.com/dong4j/starcat-localization/issues
