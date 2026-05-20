---
description: Run competitor war-gaming to find provably-durable strategic moves under worst-case competitor response. Phase E1 — uses Z3 with manual skolemization of the universal quantifier over enumerated competitor responses. v1 supports predicate 4b (feature-coverage moat) only; 4a and 4c are stubbed for future versions.
argument-hint: [brand-url-or-context-file] [optional: --predicate 4b --moves "ship_X,ship_Y" --competitors-from competitor-map-{brand}-{date}.json --lead-margin 3 --timeout 30]
---

# /war-game

Asks the question Phases A–D can't: **"With proof, is this move durable?"** Given a finite set of candidate moves and a bounded competitor response space, the `solver-z3` MCP server finds a move that survives every realistic counter — or proves no such move exists. This is the GTMVP feature that turns a static strategic recommendation into a math-backed defensibility verdict.

It's also the screenshot-worthy demo moment per the Phase E1 scoping doc §1: "no matter how my competitors respond, this move still wins." v1 ships predicate **4b (feature-coverage moat)** only. 4a (share defensibility) and 4c (channel economics) are stubbed — they print a "not yet implemented in v1, defer to scenario tree" notice and fall through to the scenario-tree fallback.

## Argument

`$ARGUMENTS` — a brand URL OR a path to a context file (preferred: `gtm-audit-{brand}-{date}.md` or `positioning-pass-{brand}-{date}.md`). If neither is supplied, ask the founder.

Optional flags (parsed from arguments):
- `--predicate <4a|4b|4c>` — predicate template per scoping doc §4. Default `4b`. **Only `4b` is implemented in v1.** Passing `4a` or `4c` prints a deferral notice and switches to scenario-tree mode (see scoping §10).
- `--moves <csv>` — comma-separated candidate moves, 3–7 entries. Required if no `/positioning-pass` or `/swot-analysis` context exists to derive them.
- `--competitors-from <path>` — path to a `competitor-map-{brand}-{date}.json` file. If absent, invoke `competitor-mapper-agent` inline (per `/competitor-map` step 2).
- `--lead-margin <int>` — minimum weighted-coverage lead the move must hold (Template 8 slot `lead_margin`). Default 3. Higher = stricter durability requirement.
- `--timeout <seconds>` — solver timeout. Default 30 (quantifier-alternation needs more than the 10s default).
- `--fallback-to-tree` — boolean. If founder data is incomplete or combo space explodes, switch to scenario-tree narration per scoping §10 instead of failing.

## Steps

1. **Establish brand context.** Crawl the URL or load the context file. Extract industry, sub-vertical, ICP, stage, and current competitive position. Same first beat as `/competitor-map` and `/positioning-pass`.

2. **Read or generate the competitor map.** If `--competitors-from` is set, load that JSON and read `competitorSet[]`. Else invoke `competitor-mapper-agent` inline. War-gaming with no defensible competitor set is garbage in, garbage out.

3. **Enumerate candidate moves (3–7).** Sources, in priority order:
   - `--moves` flag (verbatim).
   - `/positioning-pass` output `recommendedMoves[]` if present in working dir.
   - `/swot-analysis` strategic priorities (`O` and `S` quadrants).
   - Ask the founder. Don't invent.

4. **Enumerate competitor responses (3–5 per competitor).** For each competitor in the map, list the realistic counters they could make. Keep this **finite and enumerated** — never continuous. Per scoping §8a: if the founder says "they could spend anything," discretize to {low, mid, high}.

5. **Select the predicate.**
   - `--predicate 4b` (default): proceed to step 6 with the feature-coverage moat encoding.
   - `--predicate 4a` or `--predicate 4c`: print: "Predicate {N} is not yet implemented in v1 of /war-game. The Z3 encoding for share-defensibility (4a) / channel-economics (4c) is queued for Phase E1.5. Falling back to scenario tree per scoping §10." Then jump to step 9 with scenario-tree narration.
   - If no flag and ambiguous: ask the founder.

