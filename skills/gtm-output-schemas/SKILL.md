---
name: gtm-output-schemas
description: Canonical input/output JSON schemas for the 18 GTM marketing agents in this plugin. Use when an agent needs to know the exact shape of its input parameters or output payload, or when a slash command needs to validate agent results before chaining them. Covers analytics, SEO, content, social, email, video, backlinks, PR, paid ads, PPC, influencers, podcast, conversion, mobile, plus the cross-cutting brand context, trust-tier, recommendation envelopes, and solver invocation conventions.
---

# GTM Output Schemas

Every agent in this plugin emits a structured payload that downstream agents and slash commands depend on. This skill is the canonical contract.

When you are operating as one of the 18 agents:

1. **Always** wrap output in `BaseAgentOutput`.
2. **Match field names exactly.** Downstream code is type-checked against these.
3. **Honor trust-tier flags.** Tier 4 outputs MUST set `executionBlocked: true`. Tier 5 outputs MUST set `executionBlocked: true` AND `alertsOnly: true`.
4. **Don't invent fields.** If a schema doesn't have a slot for a finding, put it in the agent's `recommendations[]` array using the appropriate recommendation type.
5. **Use ISO-8601 strings for timestamps.** Numbers are decimals (not strings) unless explicitly currency-formatted.

## 1. Trust-tier model

The 18 agents are organized across 5 autonomy tiers. The tier governs how much an agent is allowed to do without human review.

| Tier | Name | Behavior | Agents |
|---|---|---|---|
| 1 | Auto-Pilot | Executes autonomously, logs after the fact | analytics, technical-seo, local-seo |
| 2 | Co-Pilot | Drafts, queues, requires approval to publish | seo-keyword, content-strategy, email-automation, social-scheduler, video-content |
| 3 | Assistant | Researches + drafts, never sends without explicit human action | backlink-builder, pr-outreach, ad-optimizer, ppc, influencer-connect |
| 4 | Research | Output is intelligence only. Sets `executionBlocked: true` | podcast, conversion |
| 5 | Observer | Monitors + alerts only. Sets `executionBlocked: true` AND `alertsOnly: true` | mobile-marketing |

The 6 framework agents (brand-strategist, competitor-mapper, positioning-sharpener, offer-architect, angle-generator, channel-scorer) inherit Tier 4 (Research) by default — they never execute, only output structured intelligence.

## 2. Base contracts

Every agent input extends `BaseAgentInput`:

```ts
interface BaseAgentInput {
  brandId: string;                       // Required — links output to a brand
  userId?: string;                       // Optional — operator running the call
  parameters?: Record<string, unknown>;  // Free-form overrides
}
```

Every agent output extends `BaseAgentOutput`:

```ts
interface BaseAgentOutput {
  generatedAt: string;     // ISO-8601 UTC, e.g. "2026-05-03T20:30:00Z"
  agentId: AgentId;        // Stable slug, see §3
  version: string;         // SemVer of the agent prompt that produced this
}
```

## 3. Agent IDs (stable slugs)

```ts
type AgentId =
  // Tier 1
  | 'analytics_agent' | 'technical_seo_agent' | 'local_seo_agent'
  // Tier 2
  | 'seo_keyword_agent' | 'content_strategy_agent' | 'email_automation_agent'
  | 'social_scheduler_agent' | 'video_content_agent'
  // Tier 3
  | 'backlink_builder_agent' | 'pr_outreach_agent' | 'ad_optimizer_agent'
  | 'ppc_agent' | 'influencer_connect_agent'
  // Tier 4
  | 'podcast_agent' | 'conversion_agent'
  // Tier 5
  | 'mobile_marketing_agent'
  // Framework agents (this plugin adds these on top of the donor 16)
  | 'brand_strategist_agent' | 'competitor_mapper_agent';
```

## 4. Cross-cutting envelopes

Several shapes recur across agents. Define once, cite many.

### 4a. Recommendation envelope

Most agents emit a `recommendations[]` array. Each recommendation is:

```ts
interface Recommendation {
  type: string;                              // Agent-specific enum, see per-agent schema
  priority: 'high' | 'medium' | 'low';       // Some agents add 'critical' (mobile-marketing)
  suggestion: string;                        // What to do
  reason?: string;                           // Why
  expectedImpact?: string;                   // Predicted business outcome

  // --- MaxSAT synthesis fields (§4e) ---
  // Required when `/gtm-audit` synthesis is the consumer.
  // Optional for standalone agent runs — backward compatible.
  claimId?: string;                          // Stable ID: "{agentId}.{type}_{seq}", e.g. "seo_keyword_agent.content_001"
  atomicClaim?: string;                      // One falsifiable statement. See §4e quality bar.
  incompatibleWithClaimIds?: string[];       // Explicit contradiction edges to claims from OTHER agents
  weight?: number;                           // 1-10, soft constraint priority for MaxSAT. 10 = must-have, 1 = nice-to-have.
  confidence?: number;                       // 0.0-1.0, agent's confidence this claim is correct given inputs
}
```

### 4b. Severity / rating enums (used widely)

```ts
type Severity = 'critical' | 'warning' | 'info';
type Rating   = 'good' | 'needs-improvement' | 'poor';
type Effort   = 'low' | 'medium' | 'high';
type Trend    = 'up' | 'stable' | 'down';
```

