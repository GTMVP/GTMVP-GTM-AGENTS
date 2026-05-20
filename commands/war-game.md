---
description: Run competitor war-gaming to find provably-durable strategic moves under worst-case competitor response. Phase E1 — uses Z3 with manual skolemization of the universal quantifier over enumerated competitor responses. Supports all three predicate templates (4a, 4b, 4c).
argument-hint: [brand-url-or-context-file] [optional: --predicate 4a|4b|4c --moves "ship_X,ship_Y" --competitors-from competitor-map-{brand}-{date}.json --lead-margin 3 --timeout 30]
---

# /war-game

Asks the question Phases A–D can't: **"With proof, is this move durable?"** Given a finite set of candidate moves and a bounded competitor response space, the `solver-z3` MCP server finds a move that survives every realistic counter — or proves no such move exists. This is the GTMVP feature that turns a static strategic recommendation into a math-backed defensibility verdict.

It's also the screenshot-worthy demo moment per the Phase E1 scoping doc §1: "no matter how my competitors respond, this move still wins." v1 supports all three predicate templates: **4a (market-share defensibility), 4b (feature-coverage moat), 4c (channel-economics resilience).** Pick via `--predicate` or auto-infer from move language.

## Argument

`$ARGUMENTS` — a brand URL OR a path to a context file (preferred: `gtm-audit-{brand}-{date}.md` or `positioning-pass-{brand}-{date}.md`). If neither is supplied, ask the founder.

Optional flags (parsed from arguments):
- `--predicate <4a|4b|4c>` — predicate template per scoping doc §4. Default `4b` when ambiguous (lowest data lift, broadest applicability). Auto-infer from move language when unset (pricing words → 4a, feature words → 4b, channel/spend words → 4c).
- `--moves <csv>` — comma-separated candidate moves, 3–7 entries. Required if no `/positioning-pass` or `/swot-analysis` context exists to derive them.
- `--competitors-from <path>` — path to a `competitor-map-{brand}-{date}.json` file. If absent, invoke `competitor-mapper-agent` inline (per `/competitor-map` step 2).
- `--lead-margin <int>` — predicate-4b only. Minimum weighted-coverage lead the move must hold. Default 3. Higher = stricter durability requirement.
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

5. **Select the predicate.** All three are first-class. Use `--predicate` if set. Otherwise auto-infer from move language per scoping §4 heuristic:
   - Pricing / freemium / packaging words → **4a (market-share defensibility)**
   - Feature / integration / coverage words → **4b (feature-coverage moat)**
   - Channel / spend / CAC / ad-budget words → **4c (channel-economics resilience)**
   - Ambiguous or mixed signals → default to **4b** and ask the founder to confirm. 4b has the lowest data lift and is the safest fallback.

6. **Collect predicate-specific data.** Per scoping §5. Use defaults where available; require explicit input where not. If >40% of inputs for the chosen predicate are defaulted, switch to scenario tree.

   **Predicate 4a — market-share defensibility (§5.1–5.3):**
   - `my_share_after_move[i]` — projected market share after move i (Real, 0..1). Founder estimate or 3rd-party (Gartner / IDC / internal sales data).
   - `their_response_impact[k][r]` — signed share impact per (competitor k, response r). Positive = they take share from you. Founder fills the per-competitor sensitivity table (typically 3–5 responses per competitor).
   - `floor_threshold` — minimum market share you commit to defending (Real, 0..1).
   - **Precheck:** confirm `max(my_share_after_move) − Σ_k max_r impact[k][r] >= floor_threshold` is plausible. If the best-case move minus worst-case response per competitor is already below floor, the predicate is trivially UNSAT — surface that *before* invoking the solver.

   **Predicate 4b — feature-coverage moat (§5.4–5.6):**
   - **Buyer dimensions (5–10).** Source: founder, or extract from `/competitor-map` whitespace gaps.
   - **Dimension weights (1–10 each).** Founder estimate of buyer importance.
   - **Coverage matrix.** 0/1 per (competitor × dimension) — who covers what *today*.
   - **Move impact.** Which dimensions each candidate move closes for the brand.
   - **Competitor response time.** Per (competitor × dimension) — months to close the gap. If response time > horizon H, treat as "cannot match in window."
   - **Horizon H.** Founder-specified, default 12 months.

   **Predicate 4c — channel-economics resilience (§5.7–5.8):**
   - `my_cac_after_move[i]` — your CAC under move i without competitor counter (founder estimate by channel).
   - `competitor_counter_impact[i][k][r]` — how much your CAC rises when (move i × competitor k × response r). **Per-move** because counter-investing in your channel hurts only that move. Founder fills `N_my_moves × N_competitors × N_responses` cells.
   - `target_cac` — LTV-derived ceiling.
   - **Defaults available** per scoping §5.7: 5–15% CAC rise per $10K competitor counter-spend depending on channel saturation. Use as a starting point; flag every defaulted cell in `founderDataGaps[]`.

   **Feasibility precheck (all predicates).** Compute the combo space: `|candidate_moves| × ∏(|responses_per_competitor|)`. If > 3000, warn and either (a) reduce response space to top-3 per competitor, or (b) fall back to scenario tree. Quantifier-alternation chokes fast at scale.

