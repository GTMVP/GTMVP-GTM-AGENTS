---
description: Map a defensible competitor set for a B2B brand using the cross-shop disqualifier method. Rejects mega-corp false positives. Outputs direct/indirect/substitute competitors plus whitespace gaps. Applies Z3 set-cover solver to guarantee optimal competitive coverage across feature dimensions.
argument-hint: [domain-or-brand-name]
---

# /competitor-map

Invokes the `competitor-mapper-agent` to produce a defensible competitor set — not the mega-corp keyword-overlap list that most automated tools spit out.

## Argument

`$ARGUMENTS` — a domain (e.g. `acme.com`) or brand name. If missing, ask before proceeding.

## Steps

1. **Crawl the brand's site** — homepage + about + pricing + features. Extract:
   - Industry + sub-vertical (specific, not "B2B SaaS")
   - Specific service combination
   - Target ICP (firmographic + role + size band)
   - Price tier (premium / mid-market / budget)
   - One-sentence value proposition

   If any of these can't be derived from the site, ask the user before proceeding. The competitor map is only as good as the input profile.

2. **Invoke `competitor-mapper-agent`** via the Task tool with the extracted profile as context.

3. **Validate the agent's output:**
   - 3-6 competitors in `competitorSet[]`
   - At least 2-3 entries in `rejectedCandidates[]` (proves the disqualifier ran)
   - At least one entry in `whitespaceGaps[]`
   - Every `crossShopProbability` has `overlapVector` evidence

   If any check fails, push the agent to refine — don't accept thin output.

4. **Optimize the competitive set via solver (Z3 set cover).** The agent's raw output may contain 6+ candidates. Use the `set-cover` template from `skills/solver-patterns` (Template 4) to pick the K competitors (default K=5) that maximally cover the feature/positioning space.

   **Dimension extraction.** From each candidate in `competitorSet[]`, derive coverage tags across these feature dimensions:

   | Dimension | Source |
   |-----------|--------|
   | `pricing_model` | Pricing page: freemium, usage-based, seat-based, flat-rate, enterprise-custom |
   | `primary_channel` | How they acquire: PLG, content/SEO, outbound, partnerships, paid |
   | `tech_stack_layer` | Where they sit: infrastructure, platform, application, workflow |
   | `buyer_persona` | Who decides: developer, marketer, ops, executive, mixed |
   | `deployment_model` | Cloud-only, self-hosted, hybrid, on-prem |
   | `geographic_focus` | Global, NA-only, EU-focused, APAC-first |
   | `maturity_stage` | Startup, growth, established, enterprise |

   Each competitor covers the dimensions where it has a differentiating presence. A competitor "covers" a dimension value if its positioning explicitly or implicitly claims that value.

   **Solver flow (per `skills/solver-patterns` §4 and `skills/gtm-output-schemas` §8):**
   1. `clear_model` — fresh session
   2. Build coverage matrix: N candidates × M dimension-values
   3. Set `target_size = 5` (or user-supplied `--competitors` flag)
   4. Set `min_coverage_per_dim = 1` — every dimension value must be covered
   5. `add_item` calls per Template 4 (set-cover)
   6. `solve_model` with 10s timeout
   7. On SAT: the selected K competitors are the optimal monitoring set
   8. On UNSAT: not enough candidates to cover all dimensions at the requested K — report which dimension-values are uncovered and suggest expanding the candidate search
   9. `clear_model` — cleanup

   **Output.** Replace the ad-hoc "pick most relevant" selection with the solver's optimal set. Include a coverage map showing which selected competitor covers which dimension-value, and flag dimension-values with only 1 cover (single-point-of-comparison risk).

5. **Render a readable summary** with:
   - The brand profile (so the user sees what was matched against)
   - **Solver-selected competitors** (K, default 5) with cross-shop probability + primary advantage + primary weakness
   - **Coverage map** — table showing which competitor covers which dimension-value. Flag single-cover dimensions with ⚠️
   - Rejected candidates with reasons (transparency about the disqualifier)
   - Whitespace gaps (where the brand can attack)
   - Recommendations

## Output format

Write the structured JSON to a file (`competitor-map-{brand-slug}-{YYYY-MM-DD}.json`), then print the readable summary in chat.

### Solver output block (embed in JSON output)

```json
{
  "clusterCover": {
    "selectedCompetitors": ["comp_a", "comp_b", "comp_c", "comp_d", "comp_e"],
    "coverageMap": {
      "pricing_model:usage_based": ["comp_a", "comp_c"],
      "pricing_model:seat_based": ["comp_b"],
      "primary_channel:plg": ["comp_a", "comp_d"],
      "buyer_persona:developer": ["comp_a", "comp_e"]
    },
    "singleCoverRisks": ["pricing_model:seat_based"],
    "uncoveredDimensions": [],
    "solverStatus": "optimal"
  }
}
```

## Quality bar

- **No `example.com` or made-up domains.** Real targets only.
- **`whitespaceGaps[]` is the highest-leverage section.** Don't let it be empty.
- **Cross-shop probability is justified.** A `0.85` that's not backed by audience/problem/price overlap = unsupported.
- **Coverage map has no blind spots.** Every dimension-value in the landscape should be covered by at least one selected competitor. If `uncoveredDimensions` is non-empty, explain why and suggest expanding the candidate pool.
- **Single-cover risks are flagged.** A dimension covered by only one competitor is fragile — if that competitor pivots or dies, the intel gap opens instantly.

## When to chain with other commands

- Run `/competitor-map` **before** `/positioning-pass` — positioning needs the competitive set
- Run `/competitor-map` **before** `/gtm-audit` if you want to validate the competitor set first; the audit will run it as Stage 2 anyway
- Run `/porters-scan` **after** to layer market-structure context onto the competitive picture
