---
description: Apply Porter's Five Forces to a market or sub-vertical. Outputs scored forces (0-10), market concentration, competitive intensity, overall attractiveness, and ranked strategic implications.
argument-hint: [market-or-sub-vertical-name]
---

# /porters-scan

Invokes the `porters-five-forces` skill to assess structural attractiveness of a market — the strategist's pre-mortem before you commit capital or strategy.

## Argument

`$ARGUMENTS` — a market or sub-vertical name (e.g., "AI customer-support SaaS for Shopify Plus merchants" or "boutique B2B SaaS marketing agencies $1-10M ARR"). The more specific the better. If missing, ask.

## Steps

1. **Confirm the market scope.** Specific sub-niche, not a top-level category. "Marketing software" is too broad; "AI-powered ad-creative generation for B2C DTC brands" is right.

2. **Gather inputs.** Either pull from prior audit context or ask:
   - 3-5 representative competitors in the space (or run `/competitor-map` first)
   - Key customer segments + price sensitivity
   - Supply-side dependencies (vendors, platforms, data)
   - Substitute solutions

3. **Apply the `porters-five-forces` skill.** Score each force 0-10:
   - **Threat of new entrants** — capital requirements, regulatory moats, network effects
   - **Bargaining power of suppliers** — supplier concentration, switching costs
   - **Bargaining power of buyers** — customer concentration, price transparency, switching costs
   - **Threat of substitutes** — alternatives, especially AI-driven substitutes reshaping the space
   - **Competitive rivalry** — number, similarity, growth rate, differentiation, exit barriers

4. **Compute overall attractiveness.** `10 – avg(forces)`. Note: high force = pressure = bad for incumbents.

5. **Produce strategic implications** — 3-5 ranked, each tied to a specific force and actionable.

6. **Note unknowns.** Where data was thin, document it — don't paper over with confidence you don't have.

## Output format

Write to `porters-scan-{market-slug}-{YYYY-MM-DD}.md`:

- Market scope (specific)
- Per-force breakdown (level, score, factors, evidence)
- Overall attractiveness (score, summary)
- Strategic implications (ranked, actionable)
- Confidence + unknowns

## Quality bar

- **Every score cites a factor.** No bare numbers.
- **Strategic implications are concrete.** "Differentiate" is not actionable.
- **Unknowns are surfaced.** Confidence < 0.6 → flag as preliminary.
- **AI substitutes are addressed explicitly.** In 2026, almost every category has AI substitutes reshaping it. If you didn't address that, you missed it.

## When to chain with other commands

- Run `/competitor-map` first if you don't have a competitor set — Porter's needs one
- Run `/porters-scan` as part of `/gtm-audit` — it's Stage 5 of the full audit
- Run `/channel-score` after — high-rivalry markets have different optimal channel mixes than low-rivalry ones

## Common pitfalls

- Scoping the market too broadly — every force scores high in a broad market
- Treating "many competitors" as automatic high rivalry without checking growth + differentiation
- Static analysis — note recent direction (rising/stable/falling) when evidence supports it
- Missing AI substitute pressure — biggest force-reshape happening right now in most categories
