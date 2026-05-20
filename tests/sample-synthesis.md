# GTM Audit — Acme Corp — 2026-05-20

> **Solver status:** `solver-z3` OK · `solver-maxsat` OK · `solver-mzn` OK · PDF bundler invoked
> **Audit confidence:** Medium-High (positioning data thin on 2 of 5 competitors)

---

## 1. Executive summary

- **Positioning is squeezed** between HubSpot (incumbent) and Common Room (mid-market) — selected positioning vector `pv-3` widens distance to nearest competitor from 0.18 → 0.34 (Stage 7, `weight=8`, `confidence=0.82`).
- **Channel mix over-indexes on paid social** (62% of spend); MaxSAT selected re-allocation to founder-led content + lifecycle email (Stage 6, claims `ch-12`, `ch-17`).
- **One war-game-durable move**: vertical wedge into Series-A vertical SaaS (Stage 8, durability score `0.71`); two non-durable moves dropped to appendix.
- **Niche TAM is tight** (~$240M SAM at current ICP) — geographic expansion is a long-bet, not a quick win (Stage 5 Porter's: high buyer power, moderate substitution).
- **Filtered claims appendix** contains 4 dropped recommendations — all conflicted with the positioning anchor selected by Stage 9.

## 2. The market and the niche

| Dimension | Score (0-10) | Notes |
| --- | --- | --- |
| Market growth | 7 | CAGR 18% through 2028 |
| Niche concentration | 5 | Top-5 ~ 41% share |
| Buyer sophistication | 8 | Buyer is a CMO/Head-of-Growth |
| Switching cost | 4 | Light — month-to-month SaaS norm |
| Substitution risk | 6 | In-house tooling viable above $5M ARR |

**SAM:** $240M · **SOM (12-month realistic):** $11.5M (4.8% of SAM) · **TAM (global B2B SaaS post-PMF):** $2.1B.

## 3. The competitive set

Top 5 competitors by overlap with Acme's positioning vector:

| Competitor | Overlap | Pricing | Differentiator |
| --- | --- | --- | --- |
| HubSpot | 0.71 | $800-$3,200/mo | Brand, ecosystem |
| Common Room | 0.58 | $400-$1,200/mo | Community signal |
| Customer.io | 0.43 | $150-$900/mo | Lifecycle automation |
| Mutiny | 0.39 | $1,500+/mo | Web personalization |
| Pocus | 0.31 | $1,000+/mo | PLG signal scoring |

**Whitespace gaps:** founder-led ICP < $5M ARR + transparent pricing + open MCP integration — currently uncovered by all five.

## 4. Positioning whitespace

Selected positioning vector: `pv-3` — "AI-powered demand-gen co-pilot for B2B SaaS founders post-PMF."

- **Min-distance to nearest 3 competitors:** 0.34 (vs. baseline `pv-0` at 0.18)
- **Separation dimensions (top 3):**
  1. Founder-as-buyer (vs. Head-of-Growth)
  2. Transparent pricing
  3. MCP-native integration
- **Recommended:** lead with founder-buyer + MCP-native; pricing is a closer, not a hook.

## 5. Strategic priorities

Only MaxSAT-selected claims, ranked by `weight × confidence`:

```
[1]  pos-3   weight=8  conf=0.82  → Anchor positioning on founder-buyer + MCP
[2]  ch-12   weight=7  conf=0.78  → Shift 30% paid-social budget to founder-led content
[3]  wg-2    weight=7  conf=0.71  → Vertical wedge into Series-A vertical SaaS
[4]  ch-17   weight=6  conf=0.80  → Build lifecycle email cadence (4-touch)
[5]  swot-9  weight=6  conf=0.65  → Stop competing on HubSpot's ecosystem axis
```

**Explicit stop-doings:**

- Stop paying for category-level SEO keywords (HubSpot dominates SERP).
- Stop running webinar funnel — `conf < 0.4` across last 3 cohorts.

## 6. Competitor war-gaming

| Move | Durability | Proof | Predicate |
| --- | --- | --- | --- |
| Vertical wedge (Series-A SaaS) | 0.71 | HubSpot horizontal-by-design; can't follow without rebuild | `competitor_cannot_match_within_18mo(vertical_focus)` |
| Founder-led content | 0.42 | Easily copied by Common Room | Dropped — not durable |
| Free tier under 50 contacts | 0.38 | Customer.io can match in one quarter | Dropped — not durable |

## 7. Channel mix and rollout

```
Phase 1 (0-3mo):  Founder-led LinkedIn (40%) · Lifecycle email (25%) · Paid retargeting (15%)
Phase 2 (3-12mo): Add podcast tour + co-marketing with 2 MCP-adjacent tools
Phase 3 (12mo+):  Category-defining content (book/research) + paid LI at scale
```

**Deprioritized:** TikTok (B2B ICP mismatch), Reddit organic (low-trust for $5K+ ARR product), Pinterest (no signal).

## 8. 14-day content calendar

| Day | LinkedIn | X | Newsletter |
| --- | --- | --- | --- |
| Mon | Pillar 1 | Pillar 2 | — |
| Tue | Pillar 3 | — | — |
| Wed | Pillar 2 | Pillar 1 | Issue #1 |
| Thu | Pillar 4 | Pillar 3 | — |
| Fri | Pillar 1 | Pillar 2 | — |

Pillar coverage: P1 (4) · P2 (4) · P3 (3) · P4 (2) · P5 (1).

## 9. Open questions and confidence

- Pricing data on Mutiny and Pocus is inferred from analyst reports — confidence 0.55. Confirm before public positioning.
- Customer.io's lifecycle-automation roadmap unknown — if they launch MCP-native in Q3, Move #1 durability drops to ~0.50.
- Acme's CAC payback period assumed 14 months — needs actual cohort data.

## 10. Filtered claims appendix

| Claim ID | Atomic claim | Reason dropped |
| --- | --- | --- |
| `ch-04` | Run aggressive HubSpot comparison ads on Google | Conflicts with `swot-9` (stop competing on HubSpot's axis) |
| `wg-5` | Acquire 2 small competitors in next 12 months | Below weight threshold; no incompatibility — solver picked higher-weight alternatives |
| `pos-7` | Pivot positioning to AI-agents-for-marketing | Conflicts with `pos-3` (founder-buyer anchor) |
| `ch-22` | Open AI-generated-podcast network | `confidence < 0.4` — not synthesis-ready |
