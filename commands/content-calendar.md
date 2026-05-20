---
description: Generate a provably-optimal multi-platform content calendar for a brand. Assigns content pillars across days and platforms under diversity, fit, cadence, and coverage constraints. Powered by the solver-mzn MCP server (MiniZinc).
argument-hint: [brand-url-or-context-file] [optional: --days 14 --platforms linkedin,x,instagram,... --cadence linkedin:4,x:7,...]
---

# /content-calendar

Builds a content calendar that's **mathematically optimal under the founder's stated constraints**, not a "vibes calendar." Given pillars, platforms, cadence, and pillar-platform fit, the `solver-mzn` MCP server (MiniZinc with global constraints) finds the assignment maximizing weighted pillar coverage subject to diversity, cadence, and bound rules.

This is GTMVP's E2 ship — the editorial output of `/positioning-pass` and `/channel-score` operationalized into a day-by-day schedule.

## Argument

`$ARGUMENTS` — a brand URL OR a path to a context file. Accepted context files:
- `gtm-audit-{brand}-{date}.md` synthesis output (preferred — has pillars + channel mix)
- `positioning-pass-{brand}-{date}.md` (has pillars but no channel mix)
- `channel-score-{brand}-{date}.json` (has channel mix but no pillars)

If two files are supplied, the union is used. If neither pillars nor a URL is available, ask the founder.

Optional flags (parsed from arguments):
- `--days <N>` — calendar length. Default 14. Range 7–28.
- `--platforms <csv>` — comma-separated platform slugs from the 28-channel taxonomy. Default `linkedin,x,instagram,youtube,tiktok,email,blog`. Must intersect with the brand's `/channel-score` active set if one exists.
- `--cadence <key:val,...>` — posts per platform across the D days, e.g. `linkedin:4,x:7,email:2`. If absent, derive from `/channel-score` allocation OR ask the founder.
- `--pillars <csv>` — override the auto-detected pillar list with explicit names.
- `--min-gap <key:val,...>` — minimum days between same-pillar posts on the same platform, per-platform. Defaults: short-form (X/Instagram/TikTok) = 3, long-form (LinkedIn/Blog) = 5, YouTube = 7, Email = 5.
- `--timeout <seconds>` — solver timeout. Default 30. Raise for D ≥ 28 or P ≥ 10.

## Steps

1. **Establish brand context.** Either:
   - Crawl the URL and derive: industry, sub-vertical, ICP, stage, voice descriptors that inform pillar selection.
   - Or load the context file(s) and extract: pillar list, active channel mix, ICP, stage.

2. **Determine the pillar set (K).**
   - If a `gtm-audit-*.md` or `positioning-pass-*.md` is supplied, extract the pillars from its synthesis section.
   - If `--pillars` flag is set, use it verbatim.
   - Else, derive 4–6 pillars from the brand context (industry, ICP, stage). Show the founder before solving so they can revise.

3. **Determine the platform set (P) and per-platform cadence.**
   - If `--platforms` is set, use it.
   - Else, if a `channel-score-*.json` is available, use the `optimalAllocation` active set, mapped to publishing platforms (drop paid-search/SEO/etc. — only platforms the founder *publishes content* to).
   - Else, default to `linkedin,x,instagram,youtube,tiktok,email,blog`.
   - Cadence: use `--cadence` flag if set; else apply per-platform macro defaults for the brand's stage:
     - Pre-PMF: linkedin 3, x 7, instagram 2, youtube 0, tiktok 1, email 1, blog 1 (over 14 days)
     - Post-PMF early: linkedin 4, x 10, instagram 4, youtube 1, tiktok 3, email 2, blog 1
     - Scaling: linkedin 5, x 14, instagram 5, youtube 2, tiktok 4, email 4, blog 2
   - **Always show the cadence used.** Founder can override and re-run.

