#!/usr/bin/env node
/**
 * Port the AGENT_REGISTRY array from the donor TypeScript file
 * (marketing-ai-platform/backend/src/agents/registry.ts) into
 * data/channel-taxonomy.json.
 *
 * Strategy: locate the array literal, strip TS-only syntax,
 * eval as a JS expression, then JSON.stringify with metadata wrapper.
 *
 * Donor file is a trusted source (Steve's own repo, MIT) — eval is acceptable
 * for a one-shot porting script. Do not generalize this to untrusted inputs.
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DONOR =
  "C:/Users/User/Downloads/marketing-ai-platform-analysis/backend/src/agents/registry.ts";
const OUT = `${__dirname}/../data/channel-taxonomy.json`;

const ts = readFileSync(DONOR, "utf8");

// Find the start of the array literal — anchor on the `=` after
// the type annotation `AgentDefinition[]` so we don't grab the
// empty brackets in the type itself.
const sentinel = "AGENT_REGISTRY: AgentDefinition[] = ";
const sentIdx = ts.indexOf(sentinel);
if (sentIdx === -1) {
  console.error("Could not find AGENT_REGISTRY in donor file");
  process.exit(1);
}
const eqIdx = sentIdx + sentinel.length - 1; // points at `= `
const arrayStart = ts.indexOf("[", eqIdx);
const tail = ts.slice(arrayStart);

// Walk the tail counting bracket depth, ignoring brackets inside strings
let depth = 0;
let arrayEnd = -1;
let inString = false;
let stringChar = "";
let escape = false;
let inLineComment = false;
let inBlockComment = false;

for (let i = 0; i < tail.length; i++) {
  const ch = tail[i];
  const next = tail[i + 1];

  if (inLineComment) {
    if (ch === "\n") inLineComment = false;
    continue;
  }
  if (inBlockComment) {
    if (ch === "*" && next === "/") {
      inBlockComment = false;
      i++;
    }
    continue;
  }
  if (escape) {
    escape = false;
    continue;
  }
  if (inString) {
    if (ch === "\\") {
      escape = true;
      continue;
    }
    if (ch === stringChar) inString = false;
    continue;
  }
  if (ch === "/" && next === "/") {
    inLineComment = true;
    i++;
    continue;
  }
  if (ch === "/" && next === "*") {
    inBlockComment = true;
    i++;
    continue;
  }
  if (ch === "'" || ch === '"' || ch === "`") {
    inString = true;
    stringChar = ch;
    continue;
  }
  if (ch === "[" || ch === "{") depth++;
  if (ch === "]" || ch === "}") {
    depth--;
    if (depth === 0 && ch === "]") {
      arrayEnd = i;
      break;
    }
  }
}

if (arrayEnd === -1) {
  console.error("Could not find end of AGENT_REGISTRY array");
  process.exit(1);
}

const arrayLiteral = tail.slice(0, arrayEnd + 1);

// eslint-disable-next-line no-eval
const agents = eval(`(${arrayLiteral})`);

if (!Array.isArray(agents) || agents.length === 0) {
  console.error("Eval produced unexpected result:");
  console.error("  typeof:", typeof agents);
  console.error("  isArray:", Array.isArray(agents));
  console.error("  length:", agents?.length);
  console.error("  arrayLiteral length:", arrayLiteral.length);
  console.error("  arrayLiteral first 200 chars:", arrayLiteral.slice(0, 200));
  console.error("  arrayLiteral last 200 chars:", arrayLiteral.slice(-200));
  process.exit(1);
}

// Build the macro_channel set from data, dedup
const macroChannels = Array.from(
  new Set(agents.map((a) => a.macro_channel).filter(Boolean))
).sort();

const output = {
  metadata: {
    name: "GTM Channel Taxonomy",
    version: "0.1.0",
    source: "marketing-ai-platform/backend/src/agents/registry.ts",
    description:
      "Structured catalog of agentic marketing modules. Each entry defines inputs/outputs/KPIs/tactics/dependencies for one micro-channel, suitable as a reference taxonomy for channel scoring, audit work, and channel-mix recommendations.",
    macro_channels: macroChannels,
    agent_count: agents.length,
    ported_at: new Date().toISOString(),
  },
  agents,
};

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify(output, null, 2));
console.log(
  `Wrote ${agents.length} agents across ${macroChannels.length} macro channels to ${OUT}`
);
