# Contributing

Thank you for helping localize Starcat.

## Easiest Workflow

1. Open or join an issue for your language.
2. Download the latest `Starcat Localizations/Localizable.xcstrings`.
3. Open it in Xcode.
4. Edit only localization values.
5. Attach the edited `.xcstrings` file in an issue comment.

This is the recommended workflow for non-Git contributors.

## Pull Request Workflow

1. Fork this repository.
2. Open `Starcat Localizations/Localizable.xcstrings` in Xcode.
3. Edit only localization values.
4. Run `jq empty "Starcat Localizations/Localizable.xcstrings"`.
5. Open a pull request and describe the language and scope of your changes.

## Non-Git Workflow

If you do not use Git, open an issue and attach the edited `.xcstrings` file. Include:

- Language code.
- What changed.
- Whether this is a full translation, a correction, or a terminology update.

You do not need to understand the app source code. Ask questions in the issue if anything is unclear.

## Review Rules

- Translations should be natural, not literal.
- UI strings should remain short enough for macOS controls.
- Placeholders must be preserved exactly.
- Product terms should follow `Glossary/`.
- Incomplete languages may wait until they reach a reviewable completion level before being imported into Starcat releases.
