---
description: Sharpen a brand's positioning using competitive whitespace and the cross-shop disqualifier. Extracts current positioning, identifies what's vague or commoditized, proposes 3 sharper alternatives with rationale, and mathematically verifies whitespace via Z3 constraint solver.
argument-hint: [brand-url]
---

# /positioning-pass

Most B2B brands describe themselves the same way as their competitors. This command sharpens positioning by triangulating: current positioning + competitor positioning + audience-specific whitespace.

## Argument

`$ARGUMENTS` — brand URL (required). If missing, ask.

## Steps

1. **Extract current positioning.** Fetch the homepage and pull:
   - Hero headline
   - Subheadline / lede
   - Primary value-prop sentence
   - "About" page positioning paragraph (if present)
   - Pricing-page positioning (often subtly different from homepage)

   Quote the exact text. Don't paraphrase yet.

2. **Diagnose the current positioning.** For each pulled element, classify:
   - **Specific** vs **Vague**: does it name a specific outcome / customer / mechanism?
   - **Differentiated** vs **Commodified**: would 5 competitors say the same thing?
   - **Believable** vs **Hyperbolic**: does the claim feel earned or aspirational?
   - **Anchored** vs **Floating**: tied to a real ICP or a generic "businesses"?

3. **Run a competitor positioning sweep.** Invoke `competitor-mapper-agent` (or load existing `competitor-map-*.json` if recent). For each direct competitor, pull their hero headline. Build a positioning matrix:

   ```
   Brand        | Headline                  | Anchor              | Mechanism
   -----------------------------------------------------------------------------
   Target       | [...]                     | [...]               | [...]
   Competitor 1 | [...]                     | [...]               | [...]
   ...
   ```

4. **Identify whitespace.** From the matrix, find:
   - **Anchor whitespace:** an audience or use case nobody is naming specifically
   - **Mechanism whitespace:** a "how it works" angle nobody owns
   - **Outcome whitespace:** a specific result no competitor claims