### 4c. Validation result (returned by every agent before producing output)

```ts
interface ValidationResult {
  valid: boolean;
  errors: string[];   // Empty when valid: true
}
```

### 4d. Execution result (the wrapper that orchestration sees)

```ts
interface AgentExecutionResult<TOutput> {
  success: boolean;
  output?: TOutput;
  error?: string;
  executionTime: number;        // Milliseconds
  tokenUsage?: { input: number; output: number; total: number };
  reasoningTrace: string[];     // Step-by-step reasoning for audit
}
```

### 4e. Atomic claims for MaxSAT synthesis

When `/gtm-audit` runs its synthesis step (Phase D1), it collects `recommendations[]` from every sub-agent and feeds them to a MaxSAT solver. The solver finds the **maximum-weight consistent subset** — the largest set of recommendations that don't contradict each other. This section defines the contract that makes recommendations MaxSAT-compatible.

#### Claim ID format

```
{agentId}.{type}_{sequence}
```

Examples: `seo_keyword_agent.content_001`, `ad_optimizer_agent.budget_003`, `content_strategy_agent.create_002`.

- `agentId` uses the stable slug from §3.
- `type` matches the agent's recommendation type enum (see §5).
- `sequence` is a zero-padded 3-digit counter, unique within a single agent run. Starts at `001`.
- The full `claimId` is globally unique within a `/gtm-audit` session.

#### Quality bar: falsifiable, not aspirational

Every `atomicClaim` must be a **single falsifiable statement** — something that can be proven true or false with data within 90 days. The test: "Could a competent analyst look at this claim in 90 days and say YES or NO?"

| Quality | Example | Why |
|---------|---------|-----|
| **BAD** | "Improve your SEO strategy" | Not falsifiable. What does "improve" mean? |
| **BAD** | "Consider investing in content marketing" | Aspirational. No measurable commitment. |
| **BAD** | "SEO is important for this brand" | Truism. Not actionable. |
| **GOOD** | "Targeting 'product analytics open source' (vol: 2.4K, KD: 45) will generate 150+ monthly organic visits within 6 months" | Falsifiable: specific keyword, measurable target, time-bound. |
| **GOOD** | "A weekly developer changelog newsletter will achieve 30%+ open rate for this audience segment" | Falsifiable: specific format, specific metric, specific threshold. |
| **GOOD** | "Reducing Google Ads CPA target from $50 to $35 will increase conversion volume by 20% without exceeding $10K monthly spend" | Falsifiable: specific input change, measurable outcome, budget constraint. |

Rules:
1. **One claim per recommendation.** If a recommendation contains two assertions ("do X AND do Y"), split into two recommendations.
2. **Include a number.** Every claim must contain at least one measurable quantity — a target, threshold, cost, volume, or percentage.
3. **Include a timeframe** when the claim involves a future outcome. Default: 90 days if not specified.
4. **No hedging language.** "Might improve", "could potentially", "should consider" are not claims. Commit or don't claim.

#### Weight assignment (1-10)

| Weight | Meaning | Use when |
|--------|---------|----------|
| 10 | Must-have — dropping this recommendation would be a critical error | Compliance, security, existential risk |
| 8-9 | Strong conviction — backed by multiple data signals | High-confidence quantitative finding |
| 5-7 | Moderate — supported by evidence but with uncertainty | Most standard recommendations |
| 3-4 | Speculative — reasonable hypothesis, limited data | Emerging opportunities, untested channels |
| 1-2 | Nice-to-have — low-impact or low-confidence | Optimization tweaks, cosmetic improvements |

Weight maps directly to the MaxSAT soft clause weight. Higher-weight claims are preferentially retained when contradictions force the solver to drop claims.

#### Confidence (0.0-1.0)

Confidence represents the agent's assessment of claim correctness given the available inputs. It is NOT the same as weight (which represents business importance).

- **0.9-1.0**: Claim is derived from direct measurement or authoritative data (e.g., GA4 shows 2.3% conversion rate)
- **0.7-0.8**: Claim is inferred from strong signals (e.g., competitor analysis, keyword tools, industry benchmarks)
- **0.5-0.6**: Claim is a reasonable inference with partial data (e.g., ICP analysis suggests this channel fits)
- **0.3-0.4**: Claim is speculative — informed guess based on pattern matching
- **0.0-0.2**: Don't emit the claim. If confidence is below 0.3, the agent should omit the recommendation entirely.

#### Incompatibility edges

`incompatibleWithClaimIds` declares explicit contradictions between claims from different agents. When two claims are incompatible, the MaxSAT solver can include at most one.

Common incompatibility patterns:

| Pattern | Example |
|---------|---------|
| **Budget competition** | `ad_optimizer_agent.budget_001` ("Allocate 60% of paid budget to Meta") conflicts with `ppc_agent.budget_001` ("Allocate 70% of paid budget to Google Ads") |
| **Channel conflict** | `content_strategy_agent.create_001` ("Publish 3 blog posts/week") conflicts with `video_content_agent.seo_001` ("Shift content investment to video tutorials") when team capacity is fixed |
| **Audience contradiction** | `social_scheduler_agent.timing_001` ("Post at 9am EST for enterprise audience") conflicts with `social_scheduler_agent.timing_002` ("Post at 7pm EST for developer audience") when brand targets both |
| **Strategic direction** | `brand_strategist_agent` claim ("Position as enterprise-grade") conflicts with `conversion_agent.cta_001` ("Use PLG self-serve signup flow") |

