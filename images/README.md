# Instruction screenshots

Screenshots referenced by `instruction.md.tmpl` and `instruction-multi-user.md.tmpl`.

## Replacement workflow

Replace each PNG in-place with an updated screenshot. Keep the filename identical — the instruction templates reference these paths directly, and the build pipeline copies this folder verbatim into the delivery zip (alongside the rendered PDF, which also embeds these images).

## Slot list

| Slot | What it shows                                                        |
|------|----------------------------------------------------------------------|
| 01   | BotFather search in Telegram                                         |
| 02   | BotFather reply with bot token                                       |
| 03   | Claude Console sign-in page                                          |
| 04   | Claude Console API keys list with Create key highlighted             |
| 05   | Anthropic "Create API key" modal                                     |
| 06   | Anthropic "Save your API key" one-time reveal                        |
| 07   | Firecrawl onboarding — "What's your next step?" (step 1 of 4)        |
| 08   | Firecrawl onboarding — "Let's get you started" copy API key (step 2) |
| 09   | Firecrawl onboarding — Terms of Service acceptance (step 3)          |
| 10   | Google AI Studio welcome popup                                       |
| 11   | Google AI Studio API Keys page with Create API key highlighted       |
| 12   | Google AI Studio "Create a new key" modal                            |
| 13   | Google AI Studio API key details with key highlighted                |
| 14   | Brave Search API — Register new account form                         |
| 15   | Brave Search API — Available plans (Search "Get started")            |
| 16   | Brave Search API — Confirm subscription (Free + limit spending)      |
| 17   | Brave Search API — Payment details form                              |
| 18   | Brave Search API — API keys page with Add API key highlighted        |
| 19   | Brave Search API — "Add new API key" modal                           |
| 20   | Brave Search API — API keys list with copy icon highlighted          |
| 21   | macOS Spotlight with "Terminal" typed                                |
| 22   | Terminal after dragging install.sh — path shown                      |
| 23   | Installer prompting for Telegram bot token + Anthropic API key       |
| 24   | OpenClaw Control UI opened in browser                                |
| 25   | Empty Telegram chat with bot (Start button)                          |
| 26   | Bot's pairing-code reply                                             |
| 27   | Terminal showing successful pairing approval                         |
| 28   | Telegram with `/content-monitor setup` sent                          |
| 29   | Setup Q1 — competitor website list pasted                            |
| 30   | Facebook login page (browser opened by bot)                          |
| 31   | X (Twitter) login page (browser opened by bot)                       |
| 32   | Social login confirmed — Mst Juthi recognised                        |
| 33   | Setup Q5 — Firecrawl + Google AI key prompts                         |
| 34   | Setup Q5 — Brave Search key prompt                                   |
| 35   | Setup Q7 — daily schedule + first-time crawl starting                |
| 36   | Setup complete — configuration summary table                         |
| 37   | `run content pipeline` — today's content candidates                  |
| 38   | Pipeline — which post to use (1 / 2 / both)                          |
| 39   | Pipeline — post approval prompt and `approve` sent                   |
| 40   | Published Facebook post by the assistant                             |
| 41   | Pipeline summary — platform post status                              |

## Constraints

- Filename format: `NN-descriptive-slug.png` (zero-padded, kebab-case).
- Recommended width: 1200–1600 px (retina-friendly without bloating the PDF).
- PNG only (Puppeteer handles JPEG too, but the templates reference `.png`).
- Keep file size < 500 KB per image where practical; the pipeline does not compress them.
