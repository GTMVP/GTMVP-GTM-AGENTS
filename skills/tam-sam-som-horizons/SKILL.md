---
name: tam-sam-som-horizons
description: Use when sizing a market and translating it into a horizon-based strategic plan — TAM/SAM/SOM with quick-wins (0-3mo), medium plays (3-12mo), and long bets (12mo+). Includes 6-dimension brand analysis (market, niche, products, opportunities, customer journey, brand & messaging). Cited by the brand-strategist agent and /gtm-audit slash command.
---

# TAM/SAM/SOM + Strategic Horizons

This skill produces a market-sizing + strategic-roadmap pair. The market sizing tells you *how big the prize is*; the horizons tell you *what to do in what order*. Most "strategy decks" do one or the other and produce nothing actionable.

## When to invoke

- Investor-deck market sizing slide
- Annual planning — where to invest
- Pre-launch market opportunity assessment
- Major channel or vertical expansion decision

Skip for tactical work. This is the strategist's pass, not the marketer's.

## Inputs

Pull from a website scrape or interview:

- **Brand name** + industry + value proposition
- **Specific products and services** (not just categories)
- **Pricing and business model** (subscription / one-time / usage / enterprise)
- **Target customer profile** (firmographics, role, jobs-to-be-done)
- **Existing competitive landscape** (use `competitor-discovery-cot` if needed)
- **Key messaging and brand voice** (from homepage and content)

If competitor data, ICP, or pricing is missing, the analysis will be shallow — flag in confidence.

## The 6 dimensions

Work through all six in order. Each feeds the next.

### 1. The Market — Total opportunity space

- **TAM** (Total Addressable Market): the global/regional revenue pool if the brand captured 100% of every conceivable buyer. Cite a basis (research firm, derivable from public data). Don't invent a number; if you have to estimate, document the math.
- **SAM** (Serviceable Addressable Market): the slice the brand could *realistically* reach given product, channel, geography, and language. Apply explicit filters from TAM.
- **SOM** (Serviceable Obtainable Market): realistic 1-3 year capture given current scale, sales motion, and competitive density. Be honest — if SAM is $2B and the brand is a 30-person team, SOM is not $200M.
- **Market dynamics**: growth rate, maturity stage, disruption potential
- **Macro trends** shaping the market (tech, regulation, consumer behavior)

### 2. The Niche — Exact competitive positioning

- **Micro-niche**: precise, not broad. Not "B2B SaaS" — "AI-powered customer support for Shopify Plus merchants doing $5-50M GMV"
- **Niche maturity**: emerging / growing / mature / declining
- **Direct competitors** (3-5 named)
- **Indirect competitors / substitutes**
- **Competitive intensity**: low / medium / high
- **Positioning strength**: weak / moderate / strong / dominant
- **Blue/red ocean score**: 0-10 (0 = brutal red, 10 = pristine blue)

### 3. Products & Services — Deep dive

- Core products with detailed descriptions
- Pricing strategy and business model
- USPs per offering
- Product-market fit signals (case studies, customer logos, retention indicators)
- Tech stack / methodology (when evident)
- Expansion gaps (where the product line could grow)

### 4. Strategic Opportunities — Actionable horizons

The heart of the skill. Each horizon has its own decision rules:

| Horizon | Time | Decision rule | Examples |
|---|---|---|---|
| **Quick wins** | 0-3 months | Reversible, low capital, high signal-to-noise | Fix a broken funnel step; launch one new ICP segment; bundle two existing offers |
| **Medium plays** | 3-12 months | Requires investment but is strategically defensible | Launch a new product module; enter one adjacent vertical; build out a partner channel |
| **Long bets** | 12+ months | Transformative, harder to reverse, higher payoff | Platform pivot; M&A; new business model; new geography |

Each opportunity gets `impact` (high/medium/low), `effort` (high/medium/low), `capacity_cost` (person-months), and `prerequisite_ids` (list of initiative IDs that must complete before this one can start) tags.

**Solver-backed scheduling (Z3, per `skills/solver-patterns` Template 5).** After generating the candidate initiatives across all three horizons, use the `scheduling-with-deps` template to produce a feasible schedule that respects:
- Dependency DAG — no initiative starts before its prerequisites complete
- Capacity per horizon — total person-months per horizon ≤ available capacity
- Horizon assignments — quick-wins in 0-3mo, medium plays in 3-12mo, long bets in 12mo+
- Maximize cumulative strategic value (Σ impact_score × horizon_weight)