Rules:
1. **Cross-agent only.** An agent never declares incompatibility with its own claims — internal consistency is the agent's responsibility.
2. **Symmetric.** If A declares incompatibility with B, B should also declare incompatibility with A. However, the MaxSAT solver treats incompatibility as a hard constraint regardless of who declared it.
3. **Specific, not categorical.** Don't declare "all PPC claims conflict with all SEO claims." Declare specific claim-to-claim edges.
4. **Conservative.** Only declare incompatibility when executing BOTH claims would produce a contradictory or harmful outcome. Two claims that compete for budget are only incompatible if their combined spend exceeds the budget — if both fit within budget, they're compatible.

#### Per-agent atomic claim examples

Below are representative atomic claims for each agent tier, showing what well-formed claims look like in practice.

**Tier 1 — Auto-Pilot agents**

`analytics_agent`:
```json
{
  "claimId": "analytics_agent.insight_001",
  "atomicClaim": "Organic search drives 42% of conversions but receives only 15% of marketing spend — reallocating $3K/mo from display to SEO content will yield 25+ additional monthly conversions",
  "weight": 7,
  "confidence": 0.85,
  "incompatibleWithClaimIds": ["ad_optimizer_agent.budget_001"]
}
```

`technical_seo_agent`:
```json
{
  "claimId": "technical_seo_agent.technical_001",
  "atomicClaim": "LCP is 4.2s (poor) on /pricing — optimizing hero image and deferring below-fold JS will bring LCP under 2.5s (good) and recover an estimated 8% bounce rate reduction",
  "weight": 8,
  "confidence": 0.9,
  "incompatibleWithClaimIds": []
}
```

`local_seo_agent`:
```json
{
  "claimId": "local_seo_agent.fix_001",
  "atomicClaim": "NAP inconsistency across 7 of 12 citation sources for the Miami office — correcting phone number format to (305) 555-1234 on Yelp, YP, and Foursquare will resolve 58% of citation errors within 30 days",
  "weight": 6,
  "confidence": 0.95,
  "incompatibleWithClaimIds": []
}
```

**Tier 2 — Co-Pilot agents**

`seo_keyword_agent`:
```json
{
  "claimId": "seo_keyword_agent.content_001",
  "atomicClaim": "Creating a comparison page targeting 'posthog vs amplitude' (vol: 1.8K, KD: 38) will rank in top 5 within 4 months given current DA of 72 and generate 400+ monthly visits",
  "weight": 8,
  "confidence": 0.75,
  "incompatibleWithClaimIds": []
}
```

`content_strategy_agent`:
```json
{
  "claimId": "content_strategy_agent.create_001",
  "atomicClaim": "Publishing 2 technical tutorials per week (Python + JavaScript SDK guides) will increase organic blog traffic by 35% within 90 days based on keyword gap analysis showing 15 uncontested longtail terms with combined volume of 8K/mo",
  "weight": 7,
  "confidence": 0.7,
  "incompatibleWithClaimIds": ["video_content_agent.seo_001"]
}
```

`email_automation_agent`:
```json
{
  "claimId": "email_automation_agent.segment_001",
  "atomicClaim": "Segmenting the onboarding drip by 'installed SDK' vs 'signed up only' and sending SDK-specific tutorials to the installed segment will increase activation rate from 23% to 30% within 60 days",
  "weight": 7,
  "confidence": 0.65,
  "incompatibleWithClaimIds": []
}
```

`social_scheduler_agent`:
```json
{
  "claimId": "social_scheduler_agent.timing_001",
  "atomicClaim": "Posting technical content on LinkedIn at 10am EST Tuesday-Thursday will achieve 2.5x the engagement rate of the current random schedule, based on audience activity data showing 68% of followers active during business hours",
  "weight": 5,
  "confidence": 0.7,
  "incompatibleWithClaimIds": []
}
```

`video_content_agent`:
```json
{
  "claimId": "video_content_agent.seo_001",
  "atomicClaim": "A 5-part YouTube tutorial series on 'PostHog for startups' (est. 8-12 min each) will generate 10K+ views in 90 days and drive 200+ signups via video description CTAs, based on competitor tutorial performance in the product analytics niche",
  "weight": 6,
  "confidence": 0.55,
  "incompatibleWithClaimIds": ["content_strategy_agent.create_001"]
}
```

**Tier 3 — Assistant agents**

`backlink_builder_agent`:
```json
{
  "claimId": "backlink_builder_agent.strategy_001",
  "atomicClaim": "Guest posting on Dev.to, Hacker Noon, and The New Stack (3 posts over 6 weeks) will acquire 5+ DA 50+ backlinks and improve domain authority from 72 to 74 within 90 days",
  "weight": 6,
  "confidence": 0.6,
  "incompatibleWithClaimIds": []
}
```

