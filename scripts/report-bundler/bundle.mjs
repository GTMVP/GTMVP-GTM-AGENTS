#!/usr/bin/env node
/**
 * GTMVP Report Bundler — Markdown → PDF
 *
 * Invocation:
 *   node bundle.mjs <path-to-markdown.md>
 *
 * On success: prints {"success": true, "pdfPath": "<absolute path>"} and exits 0.
 * On validation failure: prints {"success": false, "error": "..."} and exits 2.
 * On render failure: prints {"success": false, "error": "...", "fallback": "..."} and exits 1.
 *
 * PDF is a convenience artifact. Markdown remains the source of truth.
 */

import { existsSync, statSync, readFileSync } from "node:fs";
import { resolve, dirname, basename, extname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function emit(payload, exitCode) {
  process.stdout.write(JSON.stringify(payload) + "\n");
  process.exit(exitCode);
}

async function main() {
  const inputArg = process.argv[2];

  if (!inputArg) {
    emit(
      {
        success: false,
        error:
          "Usage: node bundle.mjs <path-to-markdown.md> — missing required markdown path argument.",
      },
      2,
    );
  }

  const mdPath = resolve(process.cwd(), inputArg);

  if (!existsSync(mdPath)) {
    emit(
      {
        success: false,
        error: `Input markdown file does not exist: ${mdPath}`,
      },
      2,
    );
  }

  if (extname(mdPath).toLowerCase() !== ".md") {
    emit(
      {
        success: false,
        error: `Input file must have a .md extension: ${mdPath}`,
      },
      2,
    );
  }

  const stats = statSync(mdPath);
  if (!stats.isFile()) {
    emit(
      {
        success: false,
        error: `Input path is not a regular file: ${mdPath}`,
      },
      2,
    );
  }

  const pdfPath = join(
    dirname(mdPath),
    basename(mdPath, extname(mdPath)) + ".pdf",
  );

  const stylesheetPath = join(__dirname, "styles.css");
  if (!existsSync(stylesheetPath)) {
    emit(
      {
        success: false,
        error: `Stylesheet missing: ${stylesheetPath}`,
        fallback: `Markdown remains the source of truth at ${mdPath}`,
      },
      1,
    );
  }

  let mdToPdf;
  try {
    ({ mdToPdf } = await import("md-to-pdf"));
  } catch (err) {
    emit(
      {
        success: false,
        error: `Failed to load md-to-pdf — run "npm install" in ${__dirname}. Underlying error: ${err.message}`,
        fallback: `Markdown remains the source of truth at ${mdPath}`,
      },
      1,
    );
  }

  try {
    const pdf = await mdToPdf(
      { path: mdPath },
      {
        dest: pdfPath,
        stylesheet: [stylesheetPath],
        document_title: "GTMVP Audit Report",
        pdf_options: {
          format: "Letter",
          margin: {
            top: "1in",
            bottom: "1in",
            left: "0.75in",
            right: "0.75in",
          },
          printBackground: true,
          displayHeaderFooter: true,
          headerTemplate: `<div style="font-size:9px;width:100%;text-align:center;color:#666;font-family:sans-serif;">GTMVP Audit Report</div>`,
          footerTemplate: `<div style="font-size:9px;width:100%;text-align:center;color:#666;font-family:sans-serif;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>`,
        },
      },
    );

    if (!pdf || !existsSync(pdfPath)) {
      emit(
        {
          success: false,
          error: "md-to-pdf returned without writing a PDF file.",
          fallback: `Markdown remains the source of truth at ${mdPath}`,
        },
        1,
      );
    }

    emit({ success: true, pdfPath }, 0);
  } catch (err) {
    emit(
      {
        success: false,
        error: `PDF render failed: ${err && err.message ? err.message : String(err)}`,
        fallback: `Markdown remains the source of truth at ${mdPath}`,
      },
      1,
    );
  }
}

main().catch((err) => {
  emit(
    {
      success: false,
      error: `Unexpected bundler error: ${err && err.message ? err.message : String(err)}`,
      fallback: "Markdown remains the source of truth (path unknown — input parsing failed).",
    },
    1,
  );
});
