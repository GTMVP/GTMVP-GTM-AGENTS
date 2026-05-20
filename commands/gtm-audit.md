---
description: Run a full GTM audit on a brand — orchestrates competitor mapping, brand strategy, SWOT, Porter's, channel scoring, positioning whitespace, war-gaming, MaxSAT synthesis, content calendar, and PDF render into one unified intelligence brief. Takes a URL or brand name as argument.
argument-hint: [url-or-brand-name]
---

# /gtm-audit

The flagship orchestration command for this plugin. Pipelines eleven analysis stages into a unified GTM intelligence brief — strategy through execution layer through PDF artifact.

## Argument

`$ARGUMENTS` — a website URL (preferred) or brand name. If neither is provided, ask the user before proceeding.

## Pipeline

Run these stages in order. Each stage consumes the prior stage's output. **Use the Task tool with `subagent_type` to invoke each agent so they run in isolated context windows.**

### Stage 1 — Crawl + brand context (preflight)

Fetch the brand's site (homepage, /about, /pricing, /features, /customers if present). Extract:

- Brand name + tagline
- One-sentence value proposition
- Specific products / services
- Pricing model + price tier (premium / mid-market / budget)
- Target customer signals (case-study logos, ICP language)
- Industry + sub-vertical

Persist this as the "brand context" — every downstream stage references it.

### Stage 2 — Competitor mapping

Invoke `competitor-mapper-agent` with brand context. Uses the `competitor-discovery-cot` skill (A3) to apply the cross-shop disqualifier and produce 3-6 defensible competitors, rejected candidates, and whitespace gaps. Block on output.

### Stage 3 — Brand strategy (TAM/SAM/SOM + horizons)

Invoke `brand-strategist-agent` with brand context + competitor set. Runs the 6-dimension analysis using the `tam-sam-som-horizons` skill (C2): market sizing, niche, products, opportunities (quick wins / medium / long), customer journey, brand & messaging.

### Stage 4 — Strategic SWOT

Apply the `swot-analysis` skill (B1) to brand using Stage 1+2+3. Produce S/W/O/T quadrants + cross-quadrant priorities with `stopDoing` fields. Strategic moves emitted here feed Stage 8.

### Stage 5 — Market structure (Porter's Five Forces)

Apply the `porters-five-forces` skill (C1) to the sub-vertical. Produce five-force scoring + overall attractiveness + strategic implications.

### Stage 6 — Channel scoring

Apply the `marketing-channel-scoring` skill (A1) against the 28-channel taxonomy in `data/channel-taxonomy.json`. Produce per-channel scores, rollout plan (now / next quarter / year two), and portfolio check. Active publishing channels feed Stage 10.

### Stage 7 — Positioning whitespace (NEW — A2)

Apply `/positioning-pass` logic with Stage 1+2+3 as input. Score brand + competitors on the 5-dimension positioning space (price_tier, audience_sophistication, feature_depth, channel_fit, defensibility_commitment), set the founder's defensibility envelope, then run the `max-min-distance` Z3 template to find the provably-optimal positioning vector. Emit:

- Optimal positioning vector + current vector + min-distance to nearest 3 competitors
- Repositioning effort signal (dimensions where current is >2.0 from optimal)
- 3 sharper positioning alternatives (anchor / mechanism / outcome)
- **Content pillars** (4-6) derived from the chosen positioning — these feed Stage 10
- MaxSAT-ready claims per the `gtm-output-schemas` atomic-claim contract

Skip if no clear competitor positioning vectors emerged from Stage 2 — output would be hand-wavy.

### Stage 8 — Competitor war-gaming (NEW — E1)

Apply `/war-game` logic with Stage 1+2 + candidate moves drawn from Stage 4 SWOT (`O` and `S` quadrants) and Stage 7 positioning alternatives. Auto-infer predicate from move language (pricing → 4a / feature → 4b / channel → 4c); default 4b. Run the `quantifier-alternation` Z3 template with manual skolemization, 30s timeout, combo-space precheck. Emit:

- Durable moves table (each with proof: kill scenarios it survives)
- Kill scenarios for non-durable moves (the specific response combo that defeats each)
- Predicate used + founder data gaps
- MaxSAT-ready durability claims

