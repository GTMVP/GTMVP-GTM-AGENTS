---
description: Map a defensible competitor set for a B2B brand using the cross-shop disqualifier method. Rejects mega-corp false positives. Outputs direct/indirect/substitute competitors plus whitespace gaps.
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

4. **Render a readable summary** with:
   - The brand profile (so the user sees what was matched against)
   - Direct competitors (3-6) with cross-shop probability + primary advantage + primary weakness
   - Rejected candidates with reasons (transparency about the disqualifier)
   - Whitespace gaps (where the brand can attack)
   - Recommendations

## Output format

Write the structured JSON to a file (`competitor-map-{brand-slug}-{YYYY-MM-DD}.json`), then print the readable summary in chat.

## Quality bar

- **No `example.com` or made-up domains.** Real targets only.
- **`whitespaceGaps[]` is the highest-leverage section.** Don't let it be empty.
- **Cross-shop probability is justified.** A `0.85` that's not backed by audience/problem/price overlap = unsupported.

## When to chain with other commands

- Run `/competitor-map` **before** `/positioning-pass` — positioning needs the competitive set
- Run `/competitor-map` **before** `/gtm-audit` if you want to validate the competitor set first; the audit will run it as Stage 2 anyway
- Run `/porters-scan` **after** to layer market-structure context onto the competitive picture
