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

## How To Help

1. Install Xcode from the Mac App Store.
2. Open `Starcat Localizations/Localizable.xcstrings` in Xcode.
3. Edit translations for your language.
4. Check the glossary before changing product terms.
5. Submit your changes by opening a pull request.

If you are not comfortable with Git, open an issue and attach the edited `.xcstrings` file. That is acceptable too.

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