4. **Build `pillar_fit[k,p]` — the K×P binary matrix.**
   - For each pillar k and platform p, decide 0 (poor fit, do not publish) or 1 (acceptable).
   - Guidance:
     - "Founder journey" pillar fits LinkedIn / X / Email / Blog. NOT TikTok/Instagram (image-heavy formats don't carry the long story).
     - "Tutorial / how-to" pillar fits YouTube / Blog / LinkedIn. NOT X (too long), Email is OK but secondary.
     - "Hot take / opinion" pillar fits X / LinkedIn. NOT YouTube (long-form effort high, ROI low).
     - "Visual product demo" pillar fits Instagram / TikTok / YouTube. NOT Email/Blog (wrong medium).
   - The matrix is your call — but **prepend the sentinel row 0 of all 1s** for the MiniZinc model. See solver-patterns Template 7 §sentinel notes.

5. **Determine pillar coverage bounds (`pillar_min[k]`, `pillar_max[k]`).**
   - Default: floor every pillar at `max(1, total_posts // (K × 2))` and cap at `total_posts // (K // 2 + 1)`. This ensures each pillar appears ≥ 1× per week-ish and never dominates >50%.
   - For brands with a clearly weighted pillar order (e.g. Steve's "AI-powered growth marketing" pillar weight 5 vs "Health AI" weight 1), bias bounds accordingly: `pillar_min` scales with `pillar_weight`.

6. **Determine `pillar_weight[k]`.**
   - 1–10 scale, higher = preferentially scheduled when contradiction forces a drop.
   - For most brands, use the founder's stated pillar priority. If absent, use uniform weights (all 5) — the solver will still respect the bounds and produce a feasible plan.

7. **Solve via `solver-mzn`.** Follow the `assignment-with-diversity` template in the `solver-patterns` skill exactly. Follow the conventions in `gtm-output-schemas` §8.

   Sequence:
   ```
   mcp__solver-mzn__clear_model
   → add_item(0, ...slot-filled data block from Template 7...)
   → add_item(1, ...decision vars verbatim...)
   → add_item(2, ...constraints verbatim...)
   → add_item(3, ...objective + output verbatim...)
   → solve_model(timeout=30)
   → clear_model
   ```

   **Feasibility precheck (BEFORE building the model)** — verify these in Python-pseudo:
   - `sum(cadence) >= sum(pillar_min)` — total posts cover the floor
   - For each pillar k: `sum(pillar_fit[k, :] * cadence) >= pillar_min[k]` — pillar k's allowed platforms have enough cadence to hit its floor

   If either fails, surface the gap in plain English ("Your weekly cadence of 21 posts can't cover the 4 + 3 + 4 + 4 + 3 = 18 pillar floors; raise cadence to ≥ 25 or lower one of the floors"). Do not proceed to solve.

8. **Parse the solution.** Per Template 7 output parsing rules:
   - `success: true` + `satisfiable: true` = usable schedule.
   - `optimal: true` = proven-optimal; `optimal: false` = best-found within timeout (rerun with `--timeout 60` if founder wants proof).
   - Read `solution.x` as a D×P matrix; map values 1..K to `pillar_names[k]`.

## Output format

Write the full JSON to `content-calendar-{brand-slug}-{YYYY-MM-DD}.json`. The JSON schema (extension of BaseAgentOutput):

```json
{
  "generatedAt": "2026-05-20T17:30:00Z",
  "agentId": "content_strategy_agent",
  "version": "1.0.0",
  "brandSlug": "posthog",
  "calendar": {
    "days": 14,
    "platforms": ["LinkedIn", "X", "Instagram", "YouTube", "TikTok", "Email", "Blog"],
    "pillars": ["AI_growth", "Founder_journey", "Building_with_AI", "MarTech", "Health_AI"],
    "schedule": [
      { "day": 1, "platform": "X", "pillar": "AI_growth" },
      { "day": 3, "platform": "Instagram", "pillar": "AI_growth" },
      ...
    ],
    "pillarCounts": { "AI_growth": 6, "Founder_journey": 4, ... },
    "platformCadenceActual": { "LinkedIn": 4, "X": 7, ... }
  },
  "solverResult": {
    "status": "optimal",
    "objective": 70,
    "templateUsed": "assignment-with-diversity",
    "solveTimeMs": 1240,
    "values": { ... },
    "activeConstraints": ["cadence_x", "pillar_min_health_ai", "diversity_youtube"]
  },
  "config": {
    "cadenceUsed": { "LinkedIn": 4, "X": 7, ... },
    "minGapUsed": { "LinkedIn": 5, "X": 3, ... },
    "pillarFitUsed": { "AI_growth": ["LinkedIn", "X", "Instagram", "YouTube", "TikTok", "Email", "Blog"], ... },
    "pillarBoundsUsed": { "AI_growth": [2, 6], ... },
    "pillarWeightsUsed": { "AI_growth": 5, ... }
  }
}
```

Print to the chat in this order:

1. **Calendar grid** — D rows × P columns. Day on the left, platforms across the top, pillar name in each cell (or `—` for no-post). Looks like:

   ```
   ## 14-day content calendar — posthog (objective: 70)

   | Day | LinkedIn | X            | Instagram   | YouTube   | TikTok      | Email       | Blog        |
   |---  |---       |---           |---          |---        |---          |---          |---          |
   | 1   | —        | AI_growth    | —           | —         | —           | —           | —           |
   | 2   | —        | —            | —           | —         | —           | —           | —           |
   | 3   | —        | —            | AI_growth   | —         | —           | —           | —           |
   | ... | ...      | ...          | ...         | ...       | ...         | ...         | ...         |
   | 14  | —        | Building_AI  | Building_AI | —         | —           | AI_growth   | —           |
   ```

2. **Pillar coverage summary** — counts per pillar, with the configured min/max bounds for visibility.

3. **Cadence summary** — posts per platform vs target cadence (should match exactly).

4. **Config table** — the `pillar_fit`, `pillar_min/max`, `min_gap`, and `pillar_weight` values used. Founder can spot anything to override and re-run.

5. **Sensitivity notes** (1–3 lines):
   - "Raising LinkedIn cadence from 4 to 6 would add 2 long-form posts (objective +10)."
   - "Dropping the Health_AI pillar floor from 1 to 0 frees 1 slot for Founder_journey (objective +3)."

## Quality bar

- **All platforms hit cadence exactly.** If cadence[p] = 4, the schedule has exactly 4 non-zero entries in column p. Off-by-one = bug in the model.
- **Diversity is honored.** No two same-pillar posts within `min_gap[p] - 1` days on the same platform. Verify post-hoc.
- **Pillar fit is honored.** No pillar appears on a platform where `pillar_fit[k,p] = 0`. Verify post-hoc.
- **Pillar bounds are honored.** Every pillar's total count is in `[pillar_min[k], pillar_max[k]]`.
- **Solver invocation uses `assignment-with-diversity` template verbatim from `solver-patterns`.** Do not re-author the model structure.
- **Sentinel row 0 is included in `pillar_fit`.** Skipping this = silent out-of-bounds errors in the solver.
- **Feasibility precheck runs before solver.** Sum-cadence-vs-pillar-floor is a 2-line check; saves a 30s timeout when constraints are obviously inconsistent.

## Common pitfalls

- **Pillar list from `/positioning-pass` ignored.** The whole point of the GTMVP loop is that the calendar derives from positioning. If the founder ran `/positioning-pass` 5 minutes ago, USE THOSE PILLARS — don't re-derive from a URL crawl.
- **`pillar_fit` set too restrictively.** If a pillar's only allowed platform has cadence=1 but pillar_min=4, infeasible. Pre-check.
- **Cadence summing below pillar_min total.** Same infeasibility — caught by the precheck.
- **Treating `optimal: false` as a failure.** Calendar problems rarely have a single optimal — satisficing within timeout is the norm. Only flag if `satisfiable: false`.
- **Forgetting to map x[d,p] = 0 → "no post".** The schedule output should skip zeros and only list scheduled posts. Don't show 98 cells with 70+ "—" rows; show the 24-or-so scheduled posts in date order.
- **Inventing platform names not in the channel taxonomy.** Stick to canonical slugs from `data/channel-taxonomy.json` for joinability with `/channel-score` output.

## Cross-references

- `skills/solver-patterns/SKILL.md` §7 — the `assignment-with-diversity` template this command instantiates.
- `skills/gtm-output-schemas/SKILL.md` §8 — runtime conventions (fresh-model, labeling, timeout).
- `skills/gtm-output-schemas/SKILL.md` §8.8 — the `solverResult` output block schema (now includes `'assignment-with-diversity'` in the `templateUsed` enum).
- `commands/positioning-pass.md` — produces the pillar list this command consumes.
- `commands/channel-score.md` — produces the active-platform allocation this command consumes.