`ad_optimizer_agent`:
```json
{
  "claimId": "ad_optimizer_agent.budget_001",
  "atomicClaim": "Reallocating 60% of the $10K paid social budget to LinkedIn (from current 40/40/20 Meta/LinkedIn/Display split) will reduce CPA from $85 to $60 for the enterprise ICP segment within 30 days",
  "weight": 7,
  "confidence": 0.65,
  "incompatibleWithClaimIds": ["ppc_agent.budget_001"]
}
```

`ppc_agent`:
```json
{
  "claimId": "ppc_agent.keyword_001",
  "atomicClaim": "Adding 'session replay tool' and 'feature flag service' as exact-match keywords with $4.50 max CPC will generate 15+ qualified clicks/day at a CPA under $45, based on search volume of 2.1K and 1.4K respectively",
  "weight": 7,
  "confidence": 0.7,
  "incompatibleWithClaimIds": []
}
```

`influencer_connect_agent`:
```json
{
  "claimId": "influencer_connect_agent.selection_001",
  "atomicClaim": "Partnering with 2 mid-tier dev YouTubers (50K-200K subscribers, >4% engagement rate) for sponsored integration tutorials will generate 500+ signups at a CAC under $25 per signup, based on comparable campaigns in the DevTools space",
  "weight": 5,
  "confidence": 0.5,
  "incompatibleWithClaimIds": []
}
```

`pr_outreach_agent`:
```json
{
  "claimId": "pr_outreach_agent.angle_001",
  "atomicClaim": "Pitching the 'open-source product analytics replaces $50K/yr enterprise stack' angle to TechCrunch, The Information, and InfoWorld will generate 2+ tier-1 media placements within 60 days based on the trending 'open-source enterprise' narrative",
  "weight": 4,
  "confidence": 0.45,
  "incompatibleWithClaimIds": []
}
```

**Tier 4-5 — Research and Observer agents**

These agents emit `executionBlocked: true` and their claims carry lower default weights (3-5) since they are intelligence-only.

`podcast_agent`:
```json
{
  "claimId": "podcast_agent.topic_001",
  "atomicClaim": "A 6-episode interview series with PostHog power users (engineering leads at Supabase, ElevenLabs, Hasura) will generate 500+ downloads per episode within 90 days of launch based on comparable DevTools podcast performance",
  "weight": 4,
  "confidence": 0.5,
  "incompatibleWithClaimIds": ["content_strategy_agent.create_001"]
}
```

`conversion_agent`:
```json
{
  "claimId": "conversion_agent.cta_001",
  "atomicClaim": "Changing the pricing page CTA from 'Talk to sales' to 'Start free — no credit card' will increase self-serve signups by 15% based on A/B test data from comparable PLG SaaS companies",
  "weight": 8,
  "confidence": 0.6,
  "incompatibleWithClaimIds": []
}
```

#### Validation rules for `/gtm-audit` synthesis

When `/gtm-audit` collects recommendations for MaxSAT synthesis, it validates each recommendation:

1. **Required fields check.** `claimId`, `atomicClaim`, `weight`, and `confidence` must all be present. Recommendations missing any field are logged as warnings and excluded from synthesis.
2. **Falsifiability check.** `atomicClaim` must contain at least one number (metric, percentage, dollar amount, count, or timeframe). Claims without numbers are rejected.
3. **Confidence floor.** Claims with `confidence < 0.3` are excluded — they add noise to the synthesis.
4. **Weight bounds.** `weight` must be 1-10. Values outside this range are clamped.
5. **Claim ID uniqueness.** Duplicate `claimId` values within a session cause the second occurrence to be rejected.
6. **Incompatibility symmetry check.** If claim A lists claim B as incompatible, and B exists but doesn't list A, the synthesis engine adds the reverse edge automatically (logs a warning).

## 5. Per-agent schemas

> Notation: `Input → Output`. All inputs extend `BaseAgentInput`, all outputs extend `BaseAgentOutput`. Optional fields marked `?`.

---

### 5.1 `analytics_agent` — Tier 1

Aggregates GA4/Mixpanel/Segment data, runs attribution rollups, surfaces top channels and conversion goals.

```ts
Input {
  dateRange?: { start: string; end: string };  // ISO-8601
  sources?: AnalyticsSource[];                 // 'ga4' | 'mixpanel' | 'segment'
  attributionModels?: AttributionModel[];      // 'first_touch' | 'last_touch' | 'linear' | 'time_decay' | 'position_based'
}

Output {
  summary: { totalSessions; totalConversions; conversionRate; topChannels: ChannelMetrics[]; dateRange };
  attribution: { firstTouch; lastTouch; linear: Record<string, number> };
  conversionTracking: { goals: ConversionGoal[]; totalValue: number };
  insights: string[];
  dataSources: string[];
}
```

---

### 5.2 `technical_seo_agent` — Tier 1

Crawls a URL, scores Core Web Vitals + schema, returns prioritized fixes.

```ts
Input {
  websiteUrl: string;               // Required
  includeSubpages?: boolean;
  maxPages?: number;
}

Output {
  coreWebVitals: { LCP, FID, CLS, INP } each with { value: number; rating: Rating };
  performanceScore: number;         // 0-100
  issues: SEOIssue[];               // { severity: Severity; category; message; recommendation; url? }
  schemaValidation: { valid: boolean; types: string[]; errors: string[] };
  recommendations: string[];
}
```

---

### 5.3 `local_seo_agent` — Tier 1

