#!/usr/bin/env node
/**
 * Plugin self-test. Validates:
 *   - Manifest is valid JSON with required fields
 *   - All agent / command / skill files have valid YAML frontmatter
 *   - Required frontmatter keys (name, description) are present
 *   - channel-taxonomy.json parses and has the expected shape
 *   - Inter-file references aren't broken (skills cited by agents exist)
 *
 * With --solver-evals flag also runs the constraint-solver eval harness:
 *   - Loads each scripts/solver-evals/*.json scenario
 *   - Invokes the matching reference runner (run-<scenario-stem>.py) via the
 *     mcp-solver venv Python
 *   - Records pass/fail per scenario; aggregates to overall solver result
 *
 * Exit code: 0 = pass, 1 = fail. Prints a summary table.
 */

import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

const errors = [];
const warnings = [];
const stats = { manifest: false, agents: 0, commands: 0, skills: 0, taxonomyAgents: 0 };

function fail(msg) { errors.push(msg); }
function warn(msg) { warnings.push(msg); }

// 1. Manifest
const manifestPath = join(ROOT, ".claude-plugin", "plugin.json");
if (!existsSync(manifestPath)) {
  fail("Missing .claude-plugin/plugin.json");
} else {
  try {
    const m = JSON.parse(readFileSync(manifestPath, "utf8"));
    if (!m.name) fail("plugin.json: missing 'name'");
    if (!m.version) fail("plugin.json: missing 'version'");
    if (!m.description) fail("plugin.json: missing 'description'");
    stats.manifest = true;
    stats.manifestVersion = m.version;
    stats.manifestName = m.name;
  } catch (e) {
    fail(`plugin.json: invalid JSON — ${e.message}`);
  }
}

// 2. Channel taxonomy
const taxonomyPath = join(ROOT, "data", "channel-taxonomy.json");
if (!existsSync(taxonomyPath)) {
  fail("Missing data/channel-taxonomy.json");
} else {
  try {
    const t = JSON.parse(readFileSync(taxonomyPath, "utf8"));
    if (!Array.isArray(t.agents)) fail("channel-taxonomy.json: 'agents' is not an array");
    else {
      stats.taxonomyAgents = t.agents.length;
      const requiredKeys = ["agent_id", "name", "macro_channel", "inputs", "outputs", "kpis", "tactics", "dependencies"];
      for (const a of t.agents) {
        for (const k of requiredKeys) {
          if (!(k in a)) {
            fail(`channel-taxonomy: agent '${a.agent_id || "<unknown>"}' missing key '${k}'`);
            break;
          }
        }
      }
    }
  } catch (e) {
    fail(`channel-taxonomy.json: invalid JSON — ${e.message}`);
  }
}