6. **Collect predicate-4b data.** Per scoping §5.4–5.6:
   - **Buyer dimensions (5–10).** Source: founder, or extract from `/competitor-map` whitespace gaps.
   - **Dimension weights (1–10 each).** Founder estimate of buyer importance.
   - **Coverage matrix.** 0/1 per (competitor × dimension) — who covers what *today*.
   - **Move impact.** Which dimensions each candidate move closes for the brand.
   - **Competitor response time.** Per (competitor × dimension) — months to close the gap. If competitor's response time > horizon H, treat as "cannot match in window."
   - **Horizon H.** Founder-specified, default 12 months.

   **Feasibility precheck.** Compute the combo space: `|candidate_moves| × ∏(|responses_per_competitor|)`. If > 3000, warn the founder and either (a) reduce response space to top-3 per competitor, or (b) fall back to scenario tree. Quantifier-alternation chokes fast at scale.

   If the founder cannot supply weights or response times, default sensibly but log every defaulted input to `founderDataGaps[]`. If >40% of inputs are defaulted, switch to scenario tree.

7. **Build the Z3 model per Template 8 (`quantifier-alternation`).** Follow `solver-patterns` SKILL.md §8 exactly. The encoding manually skolemizes the universal quantifier — expands `∀ their_responses` into a ground conjunction over the enumerated response set, then asserts the success predicate (4b) holds for every expansion.

   Sequence:
   ```
   mcp__solver-z3__clear_model
   → add_item(0, ...slot-filled data block: dims, weights, coverage, moves, responses, lead_margin...)
   → add_item(1, ...decision vars: my_move[i] Bool, exactly-one constraint...)
   → add_item(2, ...skolemized success predicate over all response combos...)
   → add_item(3, ...solve directive with timeout=30s and unsat-core tracking...)
   → solve_model(timeout=30)
   → clear_model
   ```

   No `ForAll`. v1 is manual skolemization only — per scoping §8a (qe tactic hangs) and §8c (UNSAT cores from quantified formulas are useless).

8. **Solve and interpret.**
   - **SAT** → at least one move is durable. Extract from the model.
   - **UNSAT** → no candidate move survives every realistic combo. Run a **second pass per-move** (fix each `my_move[i] = true` one at a time and re-solve) to extract the kill scenarios — the specific response combo that defeats each move. This produces the full winning set + kill table.
   - **Timeout** → reduce response space (top-3 per competitor) and retry once. If still timeout, fall back to scenario tree.

9. **Render readable summary.** Three narration shapes per scoping §6 readable-output-template:
   - **SAT, unique winner:** "Ship `<move>`. It's the only move where every realistic competitor response leaves you ahead on weighted feature coverage. Worst case tested: [combo]. Even then, your weighted lead is X — above the {lead_margin} margin you defined."
   - **SAT, multiple winners:** "Two moves are structurally durable: A and B. Pick based on non-defensibility criteria (resource cost, brand fit). Kill scenarios for the rest below."
   - **UNSAT:** "No move in your candidate set is structurally winnable. Every candidate has at least one realistic competitor response that defeats it. Two options: (1) expand the candidate set, (2) relax the lead margin or success metric. If neither helps, this market may be structurally dominated — consider repositioning."

10. **Write JSON output** to `war-game-{brand-slug}-{YYYY-MM-DD}.json` per the schema below.

## Output format

Write the full JSON to `war-game-{brand-slug}-{YYYY-MM-DD}.json`. Schema (extension of BaseAgentOutput, per `gtm-output-schemas` §8.8):

```json
{
  "generatedAt": "2026-05-20T17:30:00Z",
  "agentId": "war_game_agent",
  "version": "1.0.0",
  "brandSlug": "posthog",
  "warGame": {
    "predicateUsed": "4b",
    "candidateMoves": ["ship_salesforce_integration", "ship_api_v2", "ship_mobile_app"],
    "winningMoves": ["ship_salesforce_integration"],
    "killScenarios": {
      "ship_api_v2": "Comp X ships SF integration in 6mo AND Comp Y matches coverage — gap closes",
      "ship_mobile_app": "Comp Y already has mobile in roadmap (4mo response time)"
    },
    "solverStatus": "sat",
    "founderDataGaps": ["dim_weight:compliance defaulted to 5"]
  },
  "solverResult": {
    "status": "sat",
    "templateUsed": "quantifier-alternation",
    "solveTimeMs": 4820,
    "comboSpaceSize": 240,
    "skolemizationMode": "manual",
    "activeConstraints": ["lead_margin", "horizon", "exactly_one_move"]
  },
  "config": {
    "leadMargin": 3,
    "horizonMonths": 12,
    "dimensions": ["crm_integration", "forecasting", "hygiene", "..."],
    "dimWeights": { "crm_integration": 9, "forecasting": 8, "...": "..." },
    "coverageMatrix": { "brand": [1,1,1,0,1,0,0,1], "comp_a": [1,1,0,1,1,0,1,1] },
    "responseSpace": { "comp_a": ["ship_hygiene_6mo", "ship_mobile_12mo", "do_nothing"] }
  }
}
```

