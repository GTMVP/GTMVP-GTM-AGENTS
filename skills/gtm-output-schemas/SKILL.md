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
