---
description: Sharpen a brand's positioning using competitive whitespace and the cross-shop disqualifier. Extracts current positioning, identifies what's vague or commoditized, and proposes 3 sharper alternatives with rationale.
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

5. **Draft 3 sharper positioning alternatives:**
   - **Option A — Anchor sharpening:** narrow the audience anchor while keeping the value prop
   - **Option B — Mechanism shift:** lead with how it works rather than what it does
   - **Option C — Outcome lock:** lead with a specific quantified outcome
   
   Each option includes: hero headline (≤90 chars), subheadline (≤140 chars), and a 2-sentence rationale citing whitespace + competitor matrix.

6. **Recommend a primary option with reasoning.** Don't be wishy-washy — pick one and defend it.

## Output format

Write to `positioning-pass-{brand-slug}-{YYYY-MM-DD}.md` with sections:

1. Current positioning (quoted exactly)
2. Diagnosis (per-element classification)
3. Competitor matrix
4. Whitespace identified
5. Three options with rationale
6. Primary recommendation

## Quality bar

- **Quotes are exact.** Don't paraphrase the current state — that hides specificity issues.
- **Whitespace is real.** "No competitor talks about ROI" is fake whitespace; every B2B competitor talks about ROI.
- **Options are different from each other.** If A and B are minor word swaps, you didn't do the work.
- **Recommendation has conviction.** Pick one, defend it.

## Common pitfalls

- Suggesting positioning that requires a feature the brand doesn't have
- Sharpening for a buyer the brand doesn't actually serve well
- Beautiful copy that scores worse on specificity than the original
- Ignoring the URL slug, page title, OG tags — positioning is more than the hero
