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
4. Run the local checks below.
5. Commit only the `.xcloc` package for the language you changed.
6. Open a pull request and describe the language and scope of your changes.

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/validate_packages.py
```

The validator permits incomplete `draft` packages, but any non-empty target must
preserve placeholders and use a known XLIFF state.

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
- `needs-translation` and `needs-review-translation` are not approved translations.
- `translated`, `final`, and `signed-off` are importable states. They may come from fluent review or an explicit, recorded maintainer acceptance of AI risk.
- Translation approval does not replace in-app layout, build, or RTL acceptance before release.
- Contributors must not change `locales.json` release status in a translation pull request.

## Maintainer Notes

Each `.xcloc` contains an embedded source snapshot required by Xcode, but this
repository intentionally has no standalone runtime `Localizable.xcstrings`.
Starcat maintainers import packages back into the app from the main workspace:

```bash
supports/scripts/starcat-localization.py import-all
```

Before import, maintainers run:

```bash
supports/scripts/starcat-localization.py audit
supports/scripts/starcat-localization.py report --format json
```

The import is transactional: any invalid package prevents the catalog from being
partially updated.

### AI Draft Production

Maintainers may generate resumable AI drafts for one `draft` locale at a time:

```bash
python3 scripts/translate_draft.py --locale ja
python3 scripts/translate_draft.py --locale ja --limit 40 --apply
python3 scripts/translate_draft.py --locale ja --apply
python3 scripts/translate_draft.py --locale ja \
  --key settings.mcp.agentSetup.mcpPrompt --apply
python3 scripts/translate_draft.py --locale ja \
  --repair-protected-literals --apply
```

The first command is a dry run. `--apply` reads the API key from
`DEEPSEEK_API_KEY`, validates every response key, placeholder, executable code
block, inline code span, and URL, and writes only `needs-review-translation`.
`--key` retries an existing AI-review target; `--repair-protected-literals`
restores protected literals without calling the API. The script never promotes
AI output to `translated`.
API credentials must remain in environment variables and must never be committed.

### Maintainer AI Acceptance

A maintainer may explicitly accept complete AI drafts without claiming fluent
human review. The approval command defaults to dry-run:

```bash
python3 scripts/promote_drafts.py --all
python3 scripts/promote_drafts.py \
  --all \
  --approval-method maintainer-ai-accepted \
  --approved-by <maintainer> \
  --apply
```

The command promotes only `needs-review-translation` targets, records
`humanReviewed=false` plus source and translation digests, and leaves every
locale `draft`. It does not import the runtime Catalog, expose `AppLocale`, or
waive build, UI, or RTL release gates.
