---
name: marketing-channel-scoring
description: Use when ranking marketing channels for a specific brand and ICP using the 28-channel taxonomy in this plugin. Outputs a scored channel-mix recommendation with rationale per channel, dependencies, a sequenced rollout plan, and a provably-optimal monthly budget allocation via the solver-z3 MCP server. Cited by the channel-scorer agent and /channel-score slash command. Reads data/channel-taxonomy.json.
---

# Marketing Channel Scoring

The 28-channel taxonomy in this plugin (`data/channel-taxonomy.json`) is a comprehensive catalog of marketing micro-channels with structured metadata: inputs, outputs, KPIs, tactics, dependencies, and reference solutions. This skill is the scoring framework that turns that taxonomy into a brand-specific channel-mix recommendation.

## When to invoke

- Annual or quarterly channel planning
- New product launch — where to invest first
- Diagnostic on a stalled growth program
- Post-funding deployment — where does the new capital go
- Inside a deep audit (`/gtm-audit`) — channel recommendation step

Don't use for single-channel optimization (e.g., "should I increase my Google Ads budget?"). This is portfolio-level allocation, not in-channel tuning.

## Inputs

- Brand context: industry, ICP, product, price tier, current revenue
- Stage: pre-PMF / post-PMF early / scaling / mature
- Current channel mix and performance (if available)
- Budget and team constraints
- The taxonomy: load `data/channel-taxonomy.json` and reference channels by their canonical `agent_id`

## The scoring framework

For each of the 28 channels, score on **5 dimensions** (1-10 each). The composite is a weighted sum.

| Dimension | What it measures | Default weight |
|---|---|---|
| **ICP fit** | How well does this channel reach *this brand's* ICP? Not "B2B" — the specific firmographic + role + size band. | 0.30 |
| **Stage fit** | Is this channel right for this maturity stage? PR doesn't work for pre-PMF; SEO doesn't work fast enough for a 6-month runway. | 0.20 |
| **Capital efficiency** | Cost per qualified pipeline / revenue per dollar spent, given the brand's price tier and ACV. | 0.20 |
| **Time-to-signal** | How fast can the brand learn whether this channel works? Days = 10, weeks = 7, months = 4, quarters = 2. | 0.15 |
| **Defensibility** | Does this channel compound (SEO, community, brand)? Or is it rented (paid)? | 0.15 |

Each channel ends up with:

- 5 dimension scores (1-10)
- 1 composite score (weighted average)
- A confidence (0-1)
- 2-4 sentences of rationale tying scores to specific evidence

## Cross-channel rules

After per-channel scoring, apply these portfolio rules:

1. **Dependencies first.** Channels declare dependencies in the taxonomy (`dependencies: [agent_id]`). A dependent channel cannot precede its dependency in the rollout. Example: `agent_seo_interlinking_005` depends on `agent_seo_onpage_001` — schedule on-page first.
2. **Don't run more than 3 paid channels concurrently** unless you have a dedicated paid-media operator. Spread = noise = no learning.
3. **At least one compounding channel.** If everything in the recommendation is paid (rented audience), flag this — the brand is building no defensibility.
4. **At least one fast-feedback channel.** If everything is long-cycle (SEO, PR, podcast), the brand learns nothing for two quarters. Add at least one channel with `time-to-signal ≥ 7`.
5. **Stage gates.** Pre-PMF brands shouldn't run brand campaigns; mature brands shouldn't ignore retention. Check stage fit hard.

## Output schema

```json
{
  "summary": {
    "brand": "Brand name",
    "stage": "pre-PMF | post-PMF early | scaling | mature",
    "icpDescription": "...",
    "totalChannelsScored": 28,
    "topChannelsRecommended": 5
  },
  "channelScores": [
    {
      "agentId": "agent_seo_keyword_001",
      "name": "On-Page SEO Optimizer",
      "macroChannel": "SEO",
      "scores": {
        "icpFit": 8,
        "stageFit": 6,
        "capitalEfficiency": 9,
        "timeToSignal": 3,
        "defensibility": 9
      },
      "compositeScore": 7.05,
      "confidence": 0.82,
      "rationale": "ICP search intent is high; SEO is capital-efficient at this ACV. Time-to-signal is the constraint.",
      "dependencies": [],
      "recommended": true
    }
  ],
  "rolloutPlan": {
    "phase1_now": [
      { "agentId": "agent_xxx", "reason": "Fast-feedback, ICP-aligned, no dependencies" }
    ],
    "phase2_next_quarter": [
      { "agentId": "agent_xxx", "reason": "Depends on phase 1; high defensibility" }
    ],
    "phase3_year_two": [
      { "agentId": "agent_xxx", "reason": "Long-cycle; only after fast channels established" }
    ],
    "explicitlyDeprioritized": [
      { "agentId": "agent_xxx", "reason": "Wrong stage or wrong ICP fit" }
    ]
  },
  "portfolioCheck": {
    "compoundingChannelsCount": 2,
    "fastFeedbackChannelsCount": 2,
    "concurrentPaidChannels": 2,
    "dependencyOrderingValid": true,
    "warnings": []
  },
  "optimalAllocation": {
    "status": "optimal",
    "monthlySpendByChannel": {
      "agent_seo_onpage_001": 6200,
      "agent_content_blog_010": 11800,
      "agent_paid_search_015": 9400,
      "agent_email_drip_021": 6300,
      "agent_seo_keyword_002": 1300
    },
    "totalAllocated": 35000,
    "monthlyBudget": 35000,
    "predictedPipelineScore": 2661.6,
    "greedyBaselineScore": 2344.4,
    "sensitivities": [
      { "ifBudgetAdded": 5000, "unlocks": "agent_paid_linkedin_018", "marginalScore": 124.0, "rationale": "Adds fast-feedback paid LinkedIn at min_viable + buffer" },
      { "ifConstraintRelaxed": "min_compounding", "marginalScore": 12.0, "tradeoff": "Drops $4K from blog into paid_search; no compounding channel = zero defensibility" }
    ],
    "activeConstraints": ["budget_cap", "dep_seo_keyword_needs_seo_onpage", "team_capacity", "min_compounding", "min_fast_feedback"],
    "economicsDefaults": [
      { "agent_id": "agent_seo_onpage_001", "min_viable_spend_usd": 1500, "max_useful_spend_usd": 8000, "source": "macro_seo_default" }
    ],
    "solveTimeMs": 308,
    "templateUsed": "linear-allocation"
  },
  "confidence": 0.78
}
```

