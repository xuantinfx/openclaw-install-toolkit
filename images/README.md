# Instruction screenshots

Placeholder screenshots referenced by `instruction.md.tmpl` and `instruction-multi-user.md.tmpl`.

## Replacement workflow

Replace each PNG in-place with the real screenshot. Keep the filename identical — the instruction templates reference these paths directly, and the build pipeline copies this folder verbatim into the delivery zip (alongside the rendered PDF, which also embeds these images).

## Slot list

| Slot | What it shows                                  |
|------|------------------------------------------------|
| 01   | BotFather search in Telegram                   |
| 02   | BotFather reply with bot token                 |
| 03   | Anthropic console sign-up page                 |
| 04   | Anthropic "Create Key" dialog                  |
| 05   | Anthropic key reveal (copy-once screen)        |
| 06   | Firecrawl dashboard                            |
| 07   | Firecrawl "Create API Key" button              |
| 08   | Google AI Studio landing                       |
| 09   | Google AI Studio "Create API Key" dialog       |
| 10   | Brave Search API dashboard                     |
| 11   | Brave "Generate API Key" button                |
| 12   | macOS Spotlight with "Terminal" typed          |
| 13   | Terminal window open                           |
| 14   | Finder showing the downloaded zip              |
| 15   | Unzipped toolkit folder contents               |
| 16   | Way A: dragging install.sh into Terminal       |
| 17   | Way B: right-click → Open on install.command   |
| 18   | "Unidentified developer" Gatekeeper dialog     |
| 19   | Installer running mid-way                      |
| 20   | Installer success output                       |
| 21   | OpenClaw Control UI opened in browser          |
| 22   | Sending "hi" to bot in Telegram                |
| 23   | Bot's pairing-request reply                    |
| 24   | Terminal after successful pairing approval     |
| 25   | Bot starting `/content-monitor setup` flow     |
| 26   | Bot reporting successful `manual test run`     |

## Constraints

- Filename format: `NN-descriptive-slug.png` (zero-padded, kebab-case).
- Recommended width: 1200–1600 px (retina-friendly without bloating the PDF).
- PNG only (Puppeteer handles JPEG too, but the templates reference `.png`).
- Keep file size < 500 KB per image to keep the delivery zip reasonable.
