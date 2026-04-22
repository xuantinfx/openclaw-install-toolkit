---
phase: 02
status: completed
effort: medium
---

# Phase 02 — Build render pipeline

## Context
Standalone Node script `scripts/render-pdf.mjs` takes a `.md.tmpl`, substitutes 3 variables, prepends a shared legal header, and emits a PDF styled via `scripts/pdf-style.css`. Designed to be called twice by `build-delivery.sh` (single + multi), but also runnable standalone for iteration.

## Key Insights
- No template engine needed for 3 vars — a tiny `replaceAll` loop is enough (YAGNI).
- Prepending legal header via string concat (before MD parsing) keeps ONE pipeline — no separate "merge" step in md-to-pdf.
- md-to-pdf accepts a `dest` path and a `stylesheet` path — both CLI-like but we'll use the JS API (`mdToPdf({ content }, { dest, stylesheet_encoding: 'utf-8', stylesheet: [...] })`) for programmatic use.
- Puppeteer ships its own Chromium; no separate browser install needed.
- `pdf-style.css` kept minimal: body font, heading sizes, code-block styling, blockquote-as-notice callout. ~30 lines.

## Requirements
- `scripts/render-pdf.mjs` accepts CLI args:
  - `--template <path>` (required) — path to `.md.tmpl`
  - `--out <path>` (required) — output PDF path
  - `--client <name>` (required) — client display name
  - `--date <YYYY-MM-DD>` (required) — delivery date
  - `--build <id>` (required) — build identifier
- Exits non-zero on missing required arg or template-read failure.
- `scripts/legal-header.md.tmpl` renders as bordered callout in the PDF (styled via `blockquote.notice` or first-blockquote selector).
- `scripts/pdf-style.css` provides: readable body font stack (system UI), heading scale, monospace code blocks, notice callout styling, `pre { overflow-wrap: break-word }`.
- `package.json`:
  - New devDep `"md-to-pdf": "^5"` (check latest on install)
  - New script `"render-pdf": "node scripts/render-pdf.mjs"` (for ad-hoc invocation)

## Related Code Files
- **Create**: `scripts/render-pdf.mjs`
- **Create**: `scripts/legal-header.md.tmpl`
- **Create**: `scripts/pdf-style.css`
- **Modify**: `package.json` (devDep + script)

## Implementation Steps

### 2.1 Legal header template (`scripts/legal-header.md.tmpl`)
```markdown
> **NOTICE**
>
> This AI setup document has been exclusively developed by **Brian Lab** for client **{{client_name}}**. Any copying, use, or implementation without prior written authorization from Brian Lab is strictly prohibited and may result in legal liability under applicable copyright laws.
>
> _Delivered {{delivery_date}} — build `{{build_id}}`_

---
```

### 2.2 PDF stylesheet (`scripts/pdf-style.css`)
Sketch (keep to ~30 lines):
```css
@page { margin: 18mm 16mm; }
body { font: 11pt/1.5 -apple-system, "Segoe UI", Roboto, sans-serif; color: #222; }
h1 { font-size: 22pt; margin-top: 0; }
h2 { font-size: 15pt; margin-top: 1.4em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; }
h3 { font-size: 12pt; margin-top: 1.2em; }
code { font: 10pt/1.4 "SF Mono", Menlo, Consolas, monospace; background: #f4f4f4; padding: 1px 4px; border-radius: 3px; }
pre { background: #f7f7f7; padding: 10px 12px; border-radius: 4px; overflow-wrap: break-word; white-space: pre-wrap; }
pre code { background: transparent; padding: 0; }
blockquote { margin: 0 0 1.4em 0; padding: 12px 16px; border-left: 4px solid #b85c00; background: #fff8ef; border-radius: 4px; }
blockquote strong:first-child { color: #b85c00; letter-spacing: 0.05em; }
hr { border: 0; border-top: 1px solid #ddd; margin: 1.6em 0; }
```