GMB optimization, citation consistency, local-pack ranking analysis.

```ts
Input {
  locations?: string[];
  includeReviews?: boolean;
  checkCitations?: boolean;
}

Output {
  locations: LocationData[];        // Per-location NAP + review scores
  citations: { total; consistent; inconsistencies: CitationInconsistency[] };
  recommendations: LocalSEORecommendation[];   // type: 'update' | 'add' | 'fix'
  overallScore: number;             // 0-100
}
```

---

### 5.4 `seo_keyword_agent` — Tier 2

Keyword research + on-page suggestions for a single target keyword.

```ts
Input {
  targetKeyword: string;            // Required
  websiteUrl: string;
  contentUrl?: string;
  competitors?: string[];
}

Output {
  keywordAnalysis: {
    targetKeyword; searchVolume; difficulty; cpc; trend: Trend;
    relatedKeywords: KeywordMetrics[];
  };
  onPageSuggestions: OnPageSuggestion[];      // type: 'title'|'meta_description'|'h1'|'content'|'url'
  internalLinking: InternalLinkSuggestion[];
  competitorAnalysis: CompetitorAnalysis[];
  recommendations: SEORecommendation[];        // type: 'content'|'technical'|'link'
  overallScore: number;
}
```

---

### 5.5 `content_strategy_agent` — Tier 2

Editorial calendar, content gaps, repurposing plays.

```ts
Input {
  topic: string;                    // Required
  contentType?: 'blog' | 'whitepaper' | 'case_study' | 'infographic';
  targetPersona?: string;
  targetKeywords?: string[];
  existingContentIds?: string[];
}

Output {
  contentPlan: {
    topic; contentType; targetKeywords; targetPersona; estimatedWordCount;
    outline: { section; keyPoints: string[] }[];
  };
  repurposingOpportunities: RepurposingOpportunity[];
  contentGaps: ContentGap[];
  recommendations: ContentRecommendation[];   // type: 'create' | 'update' | 'repurpose' | 'archive'
}
```

---

### 5.6 `email_automation_agent` — Tier 2

Campaign drafts + segmentation + automation sequences.

```ts
Input {
  campaignType?: 'newsletter' | 'drip' | 'promotional' | 'transactional';
  targetAudience?: string;
  goal?: string;
  existingSegments?: string[];
  contentTheme?: string;
}

Output {
  campaignSuggestion: {
    type; subject; preheader;
    content: { sections: { type: 'hero'|'text'|'cta'|'product'|'social'; content: string }[] };
    sendTime: { recommended; reason };
  };
  segmentation: AudienceSegment[];
  automationSequence?: AutomationStep[];
  recommendations: EmailRecommendation[];      // type: 'subject_line' | 'timing' | 'segment' | 'content'
}
```

---

### 5.7 `social_scheduler_agent` — Tier 2

Multi-platform post calendar with engagement insights.

```ts
Input {
  platforms?: ('facebook'|'instagram'|'twitter'|'linkedin'|'tiktok')[];
  contentTheme?: string;
  schedulePeriod?: number;          // Days
  postFrequency?: 'low' | 'medium' | 'high';
}

Output {
  postSuggestions: SocialPostSuggestion[];     // platform + content + scheduledTime + reasoning
  engagementInsights: {
    bestTimes: Record<string, string[]>;
    topPerformingContent: TopPerformingContent[];
    audienceActivity: Record<string, number>;
  };
  contentCalendar: ContentCalendarEntry[];
  recommendations: SocialRecommendation[];     // type: 'timing' | 'content' | 'hashtag' | 'engagement'
}
```

---

### 5.8 `video_content_agent` — Tier 2

Video script + metadata + captions + optimization.

```ts
Input {
  contentBrief?: string;
  videoType?: 'tutorial' | 'promotional' | 'testimonial' | 'explainer' | 'vlog';
  targetLength?: number;            // Minutes
  platform?: 'youtube' | 'tiktok' | 'instagram' | 'linkedin';
  existingVideoUrl?: string;
}

Output {
  scriptSuggestion: {
    title; hook;
    sections: { timestamp; content; visualCue? }[];
    callToAction; estimatedDuration;
  };
  metadata: { title; description; tags: string[]; thumbnail; category };
  captions?: { format: 'srt' | 'vtt'; content: string };
  optimization: { aspect: 'seo'|'engagement'|'accessibility'; suggested; impact: 'high'|'medium'|'low' }[];
}
```

---

### 5.9 `backlink_builder_agent` — Tier 3

Link prospecting + outreach drafts.

```ts
Input {
  targetKeywords?: string[];
  competitorDomains?: string[];
  outreachType?: 'guest_post' | 'broken_link' | 'resource_page' | 'skyscraper' | 'all';
  targetDomainAuthority?: number;
  existingBacklinks?: string[];
}

Output {
  outreachCampaign: {
    targetSites: BacklinkTargetSite[];     // domain, DA, contactEmail, relevanceScore, outreachType
    emailDrafts: OutreachEmailDraft[];     // includes followUpSequence: { day, subject, body }[]
  };
  guestPostOpportunities: GuestPostOpportunity[];
  brokenLinkOpportunities: BrokenLinkOpportunity[];
  recommendations: BacklinkRecommendation[];  // type: 'strategy' | 'prioritization' | 'template'
}
```

