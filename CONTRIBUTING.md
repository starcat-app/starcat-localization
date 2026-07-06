# Contributing

Thank you for helping localize Starcat.

## Preferred Workflow

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

## Review Rules

- Translations should be natural, not literal.
- UI strings should remain short enough for macOS controls.
- Placeholders must be preserved exactly.
- Product terms should follow `Glossary/`.
- Incomplete languages may wait until they reach a reviewable completion level before being imported into Starcat releases.
