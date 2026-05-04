---
name: gtm-output-schemas
description: Canonical input/output JSON schemas for the 18 GTM marketing agents in this plugin. Use when an agent needs to know the exact shape of its input parameters or output payload, or when a slash command needs to validate agent results before chaining them. Covers analytics, SEO, content, social, email, video, backlinks, PR, paid ads, PPC, influencers, podcast, conversion, mobile, plus the cross-cutting brand context, trust-tier, and recommendation envelopes.
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

## 8. Versioning rules

- Every agent prompt has its own SemVer (`version` field on output).
- Bumping a schema field is a **MAJOR** version bump for the affected agent.
- Adding an optional field is **MINOR**.
- Tightening a description is **PATCH**.
- The plugin `version` in `.claude-plugin/plugin.json` is independent — it tracks the bundle, not individual agents.