---

### 5.10 `pr_outreach_agent` — Tier 3

Press release + journalist pitches + media kit.

```ts
Input {
  newsType?: 'product_launch' | 'company_news' | 'partnership' | 'funding' | 'executive' | 'event';
  targetOutlets?: string[];
  targetBeats?: string[];
  embargo?: { date; time; timezone };
  keyMessages?: string[];
  quotes?: { speaker; title; quote }[];
}

Output {
  pressRelease: {
    headline; subheadline?; dateline;
    body: { paragraph; type: 'lead'|'quote'|'detail'|'boilerplate' }[];
    mediaContacts: MediaContact[];
  };
  journalistPitches: JournalistPitch[];
  mediaKit: { factSheet; executiveBios; keyMessages; suggestedImages };
  recommendations: PRRecommendation[];   // type: 'timing' | 'angle' | 'outlet' | 'follow_up'
}
```

---

### 5.11 `ad_optimizer_agent` — Tier 3

Cross-platform paid creative + targeting + budget recs (Meta, LinkedIn, TikTok, display).

```ts
Input {
  platforms?: ('meta' | 'linkedin' | 'display' | 'tiktok')[];
  campaignType?: 'awareness' | 'consideration' | 'conversion';
  currentBudget?: { total: number; allocation: Record<string, number> };
  targetAudience?: string;
  existingCampaigns?: string[];
}

Output {
  campaignSuggestions: {
    platform; campaignType;
    creative: { headline; primaryText; description?; ctaButton; mediaType: 'image'|'video'|'carousel'; mediaSuggestion };
    targeting: { audiences; demographics; interests; lookalikes? };
    budget: { dailyBudget; totalBudget; bidStrategy: 'lowest_cost'|'cost_cap'|'bid_cap'; bidAmount? };
  }[];
  splitTestSuggestions: { testType: 'creative'|'audience'|'placement'|'budget'; variants; expectedLift; duration }[];
  budgetReallocation: { currentAllocation; suggestedAllocation; reasoning; expectedImpact };
  recommendations: AdRecommendation[];   // type: 'creative' | 'targeting' | 'budget' | 'timing'
}
```

---

### 5.12 `ppc_agent` — Tier 3

Google/Microsoft Ads campaign architecture: keywords, bids, RSAs, retargeting.

```ts
Input {
  platforms?: ('google_ads' | 'microsoft_ads')[];
  campaignTypes?: ('search' | 'display' | 'shopping' | 'performance_max')[];
  targetKeywords?: string[];
  currentBudget?: { total; allocation };
  targetRoas?: number;
  existingCampaigns?: string[];
}

Output {
  searchCampaigns: {
    campaignName;
    adGroups: {
      name;
      keywords: { keyword; matchType: 'exact'|'phrase'|'broad'; suggestedBid; expectedCpc; expectedConversions }[];
      ads: { headline1; headline2; headline3?; description1; description2?; finalUrl; path1?; path2? }[];
    }[];
    budget: { dailyBudget; bidStrategy: 'manual_cpc'|'maximize_clicks'|'maximize_conversions'|'target_roas'; targetRoas? };
  }[];
  retargetingCampaigns: {
    audienceType: 'site_visitors'|'cart_abandoners'|'past_converters'|'similar_audiences';
    duration; ads: RetargetingAd[]; bidModifier;
  }[];
  bidAdjustments: { dimension: 'device'|'location'|'time'|'audience'; current; suggested; reason; expectedImpact }[];
  recommendations: PPCRecommendation[];   // type: 'keyword' | 'bid' | 'budget' | 'negative_keyword'
}
```

---

### 5.13 `influencer_connect_agent` — Tier 3

Influencer matching + outreach + campaign structure + contract terms.

```ts
Input {
  targetPlatforms?: ('instagram' | 'tiktok' | 'youtube' | 'twitter')[];
  targetNiches?: string[];
  minFollowers?: number;
  maxFollowers?: number;
  minEngagementRate?: number;
  budgetRange?: { min; max };
  campaignObjectives?: string[];
  targetDemographics?: { ageRange?; gender?; location? };
}

Output {
  influencerCandidates: {
    profile: { name; handle; platform; followers; engagementRate; niche };
    fitScore;       // 0-100
    estimatedCost: { post; story; video? };
    audienceMatch: { demographicFit; interestFit; locationFit };
    previousBrands?;
  }[];
  outreachDrafts: InfluencerOutreachDraft[];
  campaignStructure: {
    objectives;
    contentTypes: { type: 'post'|'story'|'reel'|'video'|'live'; quantity; guidelines }[];
    timeline; estimatedBudget;
  };
  contractTerms: { deliverables; exclusivity; usageRights; paymentTerms; disclosureRequirements };
  recommendations: InfluencerRecommendation[];
}
```

---

### 5.14 `podcast_agent` — Tier 4 (Research-only)

```ts
Input {
  podcastName?: string;
  targetAudience?: string;
  existingTopics?: string[];
  preferredFormats?: ('solo' | 'interview' | 'panel' | 'q_and_a')[];
  episodeCount?: number;
  industryVertical?: string;
}

Output {
  episodePlan: { series: PodcastEpisode[]; contentCalendar: PodcastCalendarEntry[] };
  guestResearch: PodcastGuestResearch[];
  topicResearch: PodcastTopicResearch[];
  recommendations: PodcastRecommendation[];
  executionBlocked: true;     // REQUIRED for Tier 4
}
```

