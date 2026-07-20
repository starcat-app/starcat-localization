# Starcat Glossary

This glossary records product terms that should stay consistent across Starcat UI, documentation, release notes, support issues, and localization work.

## Product And Distribution

| Term | Preferred Usage |
| --- | --- |
| Starcat | Product name. Do not translate. |
| Starcat Pro | Product tier / public support name. Do not translate. |
| Direct build | The non-App-Store macOS build distributed from the Starcat website. |
| App Store build | The App Store distribution channel. Keep distinct from Direct build. |
| Homebrew tap | The Homebrew repository `starcat-app/homebrew-starcat`. |
| Cask | Homebrew cask package. Use when referring to `Casks/starcat.rb`. |
| Sparkle | In-app update framework. Do not translate. |
| appcast | Sparkle update feed. Keep lowercase unless starting a sentence. |
| Changelog | Starcat release notes. |
| Release notes | User-facing list of changes for an app version. |
| Pro license | Starcat Pro entitlement. Use only when the purchase/license flow is discussed. |
| Entitlement | Runtime permission or paid capability state. |

## GitHub And Repository Concepts

| Term | Preferred Usage |
| --- | --- |
| GitHub | Product name. Do not translate. |
| GitHub Stars | Use as the GitHub feature name. Avoid shortening to only "stars" when the context may be unclear. |
| Star / Unstar | GitHub action names. Use consistently for starring and unstarring repositories. |
| starred repository | A repository the user has starred on GitHub. |
| repository / repo | Use "repository" in formal copy and "repo" in compact UI when space is limited. |
| owner | GitHub account or organization that owns a repository. |
| topic | GitHub repository topic. |
| README | Keep uppercase. It refers to the repository README file/content. |
| GitHub Release | A release published by a GitHub repository. Do not shorten to app version. |
| Issues | GitHub Issues unless the UI is clearly generic. |
| Pull Request / PR | Use "Pull Request" in formal copy and "PR" in compact UI. |
| fork | GitHub fork state. |
| archived | GitHub archived repository state. |
| default branch | The repository's default branch. |
| clone URL | URL used to clone a repository. |

## Organization And Library

| Term | Preferred Usage |
| --- | --- |
| tag | User-defined Starcat tag. |
| Tags | Starcat tag section or feature. |
| note | Private user note attached to a repository. |
| private notes | User-owned local notes. |
| status | Reading or usage status, such as unread, reading, using, abandoned. |
| smart collection | Rule-based collection in Starcat. |
| library | Starcat knowledge/library scope, not a file system library. |
| import | Bringing user data into Starcat. |
| export | Writing Starcat user data out to a file. |
| JSON import/export | Starcat data portability workflow. |
| cache | Rebuildable repository/readme/runtime data. |
| local data | User-created data such as tags, notes, status, and preferences. |

## Search And Discovery

| Term | Preferred Usage |
| --- | --- |
| Search Center | Starcat search surface. Keep title case when naming the feature. |
| full-text search | Local keyword search. |
| FTS5 | SQLite full-text search engine. Do not translate. |
| semantic search | Meaning-based AI/embedding search. |
| embedding | Vector representation for semantic search. |
| RRF | Reciprocal Rank Fusion. Expand on first mention if needed. |
| filter | Narrowing results by field or condition. |
| sort | Ordering results. |
| Explore | Starcat discovery entry. Keep as feature name when used in UI. |
| Trending | GitHub Trending or Starcat Trending section. |
| Discovery | Starcat discovery backend / feature. |
| Weekly | Weekly source section. |
| recommendation | Suggested related repository. |
| similar repository | Repository recommendation based on similarity. |

## AI And Code Intelligence

| Term | Preferred Usage |
| --- | --- |
| AI | Use uppercase. |
| BYOK | Bring your own key. In Starcat, users configure their own model provider or API key. |
| provider | AI or external search provider. |
| API key | Credential used to access a provider. |
| token | Authentication token; avoid using it for generic API keys unless the UI is about tokens. |
| model | AI model. |
| prompt | Prompt sent to an AI model. |
| summary | AI-generated repository summary. |
| README translation | Translation of repository README content. |
| chat | AI conversation surface. |
| context | Repository or runtime context given to AI. |
| Agent Workspace | Starcat agent workspace. Keep title case. |
| Built-in Agents | Built-in Starcat agents. |
| artifact | Generated file or output from an agent run. |
| CodeFlow | Starcat feature name. Do not translate. |
| CodebaseMemory | Technology name. Do not translate. |
| code graph | Repository code relationship graph. |
| RAG | Retrieval-Augmented Generation. Expand on first mention if needed. |

## Health, Releases, And Activity

| Term | Preferred Usage |
| --- | --- |
| Release subscription | User subscription to repository releases. |
| timeline | Activity or release timeline. |
| unread / read | Reading state for activity or releases. |
| Repo Health | Starcat repository health feature. |
| health score | Numeric or graded repository health signal. |
| OpenSSF Scorecard | Official security scorecard name. Keep the official name. |
| service health | Availability/health status of Starcat services. |
| warmup | Background preparation work after sync. |
| prefetch | Background fetching before the user opens a resource. |
| sync | Synchronization with GitHub or backend services. |

## Browser Plugin And Support APIs

| Term | Preferred Usage |
| --- | --- |
| Browser Plugin | Starcat browser companion feature. |
| Chrome Plugin | Chrome/Chromium extension package. |
| Safari WebExtension | Safari extension package. Keep official Apple term. |
| companion | Browser-to-Starcat helper workflow. |
| local server | Local HTTP server used by the companion integration. |
| support API | Starcat backend support service. |
| self-host | Running a Starcat API project on the user's own infrastructure. |
| sharing API | Support API for share pages. |
| trending API | Support API for trending repositories. |
| weekly API | Support API for weekly sources. |
| wiki API | Support API for wiki/documentation checks. |
| recommend API | Support API for similar repository recommendations. |
| discovery API | Support API for discovery feeds. |

## macOS And UI

| Term | Preferred Usage |
| --- | --- |
| macOS | Keep Apple's capitalization. |
| Apple Silicon | Apple processor family. Do not translate in English. |
| SwiftUI | Framework name. Do not translate. |
| Liquid Glass | Apple visual design term. Keep capitalized. |
| menu bar | macOS menu bar. |
| sidebar | Left navigation column. |
| toolbar | Top action area. |
| sheet | macOS/SwiftUI sheet. |
| popover | macOS/SwiftUI popover. |
| onboarding | First-run guided setup. |
| Settings | App settings surface. |
| Diagnostics | Diagnostic logs and troubleshooting surface. |
| About | App about window or page. |
