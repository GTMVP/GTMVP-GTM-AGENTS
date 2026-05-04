---
description: Run a full GTM audit on a brand — orchestrates brand-strategist, competitor-mapper, SWOT, Porter's, and channel scoring into one synthesis. Takes a URL or brand name as argument.
argument-hint: [url-or-brand-name]
---

# /gtm-audit

The flagship orchestration command for this plugin. Pipelines six analysis stages into a unified GTM intelligence brief.

## Argument

`$ARGUMENTS` — a website URL (preferred) or brand name. If neither is provided, ask the user before proceeding.

## Pipeline

Run these stages in order. Each stage consumes the prior stage's output. **Use the Task tool with `subagent_type` to invoke each agent so they run in isolated context windows.**

### Stage 1 — Crawl + brand context (preflight)

Fetch the brand's site (homepage, /about, /pricing, /features, /customers if present). Extract:

- Brand name + tagline
- One-sentence value proposition
- Specific products / services
- Pricing model + price tier (premium / mid-market / budget)
- Target customer signals (case-study logos, ICP language)
- Industry + sub-vertical

Persist this as the "brand context" — every downstream stage will reference it.

### Stage 2 — Competitor mapping

Invoke `competitor-mapper-agent` with the brand context. The agent uses the `competitor-discovery-cot` skill to apply the cross-shop disqualifier and produce 3-6 defensible competitors, rejected candidates, and whitespace gaps.

Block on output. The brand-strategist needs this.

### Stage 3 — Brand strategy (TAM/SAM/SOM + horizons)

Invoke `brand-strategist-agent` with the brand context + competitor set. The agent runs the 6-dimension analysis using the `tam-sam-som-horizons` skill: market sizing, niche, products, opportunities (quick wins / medium / long), customer journey, brand & messaging.

### Stage 4 — Strategic SWOT

Apply the `swot-analysis` skill to the brand using context + competitor data. Produce S/W/O/T quadrants + cross-quadrant priorities with `stopDoing` fields.

### Stage 5 — Market structure (Porter's Five Forces)

Apply the `porters-five-forces` skill to the brand's sub-vertical. Produce the five-force scoring + overall attractiveness + strategic implications.

### Stage 6 — Channel scoring

Apply the `marketing-channel-scoring` skill against the 28-channel taxonomy in `data/channel-taxonomy.json`. Produce per-channel scores, the rollout plan (now / next quarter / year two), and the portfolio check.

## Synthesis output

After all six stages complete, produce a single synthesis document with these sections:

1. **Executive summary** (5-7 bullets, every bullet cites a stage's evidence)
2. **The market and the niche** (Stage 3 + Stage 5 condensed)
3. **The competitive set** (Stage 2 — top 3-5 competitors + the whitespace gaps)
4. **Strategic priorities** (Stage 4 priorities + Stage 3 horizons, ranked by impact × feasibility, with explicit stop-doings)
5. **Channel mix and rollout** (Stage 6 — phase 1 / phase 2 / phase 3)
6. **Open questions and confidence** (where data quality was thin, what to investigate before acting)

Write the synthesis to a file named `gtm-audit-{brand-slug}-{YYYY-MM-DD}.md` in the user's current working directory unless they specify otherwise.

## Quality bar

- **Don't skip stages.** Each downstream stage relies on the prior. If a stage fails or produces low-confidence output, surface that — don't paper over it.
- **All references are to the canonical schemas.** The synthesis isn't a creative writing exercise; every section ties back to structured agent output.
- **Confidence is honest.** If competitor data is thin or pricing isn't on the site, the audit's confidence drops accordingly. Say so.
- **Every recommendation is actionable.** "Improve positioning" is not actionable. "Tighten positioning from 'AI marketing platform' to 'AI-powered demand-gen co-pilot for B2B SaaS founders post-PMF' to escape the HubSpot comparison" is.

## When to skip stages

- Skip Stage 5 (Porter's) for very early-stage / pre-PMF brands — market structure analysis is premature.
- Skip Stage 6 (channel scoring) if the brand has explicitly asked for a strategic-only audit (no execution layer yet).
- Always run Stages 1-4 — they're the foundation.