7. **Build the Z3 model per Template 8 (`quantifier-alternation`).** Follow `solver-patterns` SKILL.md §8 exactly. The encoding manually skolemizes the universal quantifier — expands `∀ their_responses` into a ground conjunction over the enumerated response set, then asserts the predicate holds for every expansion. **Call the predicate-specific sub-template per `solver-patterns` §8.4a / §8.4b / §8.4c.**

   Sequence:
   ```
   mcp__solver-z3__clear_model
   → add_item(0, ...slot-filled data block per predicate: 4a shares/impacts/floor, 4b dims/weights/coverage, 4c cacs/impacts/target...)
   → add_item(1, ...decision vars: my_move[i] Bool, exactly-one constraint (PbEq))
   → add_item(2, ...skolemized success predicate over all response combos, per-predicate body)
   → add_item(3, ...solve directive with timeout=30s and unsat-core tracking...)
   → solve_model(timeout=30)
   → clear_model
   ```

   No `ForAll`. v1 is manual skolemization only — per scoping §8a (qe tactic hangs) and §8c (UNSAT cores from quantified formulas are useless).

8. **Solve and interpret.**
   - **SAT** → at least one move is durable. Extract from the model.
   - **UNSAT** → no candidate move survives every realistic combo. Run a **second pass per-move** (fix each `my_move[i] = true` one at a time and re-solve) to extract the kill scenarios — the specific response combo that defeats each move. This produces the full winning set + kill table.
   - **Timeout** → reduce response space (top-3 per competitor) and retry once. If still timeout, fall back to scenario tree.

9. **Render readable summary.** Narration adapts per predicate; three shapes per outcome.

   **SAT, unique winner:**
   - 4a: "Ship `<move>`. It holds your share above `{floor_threshold}` against any combination of competitor responses. Worst response combo loses you `{worst_impact}` share — you still land at `{final_share}`, above your floor."
   - 4b: "Ship `<move>`. It's the only move where every realistic competitor response leaves you ahead on weighted feature coverage. Worst case tested: [combo]. Your weighted lead is `{lead}` — above the `{lead_margin}` margin."
   - 4c: "Ship `<move>`. It keeps your CAC under `{target_cac}` against any competitor counter-investment. Worst-case CAC: `{worst_cac}`."

   **SAT, multiple winners:** "Two moves are structurally durable: A and B. Pick based on non-defensibility criteria (resource cost, brand fit). Kill scenarios for the rest below."

   **UNSAT:** "No move in your candidate set is structurally winnable on the chosen metric (`{predicate-specific: share floor / coverage lead / CAC ceiling}`). Every candidate has at least one realistic competitor response that defeats it. Two options: (1) expand the candidate set, (2) relax the threshold (`floor_threshold` for 4a, `lead_margin` for 4b, `target_cac` for 4c). If neither helps, this market may be structurally dominated — consider repositioning."

10. **Write JSON output** to `war-game-{brand-slug}-{YYYY-MM-DD}.json` per the schema below.

## Output format

