---
name: swot-analysis
description: Use when synthesizing strengths/weaknesses/opportunities/threats for a brand into a strategic-priority list — not for generic SWOT-as-content output. Output ties each S/W/O/T back to evidence, cross-references competitor insights, and produces a ranked strategic priorities list. Cited by the brand-strategist agent and /gtm-audit slash command.
---

# SWOT Analysis (Strategy-Grade)

Most SWOT outputs are useless because they're vague ("strong brand," "limited resources") and disconnected from action. This skill enforces evidence-anchoring and produces a ranked strategic-priorities list as the actual deliverable — the four S/W/O/T quadrants are inputs to the priorities, not the output.

## When to invoke

- Annual or quarterly strategic planning
- Pre-fundraise strategic narrative
- M&A diligence (target's strategic position)
- After a major competitive move (new entrant, competitor pivot)
- After a major macro shift (regulation, economic downturn, AI disruption)

Don't use for sales-collateral SWOTs — those want a flatter, more flattering format.

## Inputs

- Brand: name, industry, value proposition, differentiators
- Brand intelligence: target audience, products/services, market size, growth trends
- Recommended channels (if known)
- **Competitor intelligence:** at least 3-5 direct competitors with their positioning + differentiators (use `competitor-discovery-cot` first if missing)
- Market trends affecting the category

If competitor data is missing, surface that in `dataQuality` — without it the SWOT degrades to a generic blurb.

## The four quadrants — what each means

| Quadrant | Source | Question | Trap to avoid |
|---|---|---|---|
| **Strengths** | Internal | What does this brand do better than alternatives? | "Strong team" — too vague. Be specific: "20+ years selling into mid-market healthcare" |
| **Weaknesses** | Internal | What internal limitations constrain growth? | "Limited resources" — generic. Be specific: "No retention program; CAC payback 18 months" |
| **Opportunities** | External | What favorable market conditions could the brand pursue? | Restating market trends. The opportunity is what *this brand specifically* can do with the trend |
| **Threats** | External | What unfavorable external forces could damage the brand? | "Competition" — bare. Be specific: "Hubspot bundling AI features at zero marginal cost compresses our category's pricing" |

## Method

Work in this order:

1. **Establish data sufficiency.** What's known? What's assumed? What's missing? Set `dataQuality` accordingly: `excellent` (all sources), `good` (most), `fair` (some), `poor` (mostly inference).
2. **Pass through each quadrant once with evidence.** Each item must cite the source: brand intelligence, competitor analysis, market data, observed channel performance. Items without evidence are downgraded or dropped.
3. **Identify cross-quadrant tensions.** Where does a Strength enable an Opportunity? Where does a Weakness magnify a Threat? These are the strategic levers.
4. **Rank strategic priorities.** From the cross-quadrant analysis, produce 3-5 priorities ranked by impact × feasibility. Each priority must answer: what to do, why, and what to stop doing.
5. **Set confidence.** Not all SWOTs are equal. State your confidence (0-1) and why.

## Output schema

```json
{
  "strengths": [
    "Specific internal strength backed by evidence (3-7 items)"
  ],
  "weaknesses": [
    "Specific internal weakness backed by evidence (3-7 items)"
  ],
  "opportunities": [
    "Specific external opportunity tied to a market trend (3-7 items)"
  ],
  "threats": [
    "Specific external threat tied to a market force or competitor move (3-7 items)"
  ],
  "competitorInsights": {
    "competitive_advantages": ["Where this brand beats the named competitors, specifically"],
    "competitive_gaps": ["Where named competitors are stronger"],
    "market_opportunities": ["Unmet customer needs surfaced by competitor analysis"]
  },
  "marketInsights": {
    "industry_trends": ["Trends actively reshaping this category (12-24 months)"],
    "market_forces": ["Macro forces — economic, technological, regulatory"],
    "growth_areas": ["Sub-segments with above-average growth"]
  },
  "strategicPriorities": [
    {
      "priority": "Specific action — what to do",
      "rationale": "Why this priority is ranked here, citing the SWOT evidence",
      "impact": "high | medium | low",
      "effort": "high | medium | low",
      "stopDoing": "What this priority explicitly de-prioritizes (a SWOT without trade-offs is a wishlist)"
    }
  ],
  "confidence": 0.85,
  "dataQuality": "excellent | good | fair | poor"
}
```

## Quality bar

- **3-7 items per quadrant.** Fewer = thin analysis; more = unranked dump.
- **Every item is evidence-anchored.** No bare assertions.
- **Strategic priorities have a `stopDoing` field.** A SWOT without an explicit trade-off is wishful thinking.
- **`dataQuality: 'fair'` or worse triggers a recommendation to gather more intel before acting.** Bad data + confident SWOT = expensive strategy mistakes.

## Common pitfalls

- **Strengths that read like marketing copy.** "Best-in-class customer support" is sales material. "Sub-2hr median first response on enterprise tier" is a Strength.
- **Opportunities that are just trends.** "Market is growing" is not an opportunity. "Market growing 18% CAGR + our highest-LTV segment is healthcare which is growing 24%" is.
- **No internal/external split.** S/W must be internal; O/T must be external. If a "Strength" is "growing market," it's an Opportunity.
- **Strategic priorities that aren't actually trade-offs.** "Invest in marketing AND product AND sales" is not a priority list.