---

### 5.15 `conversion_agent` — Tier 4 (Research-only)

```ts
Input {
  websiteUrl?: string;
  funnelStages?: string[];
  targetPages?: string[];
  existingTestIds?: string[];
  industryBenchmark?: number;
}

Output {
  conversionAnalysis: {
    currentRate; benchmark;
    funnelDropoffs: { stage; dropoffRate; hypothesis }[];
    topBarriers: { barrier; impact: 'high'|'medium'|'low'; evidence }[];
  };
  abTestInsights: { testName; variants; winner; confidence; recommendation }[];
  uxRecommendations: { page; issue; evidence: { type: 'heatmap'|'recording'|'survey'|'analytics'; finding }; suggestion; expectedImpact; effort }[];
  heatmapInsights: { page; type: 'click'|'scroll'|'movement'; findings; actionItems }[];
  recommendations: ConversionRecommendation[];   // type: 'copy'|'layout'|'form'|'cta'|'flow'
  executionBlocked: true;     // REQUIRED for Tier 4
}
```

---

### 5.16 `mobile_marketing_agent` — Tier 5 (Observer)

SMS/MMS compliance monitoring (TCPA, CTIA).

```ts
Input {
  campaigns?: { campaignId; name }[];
  monitoringPeriod?: number;        // Days to look back
  includeOptOutDetails?: boolean;
  checkCarrierStatus?: boolean;
  consentExpiryThreshold?: number;
}

Output {
  complianceStatus: {
    overall: 'compliant'|'warning'|'violation';
    tcpaCompliance: { status; issues };
    ctiaCompliance: { status; issues };
    consentTracking: { totalSubscribers; validConsent; expiredConsent; pendingReconfirmation };
  };
  alerts: {
    severity: 'critical'|'warning'|'info';
    type: 'opt_out'|'complaint'|'consent_expiry'|'rate_limit'|'carrier_block';
    message; affectedRecords; requiredAction; deadline?;
  }[];
  optOutTracking: { recentOptOuts; optOutRate; trend: 'increasing'|'stable'|'decreasing' };
  recommendations: { type; priority: 'critical'|'high'|'medium'|'low'; suggestion; reason }[];
  executionBlocked: true;     // REQUIRED for Tier 5
  alertsOnly: true;           // REQUIRED for Tier 5 only
}
```

## 6. Framework agent schemas (plugin additions)

These two agents are GTMVP additions on top of the donor 16. Their full schemas live in their respective skills (`competitor-discovery-cot`, `tam-sam-som-horizons`); summarized here for cross-reference.

### 6.1 `competitor_mapper_agent`

```ts
Output {
  competitorSet: {
    domain; name; segment; sizeBand: 'sub-$10M'|'$10-50M'|'$50-250M'|'$250M+';
    crossShopProbability: number;   // 0-1, the disqualifier check
    overlapVector: { audience; problem; pricePoint; channels }[];
    positioningPhrase; primaryAdvantage; primaryWeakness;
  }[];
  rejectedCandidates: { domain; reason: 'mega_corp'|'wrong_icp'|'different_problem'|'different_price' }[];
  whitespaceGaps: { gap; evidence; viableFor: string[] }[];
  recommendations: Recommendation[];
}
```

### 6.2 `brand_strategist_agent`

```ts
Output {
  market: { tam; sam; som; dynamics; macroTrends };
  niche: { microNiche; oceanScore: 'red'|'pink'|'blue'; competitorDensity };
  productServices: { pricingStrategy; pmfSignals; expansionGaps };
  strategicOpportunities: {
    quickWins: Opportunity[];          // 0-3 months
    mediumPlays: Opportunity[];        // 3-12 months
    longBets: Opportunity[];           // 12+ months
  };
  customerJourney: {
    awareness; consideration; decision; retention;
    frictionPoints: { stage; friction; severity }[];
  };
  brandMessaging: {
    emotionalAppeal; rationalAppeal; audienceSophistication: 1|2|3|4|5;
  };
}
```

## 7. Channel taxonomy reference

The `data/channel-taxonomy.json` file in this plugin defines 28 micro-channels. When an agent's output references a channel, use the canonical `agent_id` slug from that file (e.g. `agent_seo_onpage_001`, not freeform "on-page SEO"). This makes downstream channel-mix analysis joinable across agent runs.

## 8. Solver Conventions

Several agents (`/channel-score`, `/positioning-pass`, `/competitor-map`, `swot-analysis`, `porters-five-forces`, `tam-sam-som-horizons`) invoke the `solver-z3` MCP server for provably-optimal recommendations under explicit constraints. Every solver-using agent MUST follow these conventions. Detailed Python z3 templates live in the `solver-patterns` skill — this section codifies the runtime rules.

### 9.1 Fresh-model pattern

Every solver-backed agent begins with `mcp__solver-z3__clear_model` and ends with `mcp__solver-z3__clear_model`, with `add_item` + `solve_model` calls in between. Skip the trailing `clear_model` only when the same agent is mid-conversation re-solving incrementally for what-if analysis.