## Optimal allocation via constraint solver (new, 2026-05-19)

The `optimalAllocation` block is produced by `/channel-score` after the per-channel scoring step, by invoking the `solver-z3` MCP server with the `linear-allocation` template from the `solver-patterns` skill. The block is **provably optimal** under the founder's stated budget, team capacity, max-concentration, and dependency/categorical constraints — meaning no other allocation under those exact constraints achieves a higher objective.

The objective is `Σ score[c] × √spend[c]` (diminishing returns), approximated via 5-breakpoint piecewise-linear sqrt per the `solver-patterns` template.

**When the solver fails (infeasible or timeout):**

`status: "infeasible"` means the founder's hard constraints can't all be satisfied. The `unsatCore[]` field surfaces which constraints conflict (labeled in plain English, e.g. `budget_cap`, `min_compounding`, `dep_seo_keyword_needs_seo_onpage`). The `relaxationSuggestions[]` array provides at most 2 prose suggestions, prioritized by least-disruptive.

`status: "timeout"` means the solver couldn't find an answer in 10 seconds. Treat as functional infeasibility — the constraint set is computationally hard.

In both cases, the `optimalAllocation` block is still present in the output; downstream consumers should check `status` before reading `monthlySpendByChannel`.

**Per-channel economics — where do `min_viable_spend_usd` / `max_useful_spend_usd` come from?**

v1 (current): the founder either supplies a 28-row CSV via the `--economics` flag, or `/channel-score` derives defaults from `default_config.daily_budget × 30` (where present in the taxonomy) and `agent_type` macros (see `commands/channel-score.md` Step 5).

v2 (planned): a curated `data/channel-economics.json` companion file in this plugin, calibrated against B2B SaaS price tiers.

The `economicsDefaults[]` array in the output shows which values were used and where they came from (`founder_supplied` | `taxonomy_default_config` | `macro_<type>_default`), so the founder can audit + override.

## Quality bar

- **All 28 channels scored.** Not just the recommended ones — explicit deprioritization is information.
- **Composite scores match the weighted math.** Don't fudge.
- **Rollout plan respects dependencies.** Use the taxonomy's `dependencies` field literally.
- **`portfolioCheck` is mandatory.** This is where common failures (no compounding, no fast feedback, too much paid concurrency) get caught.
- **`explicitlyDeprioritized` lists at least 5-10 channels.** A recommendation that says "do all 28" is not a recommendation.
- **`optimalAllocation` block is mandatory when a budget is provided.** Status `optimal` means the dollar allocation is provably best under stated constraints. Status `infeasible` or `timeout` MUST include `unsatCore` and `relaxationSuggestions`.
- **Solver model construction uses the `linear-allocation` template verbatim.** Do not re-author the Z3 code from prose — copy the template structure and fill slots.

## Common pitfalls

- **ICP-fit score that's actually capability score.** "We could do SEO" is not ICP fit. "Our ICP googles for solutions in a discoverable way" is.
- **Stage fit ignored.** Most B2B SaaS founders try to run the playbook of the company they want to be (mature). Score for the stage they're *in*.
- **Defensibility = "paid is bad."** It's not. Paid is fine if the brand has high LTV and the unit economics work. Defensibility just goes to zero when you stop spending.
- **Top 5 recommendation that's all the same macro channel.** Suggests poor ICP analysis — most ICPs don't live in one channel.
- **No dependency check.** Recommending interlinking before on-page is mechanical failure.

## Reading the taxonomy

The `data/channel-taxonomy.json` shape:

```json
{
  "metadata": { "name", "version", "macro_channels": [...] },
  "agents": [
    {
      "agent_id": "agent_seo_onpage_001",
      "name": "On-Page SEO Optimizer",
      "agent_type": "seo",
      "agent_category": "on_page_seo",
      "macro_channel": "SEO",
      "inputs": [...],
      "outputs": [...],
      "kpis": [...],
      "tactics": [...],
      "dependencies": [],
      "default_config": {...},
      "solution_examples": [...]
    }
  ]
}
```

When scoring, cite the canonical `agent_id` (not freeform names) so downstream consumers can join across runs.