**Solver flow (per `skills/solver-patterns` §5 and `skills/gtm-output-schemas` §8):**
1. `clear_model` — fresh session
2. Build initiative nodes with capacity costs, dependencies, and horizon assignments
3. `add_item` calls per Template 5
4. `solve_model` with 10s timeout
5. On SAT: extract the scheduled order with critical-path identification
6. On UNSAT: capacity too tight for all dependencies — report bottleneck initiatives and suggest deferring lowest-value items
7. `clear_model` — cleanup

**Critical-path output.** Identify which initiatives are bottlenecks — removing them delays the most downstream initiatives. Surface these as "strategic-path-critical" items that deserve extra resources or de-risking.

Top 3 priorities surface from the solver's optimal schedule, not just the impact-effort grid.

### 5. Customer Journey — Map the funnel

- **Awareness**: how do prospects discover them? Channel mix and effectiveness
- **Consideration**: what proof do they provide? (case studies, demos, trials)
- **Decision**: self-serve vs sales-led, decision factors
- **Retention**: customer success indicators
- **Friction points** in the current journey
- **Conversion optimization opportunities**

### 6. Brand & Messaging — Communication strategy

- Detected tone and voice
- Core messaging pillars
- Emotional vs rational appeal balance
- Audience sophistication (1-5: 5 = highly technical, 1 = mass market)
- Brand maturity stage (startup / growth / enterprise)

## Output schema

The full output mirrors the donor brand-strategist schema — see `gtm-output-schemas` skill, §6.2 for the full shape. Required top-level keys:

```json
{
  "market": {
    "tam": "...",
    "sam": "...",
    "som": "...",
    "marketDynamics": "...",
    "growthRate": "...",
    "macroTrends": ["..."]
  },
  "niche": {
    "microNiche": "...",
    "nicheMaturity": "emerging | growing | mature | declining",
    "directCompetitors": [{"name": "...", "positioning": "..."}],
    "indirectCompetitors": ["..."],
    "competitiveIntensity": "low | medium | high",
    "positioningStrength": "weak | moderate | strong | dominant",
    "blueOceanScore": 6
  },
  "productServices": { /* see §6.2 */ },
  "strategicOpportunities": {
    "topPriorities": [
      { "priority": "...", "reasoning": "...", "impact": "high|medium|low", "effort": "high|medium|low", "capacityCost": 2.0, "prerequisiteIds": [] }
    ],
    "quickWins": ["0-3 month opportunity 1", "..."],
    "mediumTerm": ["3-12 month opportunity 1", "..."],
    "longTerm": ["12+ month transformative opportunity 1", "..."],
    "untappedSegments": ["..."],
    "partnershipOpportunities": ["..."],
    "riskFactors": ["..."],
    "scheduledRoadmap": {
      "horizonAssignments": {
        "horizon_0_3mo": [{"id": "init_1", "capacityCost": 1.5}],
        "horizon_3_12mo": [{"id": "init_2", "capacityCost": 3.0, "blockedBy": ["init_1"]}],
        "horizon_12mo_plus": [{"id": "init_3", "capacityCost": 4.0, "blockedBy": ["init_2"]}]
      },
      "criticalPath": ["init_1", "init_2", "init_3"],
      "bottleneckInitiatives": ["init_1"],
      "deferredInitiatives": [{"id": "init_4", "reason": "capacity_overflow", "freedCapacity": 2.0}],
      "totalCapacityUsed": { "horizon_0_3mo": 1.5, "horizon_3_12mo": 3.0, "horizon_12mo_plus": 4.0 },
      "solverStatus": "optimal"
    }
  },
  "customerJourney": { /* see §6.2 */ },
  "brandMessaging": { /* see §6.2 */ },
  "confidence": 0.78,
  "dataQuality": "excellent | good | fair | poor"
}
```

## Quality bar

- **TAM/SAM/SOM each cite a basis.** "$2B TAM" with no source is a wish; "$2B TAM derived from Statista 2025 e-commerce CRM report ($14B global e-comm SaaS) × 14% CRM segment share" is an estimate.
- **Quick wins are actually quick.** If a "0-3 month" item requires a hire and a quarter of engineering, it's a medium play. Be honest.
- **Long bets are real bets.** "Become a thought leader" is not a long bet. "Build a 50-person services arm to land enterprise" is.
- **Top priorities reference the SWOT or competitor analysis.** Without that linkage they're floating recommendations.

## Common pitfalls

- **TAM inflation.** Stating TAM as "all marketing software ever" when the brand is one micro-feature. Use bottom-up math.
- **SOM over-promising.** A 30-person team is not capturing $100M in 24 months. Calibrate.
- **No mention of substitutes in the niche analysis.** Substitutes (especially AI substitutes right now) are eating most categories. Address them explicitly.
- **All horizons treated equally.** The point of horizons is sequencing. If everything is "quick win," nothing is.