Skip if Stage 4 produced fewer than 3 candidate strategic moves — nothing to war-game.

### Stage 9 — MaxSAT claim synthesis (renumbered — D1)

After Stages 2-8 complete and **before** writing the synthesis document, run the MaxSAT step. Replaces naïve recommendation concatenation with a provably-optimal consistent subset.

**Claim collection.** Scan recommendations from Stages 2-8 (now includes positioning whitespace claims from Stage 7 and war-game durability claims from Stage 8). Accept a claim only if all four MaxSAT fields are present: `claimId`, `atomicClaim`, `weight` (1-10 int), `confidence` (0.0-1.0 float). Skip incomplete recommendations — do not default missing fields. Collect `incompatibleWithClaimIds` edges and build `incompatible_pairs` by mapping claim IDs to their 0-based index.

**If fewer than 3 claims pass collection:** skip the solver and fall back to prose synthesis. Note "insufficient MaxSAT-ready claims for solver synthesis" at the top.

**Solver call (uses `solver-maxsat` — NOT `solver-z3`).** Consult `solver-patterns` skill Template 6:

1. `mcp__solver-maxsat__clear_model`
2. `mcp__solver-maxsat__add_item(1, ...)` — claim data (list of dicts, incompatible_pairs)
3. `mcp__solver-maxsat__add_item(2, ...)` — WCNF build + RC2 solve + `export_solution(result_dict)`
4. `mcp__solver-maxsat__solve_model(timeout=10000)`

**Parse the result:**
- `selected_claim_ids` — render as the synthesis recommendations
- `dropped_claim_ids` — list in the "Filtered claims" appendix with one-line reason (identify the conflicting selected claim if determinable)
- `status == "unsatisfiable"` → note "no synthesis-ready claims available; all recommendations require manual review"
- Timeout/error → fall back to prose synthesis with a visible warning

### Stage 10 — 14-day content calendar (NEW — E2)

Apply `/content-calendar` logic with Stage 7 pillars + Stage 6 active publishing channels as input. If Stage 7 produced fewer than 3 pillars, fall back to brand-context-derived pillars per content-calendar.md's own fallback logic. Run `solver-mzn` with the `assignment-with-diversity` template, 30s timeout, feasibility precheck.

Emit the D×P schedule grid, pillar coverage summary, cadence summary, and sensitivity notes. Write JSON sidecar to `content-calendar-{brand-slug}-{YYYY-MM-DD}.json`.

Skip if the brand explicitly opts out of execution-layer planning (strategic-only audit).

### Stage 11 — PDF render (NEW — best-effort)

After the synthesis markdown is written, render a PDF artifact alongside it. From PowerShell:

```
node scripts/report-bundler/bundle.mjs <path-to-synthesis-md>
```

Stage 11 must:

