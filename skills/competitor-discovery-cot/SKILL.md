---
name: competitor-discovery-cot
description: Use when you need to identify a defensible set of direct, cross-shoppable competitors for a B2B brand — not a list of mega-corps that show up because they share a keyword. Provides the 4-step chain-of-thought (define profile → must-have overlap criteria → systematic search → cross-shop validation) plus the disqualifier rules that reject HubSpot/Salesforce/Adobe-class false positives when the target is sub-$50M ARR. Cited by the competitor-mapper agent and the /competitor-map slash command.
---

# Competitor Discovery (Chain-of-Thought)

The single most common failure mode of automated competitor discovery is returning a mega-corp list. Customer of a 30-person B2B agency does not cross-shop HubSpot. This skill is the disqualifier-first method that fixes it.

When invoked, run all four steps before producing any output. Skipping steps is the fastest way to fail.

## Inputs you need

Before you can do this work, gather:

- **Brand name** + URL
- **Industry** + sub-vertical (specific, not "B2B SaaS" — "AI-powered customer support for Shopify Plus merchants")
- **Value proposition** (one sentence)
- **Specific services / product modules** (the *combination*, not individual capabilities)
- **Target customer profile** (firmographics + role + size band)
- **Price tier** (premium / mid-market / budget)

If you don't have these, ask for them or pull them from the brand's site before proceeding. Do not guess.

## Step 1 — Define the competitive profile

Pin down the exact shape of the company you're searching against:

- **Business model:** Agency / SaaS / Consulting / Marketplace / Hybrid
- **Company size band:** sub-$10M ARR / $10-50M / $50-250M / $250M+
- **Service combination:** the *exact* combination, not individual capabilities. ("AI automation + paid ads" is the combination. Finding companies that do only one of those is a Step 4 failure.)
- **Target ICP:** specific firmographic + role profile, not "B2B"
- **Price tier:** what the customer expects to pay

Write each of these as a single explicit statement before continuing.

## Step 2 — Identify must-have overlap criteria

From the profile, declare:

- **The 2-3 characteristics that are ABSOLUTELY REQUIRED** for a candidate to be a direct competitor. Without all three, they are at most "indirect."
- **Disqualifiers:** what immediately rules a company out (e.g., "is a horizontal platform with 50+ feature modules," "team size >500," "primary customer is enterprise / Fortune 1000," "self-serve only with no sales motion when target is sales-led")
- **Geographic scope:** local / regional / national / global

If you cannot name disqualifiers, you have not defined the profile tightly enough. Go back to Step 1.

## Step 3 — Search systematically

Work outward in concentric rings:

1. **Same sub-niche, same size band, same price tier** — the strongest matches
2. **Adjacent sub-niches with same service combination** — second-strongest
3. **Regional variants of the same business model** — for local/regional plays
4. **Indirect alternatives:** different approach to the same problem (e.g., DIY tooling vs done-for-you)
5. **Substitutes:** different solutions that solve the same underlying job-to-be-done

**Hard rule:** Ignore companies that are 10x+ larger than the target unless the target is itself enterprise-scale. A $5M ARR boutique agency does not compete with a $5B platform — they share a keyword, not a customer.

## Step 4 — Validate each candidate (the cross-shop test)

For every candidate, ask one question and answer it explicitly:

> **"Would a real customer actually cross-shop these two companies?"**

If the answer requires hedging ("well, theoretically..." or "if they grew 10x..."), the candidate is not a direct competitor.

Secondary checks:

- Do they compete for the *same projects* at *similar budgets*?
- Is the competitive threat **real and current** (not theoretical or future)?
- Would the brand owner recognize this company as competition? (If they'd say "huh, never heard of them" or "lol, that's not us" — they're wrong about the candidate.)

## Output schema

Return JSON. The agent calling this skill must conform to the `competitor_mapper_agent` output schema (see `gtm-output-schemas` skill, §6.1):

```json
{
  "competitorSet": [
    {
      "domain": "actual-website.com",
      "name": "Company Name",
      "segment": "What sub-niche they're in",
      "sizeBand": "sub-$10M | $10-50M | $50-250M | $250M+",
      "crossShopProbability": 0.85,
      "overlapVector": [
        { "audience": "exact-match | adjacent | partial" },
        { "problem": "exact-match | adjacent | partial" },
        { "pricePoint": "same-tier | one-tier-up | one-tier-down" },
        { "channels": ["list of shared go-to-market channels"] }
      ],
      "positioningPhrase": "How they describe themselves on their homepage",
      "primaryAdvantage": "What they do better than the target",
      "primaryWeakness": "Where the target can attack them"
    }
  ],
  "rejectedCandidates": [
    {
      "domain": "huge-platform.com",
      "reason": "mega_corp | wrong_icp | different_problem | different_price"
    }
  ],
  "whitespaceGaps": [
    {
      "gap": "What no competitor in this set is doing well",
      "evidence": "Specific evidence from competitor analysis",
      "viableFor": ["Which target customer segments this gap matters to"]
    }
  ],
  "recommendations": [
    { "type": "positioning | offer | channel", "priority": "high | medium | low", "suggestion": "...", "reason": "..." }
  ]
}
```

## Quality bar

- **3-6 high-quality candidates.** More than 6 means you didn't apply the disqualifiers; fewer than 3 means you didn't search broadly enough across rings.
- **Real domains only.** No `example.com`, no placeholders, no inferred-but-unverified URLs.
- **`rejectedCandidates` is mandatory.** Document at least 2-3 rejections — this is evidence the disqualifier logic ran.
- **`whitespaceGaps` is the highest-leverage section.** It surfaces where the brand can attack. Don't skip it.

## Common failure modes (avoid)

| Failure | What it looks like | Fix |
|---|---|---|
| Mega-corp drift | Salesforce, HubSpot, Adobe in the list for a sub-$50M brand | Apply Step 2 disqualifier hard |
| Keyword overlap | Two companies share "AI" but solve different problems | Use Step 4 cross-shop test |
| Half-overlap | Found companies doing one of two services in the combination | Re-check Step 1 — the *combination* is the requirement |
| Theoretical competition | "If they pivoted, they'd compete" | Step 4: real and current only |
| No rejections logged | Empty `rejectedCandidates` array | You skipped Step 2 — go back |

## When NOT to use this skill

- For a **lightweight win/loss touch list** during a sales call — overkill, just grep the CRM.
- For **investor-deck competitive grids** — those need a flatter format with feature comparisons, not the cross-shop method.
- For **acquisition-target sourcing** — different criteria (financial fit, integration fit), not competitive overlap.