Write the full JSON to `war-game-{brand-slug}-{YYYY-MM-DD}.json`. The JSON schema is identical across all three predicates — only the `predicateUsed` field and the `config` payload differ. Schema (extension of BaseAgentOutput, per `gtm-output-schemas` §8.8):

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
    "predicate": "4b",
    "leadMargin": 3,
    "horizonMonths": 12,
    "dimensions": ["crm_integration", "forecasting", "..."],
    "dimWeights": { "crm_integration": 9, "forecasting": 8, "...": "..." },
    "coverageMatrix": { "brand": [1,1,1,0,1,0,0,1], "comp_a": [1,1,0,1,1,0,1,1] },
    "responseSpace": { "comp_a": ["ship_hygiene_6mo", "ship_mobile_12mo", "do_nothing"] }
  }
}
```

`predicateUsed` carries `"4a"`, `"4b"`, or `"4c"`. The `config` block carries the predicate-specific inputs: 4a → `myShareAfterMove`, `theirResponseImpact`, `floorThreshold`; 4b → dims/weights/coverage/horizon/leadMargin; 4c → `myCacAfterMove`, `competitorCounterImpact`, `targetCac`.

Print to chat in this order (most actionable first):

1. **Verdict line** — single line. "1 of 3 moves is structurally durable: `ship_salesforce_integration`" or "0 of 3 moves are durable — market is structurally dominated for your stated metric."

2. **Kill scenarios** — for each non-durable move, 1 line: "`ship_api_v2` dies when Comp X ships their own SF integration in 6mo."

3. **Founder data gaps** — list defaulted inputs so the founder knows what to refine. If empty, omit.

4. **Sensitivity bullets (1–3)** — what input change would flip the verdict. Predicate-appropriate: "Raising `lead_margin` from 3 to 5 kills the winning move." / "Lowering `floor_threshold` from 0.30 to 0.25 makes a second move durable." / "Cutting `target_cac` from $85 to $75 leaves no durable move."

## Quality bar

- **All candidate-move × response combos are checked.** No sampling. Manual skolemization expands the full ∀ space.
- **Predicate dispatch picks the right sub-template; no stubs.** 4a/4b/4c each run their own encoding per `solver-patterns` §8.4a / §8.4b / §8.4c.
- **Predicate is linear in Z3 variables.** No `variable × variable` products (per scoping §8b). Weights, share impacts, and CAC elasticities are coefficients, not decision vars.
- **No `ForAll` in the encoding.** v1 = manual skolemization only. Quantifier-alternation via `ForAll` + `qe2` hangs on non-trivial inputs.
- **Unsat-core populated on UNSAT.** Every constraint is `assert_and_track`ed so the kill scenario can be extracted.
- **30s timeout enforced.** If exceeded, reduce response space and retry once before falling back to scenario tree.
- **Combo space precheck.** If `|moves| × ∏|responses|` > 3000, warn and either reduce or fall back.
- **Second-pass durability check on UNSAT.** Per-move fix + re-solve to extract kill scenarios. UNSAT alone is not enough output.
- **Founder data gaps surfaced.** Every defaulted input is logged. SAT under bad data is still bad.

## Common pitfalls

- **Combo space explosion.** 5 competitors × 5 responses each = 3,125 combos × 5 moves = 15K Z3 assertions. Solver chokes. Precheck and reduce.
- **Treating UNSAT as a bug.** UNSAT is a finding — "no move wins" is the most strategically valuable output. Narrate it with weight, not embarrassment.
- **Mixing predicate variable types.** 4b is Bool-based (coverage 0/1); 4a and 4c are Real-based (shares, CACs, impacts). Don't manually splice numeric expressions across predicate types — pick one predicate per run, build its model cleanly, clear before switching.
- **Missing competitor data.** No `/competitor-map` output and no `--competitors-from` flag = stop. Don't war-game against a competitor set you invented.
- **Non-linear predicate sneaks in.** Multi-period CAC drift or compound growth = non-linear. Pre-compute in Python before encoding.
- **Continuous response space.** "Competitor could counter-bid any amount" — discretize to {low, mid, high} before encoding.
- **Skipping the second pass on UNSAT.** Without per-move durability extraction, the output is "no winner" with no explanation. Useless.
- **Forgetting to log data gaps.** If 6 of 8 dimension weights (or share impacts, or CAC elasticities) were defaulted, the founder needs to know.

## Cross-references

- `skills/solver-patterns/SKILL.md` §8 — the `quantifier-alternation` template; §8.4a, §8.4b, §8.4c are the predicate-specific sub-templates.
- `skills/gtm-output-schemas/SKILL.md` §8 — runtime conventions (fresh-model, labeling, timeout).
- `skills/gtm-output-schemas/SKILL.md` §8.8 — the `solverResult` envelope schema.
- `commands/competitor-map.md` — produces the JSON this command reads in step 2.
- `commands/positioning-pass.md` — produces the candidate-move list this command consumes in step 3.
- `skills/swot-analysis` — alternate source for candidate moves.
- `~/.claude/plans/phase-e1-scoping.md` — master design doc. §4a/§4b/§4c are the three predicates; §5 is the data-collection spec; §8 is the risk catalog; §10 is the scenario-tree fallback.