### 2.3 Renderer (`scripts/render-pdf.mjs`)
Plain Node ES module. Pseudocode structure:
```javascript
#!/usr/bin/env node
import { readFile } from 'node:fs/promises';
import { mdToPdf } from 'md-to-pdf';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Parse CLI args: --template --out --client --date --build
// Validate all required; die on missing.

const here = path.dirname(fileURLToPath(import.meta.url));
const header = await readFile(path.join(here, 'legal-header.md.tmpl'), 'utf8');
const body   = await readFile(args.template, 'utf8');

const substitute = (s) => s
  .replaceAll('{{client_name}}',   args.client)
  .replaceAll('{{delivery_date}}', args.date)
  .replaceAll('{{build_id}}',      args.build);

const md = substitute(header) + '\n\n' + substitute(body);

const pdf = await mdToPdf(
  { content: md },
  { dest: args.out, stylesheet: [path.join(here, 'pdf-style.css')] }
);

if (!pdf) { console.error('render failed'); process.exit(1); }
console.log(`wrote ${args.out}`);
```
- Use Node's built-in `util.parseArgs` for arg parsing (zero extra deps).
- Do NOT HTML-escape client name — md-to-pdf handles it. (But: briefly sanity-check Puppeteer's HTML rendering escapes `<`/`&`; trust library here.)

### 2.4 package.json
Add:
```json
"devDependencies": { "md-to-pdf": "^5" },
"scripts": {
  "build-delivery": "bash scripts/build-delivery.sh",
  "build-delivery:no-zip": "bash scripts/build-delivery.sh --no-zip",
  "sync-skill": "bash scripts/sync-skill.sh",
  "render-pdf": "node scripts/render-pdf.mjs"
}
```

### 2.5 Smoke test (developer action, not committed)
Run once by hand:
```
npm install
node scripts/render-pdf.mjs \
  --template instruction.md.tmpl \
  --out /tmp/test.pdf \
  --client "Jack Carter" \
  --date "2026-04-22" \
  --build "2026-04-22-a831327"
open /tmp/test.pdf
```
Eyeball: legal header callout appears at top, content well-formatted, no broken lists.

## Todo List
- [x] Create `scripts/legal-header.md.tmpl`
- [x] Create `scripts/pdf-style.css`
- [x] Create `scripts/render-pdf.mjs` with `util.parseArgs` arg parsing
- [x] Add `md-to-pdf` devDep + `render-pdf` script to `package.json`
- [x] `npm install` locally to hydrate lockfile (if any) and confirm Puppeteer installs
- [x] Smoke-render one template to `/tmp/test.pdf`, visually verify

## Success Criteria
- `node scripts/render-pdf.mjs --template … --out … --client … --date … --build …` writes a valid PDF.
- PDF opens with legal notice callout (orange-left-border blockquote) at top containing substituted client name, date, build id.
- Instruction body renders below with proper headings and code formatting.
- Missing any `--<flag>` → renderer exits non-zero with clear message.

## Risk Assessment
- **Risk**: Puppeteer install fails (arm64/x64 mismatch, network blocked). **Mitigation**: Document troubleshooting in phase 03 README snippet; fallback plan is pandoc+wkhtmltopdf (not implemented v1).
- **Risk**: Client name containing literal `{{client_name}}` (meta) would break substitution. **Mitigation**: vanishingly unlikely; accept.
- **Risk**: CSS rendering differences across Puppeteer versions. **Mitigation**: pin md-to-pdf to `^5` exact minor; re-verify on bump.

## Security Considerations
- Renderer runs with whatever shell user ran `npm install`. No elevated perms needed.
- Client name rendered into HTML via Chromium — library escapes `<`/`&`; no XSS surface since PDF is offline.
- Template files are static repo content; no remote fetches.

## Next Steps
- Phase 03 wires this renderer into `build-delivery.sh`.
