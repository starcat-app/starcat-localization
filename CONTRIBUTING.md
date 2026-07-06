# Contributing

Thank you for helping localize Starcat.

## Easiest Workflow

1. Open or join an issue for your language.
2. Download the latest `.xcloc` package for your language from `Translation Packages/`.
3. Open the `.xcloc` package in Xcode.
4. Edit only localization values.
5. Attach the edited `.xcloc` package in an issue comment.

This is the recommended workflow for non-Git contributors.

## Pull Request Workflow

1. Fork this repository.
2. Open your language package under `Translation Packages/` in Xcode.
3. Edit only localization values.
4. Commit only the `.xcloc` package for the language you changed.
5. Open a pull request and describe the language and scope of your changes.

## Non-Git Workflow

If you do not use Git, open an issue and attach the edited `.xcloc` package. Include:

- Language code.
- What changed.
- Whether this is a full translation, a correction, or a terminology update.

You do not need to understand the app source code. Ask questions in the issue if anything is unclear.

## Review Rules

- Translations should be natural, not literal.
- UI strings should remain short enough for macOS controls.
- Placeholders must be preserved exactly.
- Product terms should follow `Glossary/`.
- Each language should stay in its own `.xcloc` package.
- Incomplete languages may wait until they reach a reviewable completion level before being imported into Starcat releases.

## Maintainer Notes

The public repository intentionally does not contain the full `Localizable.xcstrings` source file. Starcat maintainers import packages back into the app from the main Starcat workspace:

```bash
supports/scripts/starcat-localization.py import-all
```
