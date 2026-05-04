---
description: Score all 28 marketing micro-channels for a specific brand and stage, producing a sequenced rollout plan with phase 1 / phase 2 / phase 3 and explicit deprioritizations.
argument-hint: [brand-url-or-context-file]
---

# /channel-score

Applies the `marketing-channel-scoring` skill to produce a portfolio-level channel mix recommendation — not single-channel optimization.

## Argument

`$ARGUMENTS` — a brand URL OR a path to a context file containing prior audit output (`gtm-audit-*.md` synthesis, `competitor-map-*.json`, etc.). If missing, ask.

## Steps

1. **Establish brand context.** Either:
   - Crawl the URL and derive: industry, sub-vertical, ICP, price tier, stage (pre-PMF / post-PMF early / scaling / mature), current channel mix if visible
   - Or load the context file and extract the same fields
   
   Stage matters. Ask for it explicitly if you can't infer.

2. **Load `data/channel-taxonomy.json`** from this plugin's directory. Confirm 28 agents are present.

3. **Apply `marketing-channel-scoring` skill** — score every channel on the 5 dimensions (ICP fit, stage fit, capital efficiency, time-to-signal, defensibility), compute weighted composites, run portfolio checks (compounding count, fast-feedback count, paid concurrency, dependency ordering).

4. **Produce the rollout plan:**
   - Phase 1 (now): 3-5 channels with no dependencies, fast feedback, ICP-aligned
   - Phase 2 (next quarter): channels that depend on phase 1 or build defensibility
   - Phase 3 (year two): long-cycle channels (PR, podcast, SEO at scale)
   - Explicitly deprioritized: 5-10+ channels with reasons

5. **Render the recommendation** with composite-score table, rollout phases, and the portfolio check warnings.

## Output format

Write the full JSON to `channel-score-{brand-slug}-{YYYY-MM-DD}.json`, then print:

- A table of the top 10 channels by composite score (name, macro channel, score, recommended yes/no)
- The 3-phase rollout plan
- Any portfolio warnings (no compounding channels? all paid? wrong stage?)

## Quality bar

- **All 28 channels scored.** Skipping channels = incomplete portfolio analysis.
- **Composite scores match the weighted math.** Default weights: ICP 0.30, stage 0.20, capital efficiency 0.20, time-to-signal 0.15, defensibility 0.15.
- **Dependency check.** A recommended channel with an unfulfilled dependency in the same phase = error.
- **Portfolio warnings are surfaced.** Not buried — top of the output.

## Common pitfalls

- Recommending a channel because it's trendy ("everyone's doing AI SEO") without ICP fit
- Phase 1 with all paid channels (no compounding, no defensibility)
- Phase 1 with all long-cycle channels (no fast feedback for 6 months)
- Ignoring stage — pre-PMF brands shouldn't run brand campaigns