// 3. YAML frontmatter validator (lightweight — checks --- delimiters and required keys)
// Normalizes CRLF (Windows) → LF before parsing so Windows-checked-out files validate.
function parseFrontmatter(rawContent, filename) {
  const content = rawContent.replace(/\r\n/g, "\n");
  if (!content.startsWith("---\n")) {
    fail(`${filename}: missing opening '---' frontmatter delimiter`);
    return null;
  }
  const end = content.indexOf("\n---\n", 4);
  if (end === -1) {
    fail(`${filename}: missing closing '---' frontmatter delimiter`);
    return null;
  }
  const raw = content.slice(4, end);
  const fm = {};
  for (const line of raw.split("\n")) {
    if (!line.trim() || line.trim().startsWith("#")) continue;
    const colonIdx = line.indexOf(":");
    if (colonIdx === -1) continue;
    const key = line.slice(0, colonIdx).trim();
    const value = line.slice(colonIdx + 1).trim().replace(/^["']|["']$/g, "");
    if (key && !line.startsWith(" ")) fm[key] = value;
  }
  return fm;
}

function validateFrontmatterFile(path, filename, requiredKeys) {
  const content = readFileSync(path, "utf8");
  const fm = parseFrontmatter(content, filename);
  if (!fm) return null;
  for (const k of requiredKeys) {
    if (!fm[k]) fail(`${filename}: missing frontmatter key '${k}'`);
  }
  return fm;
}

// 4. Agents
const agentsDir = join(ROOT, "agents");
const agentNames = new Set();
if (existsSync(agentsDir)) {
  const files = readdirSync(agentsDir).filter((f) => f.endsWith(".md"));
  for (const f of files) {
    const fm = validateFrontmatterFile(join(agentsDir, f), `agents/${f}`, ["name", "description"]);
    if (fm) {
      const expectedName = f.replace(/\.md$/, "");
      if (fm.name !== expectedName) {
        warn(`agents/${f}: frontmatter name '${fm.name}' doesn't match filename '${expectedName}'`);
      }
      if (fm.name) agentNames.add(fm.name);
      stats.agents++;
    }
  }
}

// 5. Commands
const commandsDir = join(ROOT, "commands");
if (existsSync(commandsDir)) {
  const files = readdirSync(commandsDir).filter((f) => f.endsWith(".md"));
  for (const f of files) {
    validateFrontmatterFile(join(commandsDir, f), `commands/${f}`, ["description"]);
    stats.commands++;
  }
}

// 6. Skills
const skillsDir = join(ROOT, "skills");
const skillNames = new Set();
if (existsSync(skillsDir)) {
  const dirs = readdirSync(skillsDir, { withFileTypes: true }).filter((d) => d.isDirectory());
  for (const d of dirs) {
    const skillFile = join(skillsDir, d.name, "SKILL.md");
    if (!existsSync(skillFile)) {
      fail(`skills/${d.name}: missing SKILL.md`);
      continue;
    }
    const fm = validateFrontmatterFile(skillFile, `skills/${d.name}/SKILL.md`, ["name", "description"]);
    if (fm) {
      if (fm.name !== d.name) {
        warn(`skills/${d.name}/SKILL.md: frontmatter name '${fm.name}' doesn't match dir name '${d.name}'`);
      }
      if (fm.name) skillNames.add(fm.name);
      stats.skills++;
    }
  }
}

// 7. Cross-reference check (lightweight) — agents reference framework skills by name
const expectedSkills = ["gtm-output-schemas", "competitor-discovery-cot", "porters-five-forces", "swot-analysis", "tam-sam-som-horizons", "marketing-channel-scoring"];
for (const s of expectedSkills) {
  if (!skillNames.has(s)) fail(`Expected skill '${s}' not found`);
}

const expectedAgents = [
  "analytics-agent", "technical-seo-agent", "local-seo-agent",
  "seo-keyword-agent", "content-strategy-agent", "email-automation-agent",
  "social-scheduler-agent", "video-content-agent",
  "backlink-builder-agent", "pr-outreach-agent", "ad-optimizer-agent",
  "ppc-agent", "influencer-connect-agent",
  "podcast-agent", "conversion-agent", "mobile-marketing-agent",
  "competitor-mapper-agent", "brand-strategist-agent",
];
for (const a of expectedAgents) {
  if (!agentNames.has(a)) fail(`Expected agent '${a}' not found`);
}

// 8. Solver evals (opt-in via --solver-evals flag)
const runSolverEvals = process.argv.includes("--solver-evals");
const solverResults = [];
if (runSolverEvals) {
  const evalsDir = join(ROOT, "scripts", "solver-evals");
  if (!existsSync(evalsDir)) {
    warn("--solver-evals requested but scripts/solver-evals/ does not exist");
  } else {
    // Find Python — prefer mcp-solver venv, fall back to system python
    const venvPython =
      process.platform === "win32"
        ? "C:\\Users\\User\\Projects\\mcp-solver\\.venv\\Scripts\\python.exe"
        : `${process.env.HOME}/Projects/mcp-solver/.venv/bin/python`;
    const pythonBin = existsSync(venvPython) ? venvPython : "python";

    // Group scenario files by the runner script that handles them.
    // Convention: run-<prefix>.py handles all <prefix>-*.json scenarios.
    // Example: run-channel-score.py handles channel-score-1.json, channel-score-2.json, ...
    const files = readdirSync(evalsDir).filter((f) => f.endsWith(".json"));
    for (const f of files) {
      const stem = f.replace(/\.json$/, "");
      // Find the matching runner: strip trailing -N suffix to get the prefix
      const prefix = stem.replace(/-\d+$/, "");
      const runner = join(evalsDir, `run-${prefix}.py`);
      if (!existsSync(runner)) {
        fail(`solver-evals: no runner found for ${f} (expected ${prefix}.py)`);
        continue;
      }
      const scenarioPath = join(evalsDir, f);
      try {
        const output = execSync(`"${pythonBin}" "${runner}" "${scenarioPath}"`, {
          encoding: "utf8",
          stdio: ["ignore", "pipe", "pipe"],
        });
        const parsed = JSON.parse(output);
        solverResults.push({ file: f, ...parsed });
      } catch (e) {
        // Non-zero exit means scenario failed; output is still on stdout.
        const stdout = e.stdout || "";
        let parsed = null;
        try {
          parsed = JSON.parse(stdout);
        } catch {
          parsed = { error: e.message.slice(0, 200) };
        }
        solverResults.push({ file: f, ...parsed, exitCode: e.status });
        if (!parsed?.allPass) {
          fail(`solver-evals: ${f} failed (${JSON.stringify(parsed?.passes ?? parsed?.error)})`);
        }
      }
    }
  }
}

// 9. Print results
console.log("\n=== GTMVP-GTM-AGENTS Plugin Validation ===\n");
console.log(`Manifest:       ${stats.manifest ? "OK" : "MISSING"}${stats.manifestName ? ` (${stats.manifestName} v${stats.manifestVersion})` : ""}`);
console.log(`Agents:         ${stats.agents} files`);
console.log(`Commands:       ${stats.commands} files`);
console.log(`Skills:         ${stats.skills} dirs`);
console.log(`Taxonomy:       ${stats.taxonomyAgents} agents in channel-taxonomy.json`);

if (runSolverEvals) {
  const passed = solverResults.filter((r) => r.allPass).length;
  const total = solverResults.length;
  console.log(`Solver evals:   ${passed}/${total} passing`);
  for (const r of solverResults) {
    const tag = r.allPass ? "PASS" : "FAIL";
    let details = `time=${r.solveTimeMs}ms`;
    if (r.solverStatus === "infeasible") {
      details = `unsat-core=[${(r.unsatCore || []).join(",")}]`;
    } else if (r.solverObjective !== undefined) {
      details = `obj=${r.solverObjective}, greedy=${r.greedyObjective}, ${details}`;
    } else if (r.minDist !== undefined) {
      details = `minDist=${r.minDist}, ${details}`;
    } else if (r.selectedCompetitors) {
      details = `selected=${r.selectedCompetitors.length}, uncovered=${(r.uncoveredDimensions || []).length}, ${details}`;
    }
    console.log(`  ${tag}  ${r.file}: ${details}`);
  }
}

if (warnings.length > 0) {
  console.log(`\nWarnings (${warnings.length}):`);
  for (const w of warnings) console.log(`  - ${w}`);
}

if (errors.length > 0) {
  console.log(`\nErrors (${errors.length}):`);
  for (const e of errors) console.log(`  - ${e}`);
  console.log("\nFAIL");
  process.exit(1);
}

console.log("\nPASS");
process.exit(0);
