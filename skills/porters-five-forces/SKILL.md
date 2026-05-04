---
name: porters-five-forces
description: Use when assessing the structural attractiveness of a market or sub-niche before committing strategy or capital. Outputs Porter's Five Forces analysis with numerical scores per force, market concentration assessment, and ranked strategic implications. Cited by /porters-scan slash command and the brand-strategist agent's market-context section.
---

# Porter's Five Forces

A market is attractive when the five forces are weak (low competitive pressure). When forces are strong, profits get squeezed and even good companies struggle. This skill produces a scored, evidence-anchored five-forces analysis suitable for a strategy memo.

## When to invoke

- Evaluating a new market entry (geographic expansion, new vertical, new product line)
- Pre-mortem on a strategic bet
- Investor-deck "why now / why us" market analysis
- Annual strategic refresh — where does pricing power sit?

Don't use it for tactical campaign decisions. This is structural analysis, not channel optimization.

## Inputs

- Brand name + industry
- Sub-vertical / micro-niche (specific)
- Number and shape of competitors (use `competitor-discovery-cot` first if you don't have a defensible set)
- Customer segments + price sensitivity intel
- Supply-side / vendor / labor dependencies
- Substitute solutions customers might use

If any of these are unknown, mark them in the output's `unknowns` array — do not invent.

## The five forces

### 1. Threat of new entrants

How easily can a new competitor enter and capture share?

**Scoring drivers (raise = high threat):**
- Low capital requirements
- No regulatory moat
- No proprietary technology required
- Low brand-loyalty friction
- Low economies of scale

**Scoring drivers (lower = low threat):**
- High capital intensity
- Regulated/licensed market
- Network effects already entrenched
- Proprietary data or distribution

### 2. Bargaining power of suppliers

How much can input providers (vendors, labor, infrastructure) dictate terms?

**High supplier power signals:**
- Few suppliers / supplier concentration
- High switching cost between suppliers
- Suppliers can forward-integrate
- Critical input with no substitute

### 3. Bargaining power of buyers

How much can customers dictate price and terms?

**High buyer power signals:**
- Customer concentration (few large buyers)
- Low switching cost
- Buyer can backward-integrate (build it themselves)
- Product is undifferentiated / commoditized
- High price transparency

### 4. Threat of substitutes

What alternative solutions solve the same job-to-be-done?

**High substitute threat signals:**
- Alternative with better price-performance
- Low switching cost to substitute
- Substitute is improving rapidly (e.g., AI replacing manual workflows)
- Buyer's job-to-be-done can be solved another way

### 5. Competitive rivalry

How intense is rivalry among existing competitors?

**High rivalry signals:**
- Many competitors of similar size (fragmented market)
- Slow industry growth (zero-sum)
- Low product differentiation
- High exit barriers (capital, contracts)
- Recurring price wars

## Output schema

```json
{
  "threatOfNewEntrants": {
    "level": "low | medium | high",
    "score": 6.5,
    "factors": ["Specific factor with evidence", "..."],
    "barriers": ["Existing barriers to entry in this market"],
    "opportunities": ["How the brand can strengthen barriers"]
  },
  "bargainingPowerOfSuppliers": {
    "level": "low | medium | high",
    "score": 5.0,
    "factors": ["..."],
    "keySuppliers": ["Types of critical suppliers"],
    "risks": ["Supply chain risks"]
  },
  "bargainingPowerOfBuyers": {
    "level": "low | medium | high",
    "score": 7.0,
    "factors": ["..."],
    "buyerSegments": ["Key customer segments"],
    "priceSensitivity": "Low | Medium | High — with reasoning"
  },
  "threatOfSubstitutes": {
    "level": "low | medium | high",
    "score": 4.0,
    "substitutes": ["Alternative 1", "Alternative 2"],
    "switchingCosts": "Low | Medium | High — with reasoning",
    "factors": ["..."]
  },
  "competitiveRivalry": {
    "level": "low | medium | high",
    "score": 8.0,
    "numberOfCompetitors": 12,
    "marketConcentration": "Fragmented | Moderately concentrated | Highly concentrated",
    "competitionFactors": ["Key competitive factors"],
    "differentiationLevel": "Low | Medium | High — with reasoning"
  },
  "overallAttractiveness": {
    "score": 6.2,
    "summary": "One-paragraph assessment",
    "strategicImplications": [
      "Strategic recommendation 1 — what to do given the forces",
      "Strategic recommendation 2",
      "Strategic recommendation 3"
    ]
  },
  "confidence": 0.75,
  "unknowns": ["What you couldn't assess due to missing data"]
}
```

## Scoring guide

- **0-3 = low force** (favorable to incumbents)
- **4-6 = medium force** (balanced)
- **7-10 = high force** (unfavorable, profit-squeezing)

For **overall attractiveness**, the math is *inverted*:

- Score = 10 – (average of the five forces)
- 7-10 = highly attractive market
- 4-6 = moderately attractive
- 0-3 = unattractive (high pressure, low returns)

## Quality bar

- **Every score must cite at least one specific factor.** No bare numbers.
- **Strategic implications must be actionable.** "Differentiate" is not actionable. "Move from horizontal to vertical SaaS positioning to escape buyer concentration in the SMB segment" is.
- **Confidence < 0.6 means flag the analysis as preliminary.** Don't pretend certainty you don't have.
- **`unknowns` array is mandatory.** What you can't assess is information.

## Common pitfalls

- **Treating "many competitors" as automatically high rivalry.** Many *similar-sized* competitors with *low differentiation* in a *slow-growth* market = high rivalry. Many competitors in fast-growth markets often co-exist fine.
- **Ignoring substitutes.** AI is reshaping substitute threat in almost every category right now. If your substitute analysis doesn't mention AI tooling that could solve the job differently, you missed it.
- **Static analysis.** Forces shift. Note recent direction (rising / stable / falling) when evidence supports it.
