---
description: Score all 28 marketing micro-channels for a specific brand and stage, producing a sequenced rollout plan with phase 1 / phase 2 / phase 3, explicit deprioritizations, AND a provably-optimal $/month allocation under founder-stated budget and capacity constraints.
argument-hint: [brand-url-or-context-file] [optional: --budget 35000 --team-size 1]
---

# /channel-score

Applies the `marketing-channel-scoring` skill to produce a portfolio-level channel mix recommendation, then upgrades that recommendation to a **provably-optimal dollar allocation** via the `solver-z3` MCP server. Not single-channel optimization.

## Argument

`$ARGUMENTS` — a brand URL OR a path to a context file containing prior audit output (`gtm-audit-*.md` synthesis, `competitor-map-*.json`, etc.). If missing, ask.

Optional flags (parsed from arguments):
- `--budget <USD>` — monthly marketing budget. If absent, ask the founder.
- `--team-size <N>` — number of FTEs available for marketing execution. Default 1.
- `--max-concentration <PCT>` — max % of budget on any single channel. Default 40.
- `--economics <path>` — path to a 28-row CSV with per-channel `min_viable_spend_usd` and `max_useful_spend_usd`. If absent, fall back to defaults derived from `default_config.daily_budget × 30` where present, else `agent_type` macro defaults (see Step 5 below).

## Steps

1. **Establish brand context.** Either:
   - Crawl the URL and derive: industry, sub-vertical, ICP, price tier, stage (pre-PMF / post-PMF early / scaling / mature), current channel mix if visible
   - Or load the context file and extract the same fields
   
   Stage matters. Ask for it explicitly if you can't infer.

2. **Load `data/channel-taxonomy.json`** from this plugin's directory. Confirm 28 agents are present.

3. **Apply `marketing-channel-scoring` skill** — score every channel on the 5 dimensions (ICP fit, stage fit, capital efficiency, time-to-signal, defensibility), compute weighted composites, run portfolio checks (compounding count, fast-feedback count, paid concurrency, dependency ordering).

4. **Produce the rollout plan** (existing prose-driven output):
   - Phase 1 (now): 3-5 channels with no dependencies, fast feedback, ICP-aligned
   - Phase 2 (next quarter): channels that depend on phase 1 or build defensibility
   - Phase 3 (year two): long-cycle channels (PR, podcast, SEO at scale)
   - Explicitly deprioritized: 5-10+ channels with reasons

5. **Build per-channel economics for the solver step.** For each of 28 channels, determine `min_viable_spend_usd` and `max_useful_spend_usd`:
   - **Founder-supplied** via `--economics <csv>`: use as-is, with `agent_id` as the join key.
   - **Default derivation** (fallback): for channels with `default_config.daily_budget` in the taxonomy, use `daily_budget × 30` as `min_viable_spend_usd`. Otherwise, use `agent_type` macros:
     - `paid_*` → min $3000, max $25000
     - `seo_*` → min $1500, max $8000
     - `content_*` → min $4000, max $15000
     - `email_*` → min $2000, max $8000
     - `social_*` → min $1500, max $6000
     - `partnerships_*` → min $5000, max $20000
     - `press_pr_*` → min $5000, max $20000
     - `affiliate_*` → min $3000, max $15000
     - `analytics_*` → min $1000, max $5000
   - **Always show the founder which defaults you used.** Print as a table before the solver step. Founder can override with `--economics` and re-run.

6. **Solve for the optimal allocation** via `solver-z3`. Follow the `linear-allocation` template in the `solver-patterns` skill exactly. Follow the conventions in `gtm-output-schemas` §8 — fresh-model pattern, labeled assertions, 10s timeout, UNSAT explanation.

   Build the model with these slot values:
   - `option_ids` = list of all 28 `agent_id` slugs in taxonomy order
   - `scores` = composite score (1-10) from Step 3 per channel
   - `min_viable` = from Step 5
   - `max_useful` = from Step 5
   - `total_budget` = `--budget` argument
   - `max_concentration_pct` = `--max-concentration / 100` (default 0.40)
   - `dependencies` = `(child_idx, parent_idx)` pairs derived from taxonomy `dependencies` field
   - `compounding_indices` = channels you would have called compounding in Step 4 portfolio check
   - `fast_feedback_indices` = channels you would have called fast-feedback in Step 4
   - `team_size` = `--team-size` argument

   Run the feasibility precheck FIRST. If UNSAT, surface the named labels in plain English and propose at most 2 relaxations (e.g. "Raise budget to $X, OR drop compounding floor"). Do not proceed to optimization if the feasibility precheck fails.

   If feasible, run the optimization. Extract the spend solution into the `optimalAllocation` output block per §8.8 of `gtm-output-schemas`.

