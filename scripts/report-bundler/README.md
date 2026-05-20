# GTMVP Report Bundler

Markdown → PDF renderer for `/gtm-audit` synthesis documents. Produces a shareable
PDF artifact next to the source markdown. The markdown remains authoritative; the
PDF is convenience-only.

## Setup

Run once, in this directory:

```
npm install
```

This installs `md-to-pdf` and its bundled Puppeteer + headless Chromium. Network
access is required during install — Puppeteer downloads its own Chromium build
(~150 MB) into `node_modules/`.

## Usage

From the plugin root:

```
node scripts/report-bundler/bundle.mjs path/to/synthesis.md
```

The bundler writes `path/to/synthesis.pdf` alongside the markdown.

## Output

The bundler emits a single JSON line to stdout:

- Success: `{"success": true, "pdfPath": "<absolute path to .pdf>"}` — exit 0
- Validation error (missing file, wrong extension): `{"success": false, "error": "..."}` — exit 2
- Render error (Puppeteer crash, missing dep, etc.):
  `{"success": false, "error": "...", "fallback": "Markdown remains the source of truth at <path>"}` — exit 1

The `/gtm-audit` command treats exit-1 as a soft warning, not a hard failure.

## Troubleshooting

**Puppeteer fails to download Chromium during `npm install`:**

- Check `npm config get puppeteer_skip_download` — must be `undefined` or `false`.
- Corporate proxies or restricted networks can block the Chromium CDN. Try from
  a different network, or set `PUPPETEER_DOWNLOAD_HOST` to a mirror.
- If you have Chrome already installed and want to use it instead, set
  `PUPPETEER_EXECUTABLE_PATH` to the Chrome binary path before invoking the
  bundler. (Not the default; not recommended for reproducibility.)

**Windows Defender / SmartScreen flags the Chromium binary:**

- The Chromium build downloaded by Puppeteer is unsigned. Add an exclusion for
  `scripts\report-bundler\node_modules\puppeteer\.local-chromium\` if Defender
  quarantines it.

**`md-to-pdf` returns without writing a PDF:**

- Confirm the markdown is well-formed (no malformed front-matter, balanced code
  fences). The bundler surfaces the underlying Puppeteer error in `error`.

**PDF renders but tables / code blocks look wrong:**

- The stylesheet lives at `styles.css` in this directory. Adjust and re-run.
  No npm step needed for CSS changes.

## Why md-to-pdf

Chosen over pandoc, wkhtmltopdf, and chrome-headless-render-pdf because:

- **Zero external installs.** Bundles Puppeteer + Chromium. No system pandoc, no
  wkhtmltopdf binary, no LaTeX. `npm install` is the only setup step.
- **GFM-native.** Tables, fenced code blocks, task lists, strikethrough all
  render correctly out of the box (it uses `marked` under the hood).
- **Cross-platform.** Works on Windows, macOS, Linux identically — important
  because GTMVP runs primarily on Windows.
- **Style via CSS.** Standard CSS in `styles.css`; no template language to
  learn. Quick iteration.
- **Maintained and stable.** v5.x is the current major. Used in production by
  multiple docs pipelines.