```
clear_model → add_item(0, "from z3 import *; from mcp_solver.z3 import export_solution") →
  add_item(1, brand_data) → add_item(2, variables) → add_item(3, constraints) →
  add_item(4, objective) → add_item(5, export_solution_call) →
  solve_model(timeout=10000) → clear_model
```

### 9.2 No solver in parallel sub-agents (CRITICAL)

The `solver-z3` MCP server holds shared session state. If two parallel `Task` sub-agents both invoke solver tools simultaneously, their `add_item` calls interleave and produce a corrupted model that may nonetheless return a clean number. This is the #1 silent-bug risk.

**Rules:**
- `/gtm-audit` and any future orchestrator must serialize solver-using stages. Two solver agents cannot run inside the same `Task` parallel block.
- Prefer placing solver invocation in the **synthesis stage** (final, sequential) rather than inside parallel research sub-agents.
- If a sub-agent absolutely needs the solver, the parent must dispatch sub-agents sequentially for those tasks — explicit `Task A → wait → Task B → wait`.

### 9.3 Labeling convention for UNSAT explainability

Every `assert_and_track` call uses a lowercase snake_case label that reads as English when narrated to the user. Labels appear in the unsat core when constraints are infeasible — that core is what the agent translates into "your constraints are too tight, try relaxing X" guidance.

Required label format:
- `budget_cap` — single global constraint
- `max_concentration_paid_search` — per-category constraint
- `dep_<child_id>_needs_<parent_id>` — dependency constraints
- `min_compounding` — categorical floor constraints
- `team_capacity` — operator-capacity constraint

Never use `c1`, `c2`, `assertion_0` — these surface as opaque IDs to the user.

### 9.4 Timeout policy

Default `solve_model` timeout = **10 seconds** for optimization problems, **5 seconds** for pure SAT feasibility checks, **15 seconds** for scheduling problems with dependencies.

Treat solver timeout as **functional infeasibility** — not as a system error. The agent surfaces it as: "Constraints could not be satisfied within the time budget; the active hard constraints are [list]. Consider relaxing one of them."

### 9.5 UNSAT explanation pattern

When `solve_model` returns UNSAT or times out, the agent MUST:

1. Extract the minimal unsat core via `solver.unsat_core()` (Python z3 API — surfaces in `export_solution` output).
2. Translate each label tag to a prose sentence using a lookup table the agent maintains for its constraint set.
3. Suggest at most 2 relaxations, ordered by least-disruptive. Example: "Your `min_compounding ≥ 1` and `team_capacity ≤ 3` together leave no room for a feasible allocation with current `budget_cap = $30K`. Consider either raising budget to $45K (unlocks SEO + community + 1 paid channel) or dropping the compounding floor (allows all-paid mix for fast feedback)."
4. Never present raw assertion IDs or Z3 expressions to the user.

### 9.6 Piecewise-linear approximation policy

Z3 has no native `sqrt` or `log`. For diminishing-returns objectives, use **5 breakpoints with logarithmic spacing** between each option's minimum viable spend and maximum useful spend. The breakpoint computation lives in `solver-patterns` §1 as the `pwl_sqrt` helper — use it directly, do not re-derive breakpoint counts or spacing.

Why this matters: if Claude authors 3-breakpoint approximations in one run and 7-breakpoint in another, the same brand context produces different "optimal" allocations across sessions. The 5-breakpoint policy is the reproducibility guarantee.

### 9.7 Export contract

Every solver run ends with exactly one `export_solution(...)` call:

- Satisfiable: `export_solution(solver=opt, variables=variables, objective=opt.objectives()[0])`
- Infeasible: `export_solution(satisfiable=False, variables=variables)`
- Timeout: same as infeasible — `export_solution(satisfiable=False, variables=variables)` + an extra `print("Timeout after 10s")` so the orchestrator can distinguish.

The `variables` dictionary keys are stable IDs derived from the brand's taxonomy slugs (e.g. `spend_agent_seo_onpage_001`). Free-form names break the eval harness's stability check.

### 9.8 Output addition to BaseAgentOutput

Solver-using agents extend their existing output schema with a `solverResult` block:

```ts
interface SolverResult {
  status: 'optimal' | 'feasible' | 'infeasible' | 'timeout';
  values: Record<string, number | boolean>;       // variable_name → assigned value
  objective?: number;                              // present when status is 'optimal' | 'feasible'
  activeConstraints: string[];                     // labels of constraints binding at the optimum
  unsatCore?: string[];                            // labels that conflict; present when status is 'infeasible'
  relaxationSuggestions?: string[];                // English prose suggestions; present when 'infeasible' or 'timeout'
  solveTimeMs: number;
  templateUsed: 'linear-allocation' | 'knapsack' | 'max-min-distance' | 'set-cover' | 'scheduling-with-deps';
}
```

This block is appended to the agent's existing output, never replacing existing fields. Downstream agents that don't understand solver results continue to read the agent's traditional ranked-list output.

## 9. Versioning rules

- Every agent prompt has its own SemVer (`version` field on output).
- Bumping a schema field is a **MAJOR** version bump for the affected agent.
- Adding an optional field is **MINOR**.
- Tightening a description is **PATCH**.
- The plugin `version` in `.claude-plugin/plugin.json` is independent — it tracks the bundle, not individual agents.