Print to chat in this order (most actionable first):

1. **Verdict line** — single line. "1 of 3 moves is structurally durable: `ship_salesforce_integration`" or "0 of 3 moves are durable — market is structurally dominated for your stated metric."

2. **Kill scenarios** — for each non-durable move, 1 line: "`ship_api_v2` dies when Comp X ships their own SF integration in 6mo."

3. **Founder data gaps** — list defaulted inputs so the founder knows what to refine. If empty, omit.

4. **Sensitivity bullets (1–3)** — what input change would flip the verdict. "Raising `lead_margin` from 3 to 5 kills the winning move (no move survives). Dropping Comp Y's mobile response time from 4mo to 8mo makes `ship_mobile_app` durable too."

## Quality bar

- **All candidate-move × response combos are checked.** No sampling. Manual skolemization expands the full ∀ space.
- **Predicate is linear in Z3 variables.** No `variable × variable` products (per scoping §8b). Weights are coefficients, not decision vars.
- **No `ForAll` in the encoding.** v1 = manual skolemization only. Quantifier-alternation via `ForAll` + `qe2` hangs on non-trivial inputs.
- **Unsat-core populated on UNSAT.** Per `gtm-output-schemas` §8 labeling convention, every constraint is `assert_and_track`ed so the kill scenario can be extracted.
- **30s timeout enforced.** If exceeded, reduce response space and retry once before falling back to scenario tree.
- **Combo space precheck.** If `|moves| × ∏|responses|` > 3000, warn and either reduce or fall back. Don't blindly submit.
- **Second-pass durability check on UNSAT.** Per-move fix + re-solve to extract kill scenarios. UNSAT alone is not enough output.
- **Predicate 4a / 4c gracefully deferred.** Don't half-implement. Print the deferral notice and switch to scenario tree.
- **Founder data gaps surfaced.** Every defaulted input is logged. Founder must see what's assumption vs. what's data.

## Common pitfalls

- **Combo space explosion.** 5 competitors × 5 responses each = 3,125 combos × 5 moves = 15K Z3 assertions. Solver chokes. Precheck and reduce.
- **Treating UNSAT as a bug.** UNSAT is a finding — "no move wins" is the most strategically valuable output. Narrate it with weight, not embarrassment.
- **Predicate 4a/4c stub fallthrough.** If a founder passes `--predicate 4a`, don't silently use the 4b encoding. Print the deferral and switch to scenario tree.
- **Missing competitor data.** No `/competitor-map` output and no `--competitors-from` flag = stop. Don't war-game against a competitor set you invented.
- **Non-linear predicate sneaks in.** Multi-period CAC drift or compound growth = non-linear. Pre-compute in Python before encoding.
- **Continuous response space.** "Competitor could counter-bid any amount" — discretize to {low, mid, high} before encoding.
- **Skipping the second pass on UNSAT.** Without per-move durability extraction, the output is "no winner" with no explanation. Useless.
- **Forgetting to log data gaps.** If 6 of 8 dimension weights were defaulted, the founder needs to know. SAT under bad data is still bad.

## Cross-references

- `skills/solver-patterns/SKILL.md` §8 — the `quantifier-alternation` template this command instantiates (Template 8).
- `skills/gtm-output-schemas/SKILL.md` §8 — runtime conventions (fresh-model, labeling, timeout).
- `skills/gtm-output-schemas/SKILL.md` §8.8 — the `solverResult` envelope schema (now includes `'quantifier-alternation'` in `templateUsed`).
- `commands/competitor-map.md` — produces the JSON this command reads in step 2.
- `commands/positioning-pass.md` — produces the candidate-move list this command consumes in step 3.
- `skills/swot-analysis` — alternate source for candidate moves (strategic priorities).
- `~/.claude/plans/phase-e1-scoping.md` — master design doc. §4b is the predicate, §6 is the command sketch, §8 is the risk catalog, §10 is the scenario-tree fallback.