1. Check if `scripts/report-bundler/bundle.mjs` exists. If not, log a warning and report the markdown path only.
2. Check if `node` is available on PATH.
3. Invoke the bundler with the markdown path.
4. Report the PDF path to the user on success.
5. **On any failure** (missing bundler, missing npm dep, Puppeteer can't launch headless Chromium, etc.): log the error, surface the markdown path only, do NOT block the audit.

The bundler outputs `gtm-audit-{brand-slug}-{YYYY-MM-DD}.pdf` next to the markdown.

## Solver serialization (critical)

The `solver-z3` MCP server holds shared session state. **Stages 2, 3, 4, 5, 6, 7, 8 must all run sequentially** — never invoke them from parallel `Task` sub-agents. Stage 9 (`solver-maxsat`) and Stage 10 (`solver-mzn`) each use a different MCP server but the same serial discipline applies: one solver invocation at a time.

## Synthesis output

After Stage 10 completes, produce a single synthesis document. **Only render recommendations that appear in `selected_claim_ids` from Stage 9.** Dropped claims go to the appendix. Section order:

1. **Executive summary** (5-7 bullets, every bullet cites a stage's evidence; only solver-selected claims from Stage 9)
2. **The market and the niche** (Stages 3 + 5 condensed)
3. **The competitive set** (Stage 2 — top 3-5 competitors + whitespace gaps)
4. **Positioning whitespace** (Stage 7 — proposed positioning vector, min-distance to nearest 3 competitors, which dimensions provide most separation, primary recommended option)
5. **Strategic priorities** (Stage 4 + 3 — only MaxSAT-selected, ranked by `weight × confidence`, with explicit stop-doings)
6. **Competitor war-gaming** (Stage 8 — durable moves table with proof, kill scenarios for non-durable moves, predicate used)
7. **Channel mix and rollout** (Stage 6 — phase 1 / phase 2 / phase 3 — only selected claims)
8. **14-day content calendar** (Stage 10 — calendar grid day × platform, pillar coverage summary)
9. **Open questions and confidence** (where data quality was thin, what to investigate before acting)
10. **Filtered claims appendix** (Stage 9 dropped claims — one line each: claim ID, atomic claim text, reason dropped)

Write to `gtm-audit-{brand-slug}-{YYYY-MM-DD}.md` in the user's current working directory unless specified otherwise. Stage 11 produces `gtm-audit-{brand-slug}-{YYYY-MM-DD}.pdf` alongside it (when possible).

## Quality bar

- **Don't skip stages without saying so.** If a stage fails or produces low-confidence output, surface that — don't paper over it.
- **All references tie to canonical schemas.** Synthesis isn't creative writing; every section ties back to structured agent output.
- **Confidence is honest.** Thin competitor data or missing pricing → audit confidence drops. Say so.
- **Every recommendation is actionable.** "Improve positioning" is not actionable. "Tighten positioning from 'AI marketing platform' to 'AI-powered demand-gen co-pilot for B2B SaaS founders post-PMF' to escape the HubSpot comparison" is.
- **MaxSAT synthesis is not optional.** If sub-agents emit MaxSAT-ready claims, Stage 9 must run before synthesis. Naïve concatenation is a regression, not a fallback.
- **All 8 strategic stages contribute claims to MaxSAT.** Positioning (Stage 7) and war-game (Stage 8) outputs MUST emit MaxSAT-ready claims per the `gtm-output-schemas` atomic-claim contract.
- **Dropped claims get an explanation.** Name which selected claim conflicted, or flag "no incompatible pair found — dropped by solver weight optimization."
- **PDF is a convenience artifact, not the source of truth.** The markdown stays authoritative. PDF failure does not block the audit.

## When to skip stages

- Skip Stage 5 (Porter's) for very early-stage / pre-PMF brands — market structure analysis is premature.
- Skip Stage 6 (channel scoring) if the brand has explicitly asked for a strategic-only audit (no execution layer).
- Skip Stage 7 (positioning) if no clear competitor positioning vectors emerged from Stage 2 — output would be hand-wavy.
- Skip Stage 8 (war-game) if Stage 4 SWOT produced fewer than 3 candidate strategic moves — needs candidate moves to war-game.
- Skip Stage 9 (MaxSAT) only if fewer than 3 synthesis-ready claims exist across Stages 2-8, or if `solver-maxsat` is unavailable. Note the skip reason in the synthesis header.
- Skip Stage 10 (content-calendar) if the brand explicitly opts out of execution-layer planning (strategic-only audit).
- Skip Stage 11 (PDF) if `scripts/report-bundler/` is missing — markdown stays the primary artifact regardless.
- Always run Stages 1-4 — they're the foundation.

## Solver dependency

The full audit requires three MCP servers and one Node toolchain:

- **`solver-z3`** — Stages 2-8 (registered in `~/.claude.json` as `mcp-solver-z3.exe`). Serial: one stage at a time.
- **`solver-maxsat`** — Stage 9 (`mcp-solver-maxsat.exe`). Without it, Stage 9 falls back to prose with a prominent warning.
- **`solver-mzn`** — Stage 10 (`mcp-solver-mzn.exe`, MiniZinc on PATH). Without it, Stage 10 is skipped with a note.
- **Node.js + npm + bundler deps** — Stage 11. Requires `scripts/report-bundler/bundle.mjs` plus its installed Puppeteer dependency. Failure here is non-blocking.

Never silently degrade — always state the solver/bundler status at the top of the synthesis document.