5. **Verify whitespace mathematically (Z3 solver).** Encode the positioning landscape as an N-dimensional space and use the `max-min-distance` template from `skills/solver-patterns` (Template 3) to find the provably-optimal positioning vector.

   **Dimension encoding.** Score each brand (target + competitors) on 5 dimensions, each 1.0–10.0:

   | Dimension | What it measures | How to score |
   |-----------|-----------------|--------------|
   | `price_tier` | Premium vs budget positioning | 1=free/budget, 5=mid-market, 10=enterprise premium |
   | `audience_sophistication` | Technical depth of buyer | 1=non-technical SMB owner, 10=staff engineer |
   | `feature_depth` | Breadth of capability claims | 1=single-feature tool, 10=platform/suite |
   | `channel_fit` | Primary acquisition channel implied | 1=PLG/self-serve, 5=mixed, 10=enterprise sales |
   | `defensibility_commitment` | What moat they're building | 1=commodity/reskin, 10=deep tech/data/network |

   **Envelope constraints.** The founder's defensibility envelope defines which regions of the space are credible for the brand. Derive from the brand's actual product, team, and market:
   - `envelope_lows[d]`: minimum credible score on each dimension (e.g. a solo founder can't credibly claim 9 on `feature_depth`)
   - `envelope_highs[d]`: maximum credible score (e.g. a $49/mo tool can't claim 9 on `price_tier`)

   **Solver flow (per `skills/solver-patterns` §3 and `skills/gtm-output-schemas` §8):**
   1. `clear_model` — fresh session
   2. Build competitor points from the positioning matrix (Step 3)
   3. Set envelope from brand analysis (Step 1–2)
   4. `add_item` calls per Template 3 (max-min-distance with Manhattan distance)
   5. `solve_model` with 10s timeout
   6. On SAT: extract optimal positioning vector + `min_dist` + per-competitor distances
   7. On UNSAT: the envelope is entirely inside a competitor's shadow — report which envelope bounds to relax
   8. `clear_model` — cleanup

   **Post-solve analysis.** After extracting the optimal vector:
   - Rank dimensions by contribution to separation (largest `|pos[d] - nearest_comp[d]|`)
   - Identify the 3 nearest competitors and their distances
   - Flag any dimension where the brand's current positioning (from Step 2) is >2.0 away from the solver-recommended position — this is the "repositioning effort" signal

6. **Draft 3 sharper positioning alternatives:**
   - **Option A — Anchor sharpening:** narrow the audience anchor while keeping the value prop
   - **Option B — Mechanism shift:** lead with how it works rather than what it does
   - **Option C — Outcome lock:** lead with a specific quantified outcome
   
   Each option includes: hero headline (≤90 chars), subheadline (≤140 chars), and a 2-sentence rationale citing whitespace + competitor matrix.

   **Solver-informed drafting.** Use the optimal positioning vector from Step 5 to ground each option:
   - The dimension with the highest separation contribution should anchor at least one option
   - Each option's implied positioning vector should be sketched (5 rough scores) and compared against the solver optimum — options close to the optimum get a "solver-validated" tag
   - If the solver found dimensions where current positioning is >2.0 from optimal, at least one option must address that gap

7. **Recommend a primary option with reasoning.** Don't be wishy-washy — pick one and defend it. Reference the solver's whitespace measurement as quantitative evidence: "Option B positions you 3.2 weighted-Manhattan units from your nearest competitor vs. 1.1 today."

## Output format

Write to `positioning-pass-{brand-slug}-{YYYY-MM-DD}.md` with sections:

1. Current positioning (quoted exactly)
2. Diagnosis (per-element classification)
3. Competitor matrix
4. Whitespace identified (qualitative)
5. **Solver-verified whitespace** (quantitative — new)
6. Three options with rationale (solver-validated tags where applicable)
7. Primary recommendation (with distance measurement)

### Solver output block (embed in section 5)

```json
{
  "positioningWhitespace": {
    "optimalVector": { "price_tier": 3.2, "audience_sophistication": 7.1, "feature_depth": 4.0, "channel_fit": 2.5, "defensibility_commitment": 6.8 },
    "currentVector": { "price_tier": 5.0, "audience_sophistication": 6.0, "feature_depth": 6.0, "channel_fit": 5.0, "defensibility_commitment": 4.0 },
    "minDistanceToNearestCompetitor": 4.7,
    "currentDistanceToNearestCompetitor": 1.1,
    "nearestCompetitors": [
      { "name": "Competitor A", "distance": 4.7, "separatingDimensions": ["price_tier", "defensibility_commitment"] },
      { "name": "Competitor B", "distance": 5.2, "separatingDimensions": ["audience_sophistication"] }
    ],
    "repositioningEffort": [
      { "dimension": "defensibility_commitment", "currentScore": 4.0, "optimalScore": 6.8, "gap": 2.8 }
    ],
    "envelope": { "lows": [1, 5, 2, 1, 3], "highs": [6, 9, 7, 5, 9] },
    "solverStatus": "optimal"
  }
}
```

## Quality bar

- **Quotes are exact.** Don't paraphrase the current state — that hides specificity issues.
- **Whitespace is real.** "No competitor talks about ROI" is fake whitespace; every B2B competitor talks about ROI.
- **Options are different from each other.** If A and B are minor word swaps, you didn't do the work.
- **Recommendation has conviction.** Pick one, defend it.
- **Solver result is grounded.** The 5-dimension scores must be defensible from the brand's actual site content and competitor analysis — not fabricated to produce a pretty distance number. If the scoring is arbitrary, the solver output is theater.
- **At least one option is solver-validated.** If all three options diverge wildly from the optimal vector, explain why (e.g. the envelope was too narrow, or qualitative factors dominate).

## Common pitfalls

- Suggesting positioning that requires a feature the brand doesn't have
- Sharpening for a buyer the brand doesn't actually serve well
- Beautiful copy that scores worse on specificity than the original
- Ignoring the URL slug, page title, OG tags — positioning is more than the hero
- Setting the defensibility envelope too wide ("1–10 on everything") — produces trivial corner solutions with no strategic meaning
- Scoring dimensions subjectively without grounding in the brand's actual homepage copy and pricing page — garbage in, garbage out
- Ignoring the `repositioningEffort` signal — recommending a position that's optimal but requires the brand to become a different company