7. **Render the recommendation** with composite-score table, rollout phases, portfolio warnings, AND the optimal allocation table. The allocation is the new headline — present it BEFORE the rollout phases:

   ```
   ## Optimal monthly allocation ($35,000 / month, 1 operator)

   | Channel                    | Macro      | Score | $/mo    | Active |
   |---                         |---         |---    |---      |---     |
   | agent_seo_onpage_001       | SEO        | 7.5   | $6,200  | ✓      |
   | agent_content_blog_010     | Content    | 8.0   | $11,800 | ✓      |
   | agent_paid_search_015      | Paid       | 7.8   | $9,400  | ✓      |
   | agent_email_drip_021       | Email      | 7.2   | $6,300  | ✓      |
   | agent_seo_keyword_002      | SEO        | 7.0   | $1,300  | ✓      |
   | (... unallocated)          | ...        | ...   | $0      |        |
   | Total                      |            |       | $35,000 |        |

   Predicted pipeline score: 2661.6  (greedy baseline 2344.4)
   Active constraints: budget_cap, dep_seo_keyword_needs_seo_onpage, team_capacity, min_compounding, min_fast_feedback
   ```

   Below the table, include 1-3 sensitivity bullets:
   - "If you added $5K to budget: unlocks `agent_paid_linkedin_018` for fast-feedback acceleration."
   - "If you dropped the compounding floor: shifts $4K from blog to paid_search, +12 objective."

## Output format

Write the full JSON to `channel-score-{brand-slug}-{YYYY-MM-DD}.json`. The JSON now contains a new `optimalAllocation` block (see §8.8 of `gtm-output-schemas`) in addition to all existing fields.

Print to the chat in this order (most actionable first):
1. **Optimal monthly allocation table** (see Step 7 format)
2. **Sensitivity bullets** (1-3 lines on what additional budget or relaxed constraints unlock)
3. Top 10 channels by composite score (existing table)
4. The 3-phase rollout plan (existing)
5. Portfolio warnings (existing — surface anything `compounding_count == 0`, `all_paid`, etc.)
6. **Defaults used** if no `--economics` CSV was supplied — so the founder can override and re-run

## Quality bar

- **All 28 channels scored AND modeled.** Scores feed the solver objective; missing channels = missing optimization terms.
- **Composite scores match the weighted math.** Default weights: ICP 0.30, stage 0.20, capital efficiency 0.20, time-to-signal 0.15, defensibility 0.15.
- **Feasibility precheck runs before optimization.** UNSAT must surface a labeled core, not just "no solution".
- **Solver invocation uses `linear-allocation` template verbatim from `solver-patterns`.** Do not re-author the model structure.
- **Defaults are surfaced.** Founders must see which `min_viable_spend_usd` / `max_useful_spend_usd` values were used so they can adjust.
- **Active constraints are surfaced.** The `activeConstraints[]` in `optimalAllocation` shows which constraints bind at the optimum — these are the levers the founder cares about.

## Common pitfalls

- Recommending a channel because it's trendy ("everyone's doing AI SEO") without ICP fit
- Phase 1 with all paid channels (no compounding, no defensibility)
- Phase 1 with all long-cycle channels (no fast feedback for 6 months)
- Ignoring stage — pre-PMF brands shouldn't run brand campaigns
- **Skipping the feasibility precheck.** If the founder's budget can't satisfy the compounding + fast-feedback floors, the optimizer returns an arbitrary feasible-but-bad allocation. The precheck catches this and explains it.
- **Inventing per-channel economics not in the taxonomy.** Either use the macro defaults from Step 5 or ask the founder for a CSV. Don't make up min_viable / max_useful from thin air.
- **Forgetting the fresh-model pattern.** Every `/channel-score` invocation begins with `mcp__solver-z3__clear_model`. Otherwise prior-run state contaminates the model.

## Cross-references

- `skills/solver-patterns/SKILL.md` §1 — the `linear-allocation` template this command instantiates.
- `skills/gtm-output-schemas/SKILL.md` §8 — runtime conventions (fresh-model, labeling, timeout, UNSAT explanation).
- `skills/gtm-output-schemas/SKILL.md` §8.8 — the `solverResult` output block schema.
- `skills/marketing-channel-scoring/SKILL.md` — the scoring framework + new `optimalAllocation` JSON addition.
- `scripts/solver-evals/channel-score-*.json` — eval scenarios validating this integration.
