# GTMVP-GTM-AGENTS

A Claude Code plugin packaging the GTM intelligence stack used inside [GTMVP](https://gtmvp.ai) — 18 specialist agents, 6 framework skills, 5 orchestration slash commands, and a 28-channel taxonomy — for use in any Claude Code session.

> **v1.0.0** — All surfaces shipped. Validated by `scripts/validate-plugin.mjs`.

## What's in the box

| Surface | Count | Files |
|---|---|---|
| Subagents | 18 | `agents/*.md` |
| Skills | 6 | `skills/*/SKILL.md` |
| Slash commands | 5 | `commands/*.md` |
| Reference data | 1 | `data/channel-taxonomy.json` (28 channels, 9 macro categories) |
| Scripts | 2 | `scripts/{port-channel-taxonomy,validate-plugin}.mjs` |

## The 18 agents

Organized across 5 trust tiers:

**Tier 1 — Auto-Pilot** (executes autonomously)
- `analytics-agent` — GA4/Mixpanel attribution rollups
- `technical-seo-agent` — Core Web Vitals, schema, crawl health
- `local-seo-agent` — GMB, citations, local pack

**Tier 2 — Co-Pilot** (drafts, queues for approval)
- `seo-keyword-agent` — keyword research + on-page optimization
- `content-strategy-agent` — content plan, gaps, repurposing
- `email-automation-agent` — campaigns + segmentation + sequences
- `social-scheduler-agent` — multi-platform organic post calendar
- `video-content-agent` — script + metadata + captions

**Tier 3 — Assistant** (drafts, never sends without approval)
- `backlink-builder-agent` — link prospecting + outreach
- `pr-outreach-agent` — press release + journalist pitches
- `ad-optimizer-agent` — Meta/LinkedIn/TikTok/display campaigns
- `ppc-agent` — Google/Microsoft search + retargeting
- `influencer-connect-agent` — creator sourcing + outreach

**Tier 4 — Research** (intelligence only, `executionBlocked: true`)
- `podcast-agent` — episode + guest + topic research
- `conversion-agent` — CRO diagnosis + UX recs
- `competitor-mapper-agent` — cross-shop disqualifier method
- `brand-strategist-agent` — TAM/SAM/SOM + 6-dim brand analysis

**Tier 5 — Observer** (alerts only, `alertsOnly: true`)
- `mobile-marketing-agent` — TCPA/CTIA SMS compliance monitoring

## The 6 framework skills

| Skill | Purpose |
|---|---|
| `gtm-output-schemas` | Canonical I/O contracts for all 18 agents (cite this from every agent) |
| `competitor-discovery-cot` | 4-step chain-of-thought with cross-shop disqualifier |
| `porters-five-forces` | Scored five-forces with strategic implications |
| `swot-analysis` | Strategy-grade SWOT with `stopDoing` priorities |
| `tam-sam-som-horizons` | 6-dimension brand analysis with quick-win / 3-12mo / 12mo+ horizons |
| `marketing-channel-scoring` | 5-dimension channel scoring against the 28-channel taxonomy |

## The 5 slash commands

| Command | Effect |
|---|---|
| `/gtm-audit [url]` | Full 6-stage audit pipeline — the flagship orchestration |
| `/competitor-map [domain]` | Defensible competitor set with whitespace gaps |
| `/channel-score [url]` | All 28 channels scored, 3-phase rollout plan |
| `/positioning-pass [url]` | 3 sharper positioning options with rationale |
| `/porters-scan [market]` | Five-forces market structure analysis |

## Macro channels covered

SEO · Content Marketing · Social Media · Email · PPC/Paid Ads · PR & Brand · Affiliate · Partnerships · Analytics

Full breakdown — inputs, outputs, KPIs, tactics, dependencies — lives in [`data/channel-taxonomy.json`](./data/channel-taxonomy.json).

## Install

### Local (development)

```powershell
New-Item -ItemType Junction -Path C:\Users\User\.claude\plugins\gtmvp-gtm-agents -Target C:\Users\User\Projects\GTMVP-GTM-AGENTS
```

Verify with `/plugin` in any Claude Code session — `gtmvp-gtm-agents` should appear.

### Remote (private marketplace)

```
/plugin marketplace add github.com/GTMVP/GTMVP-GTM-AGENTS
/plugin install gtmvp-gtm-agents
```

### Validate

```powershell
node C:\Users\User\Projects\GTMVP-GTM-AGENTS\scripts\validate-plugin.mjs
```

Should print `PASS` with manifest, 18 agents, 5 commands, 6 skills, 28 taxonomy agents.

## Usage

Once installed, invoke an agent via the Task tool:

```
Task(subagent_type="competitor-mapper-agent",
     description="Map Acme's competitive set",
     prompt="Acme is a $5M ARR boutique B2B SaaS marketing agency targeting post-PMF founders. Map their direct competitor set, with rejected mega-corp candidates and whitespace gaps.")
```

Or use a slash command:

```
/gtm-audit https://acme.com
/competitor-map acme.com
/channel-score gtmvp.ai
/positioning-pass synap.io
/porters-scan boutique-B2B-SaaS-marketing-agencies-1-10M-ARR
```

## Architecture

### Trust-tier model

Every agent declares a tier (1-5) governing autonomy. Tier 4/5 agents MUST set `executionBlocked: true`; Tier 5 also sets `alertsOnly: true`. The `gtm-output-schemas` skill enforces these flags.

### Schema-first agents

The 16 donor-derived agent schemas come from a TypeScript reference codebase (~1,873 LOC of detailed I/O types). Each agent's system prompt is written *against* the schema — the schema tells the agent exactly what to produce. This keeps outputs joinable across agents and across runs.

### Skills as the deep-knowledge layer

The 5 framework skills (excluding `gtm-output-schemas`, which is the contract layer) carry the deep methodology — chain-of-thought scaffolding, scoring rubrics, decision rules. Agents invoke skills; skills don't invoke agents.

### Channel taxonomy as join key

When any agent references a marketing channel, it cites the canonical `agent_id` slug from `data/channel-taxonomy.json` (e.g., `agent_seo_onpage_001`). This makes downstream channel-mix analysis joinable across runs.

## Origin

Donor material: a private TypeScript reference codebase (`marketing-ai-platform`) that defined 28 marketing micro-channels with structured I/O contracts. The agent prompts here are net-new, written from scratch against those schemas. Two donor service prompts (competitor discovery, brand strategist) were materially folded into the framework skills.

## Related

- [GTMVP_V0](https://github.com/GTMVP/GTMVP_V0) — production audit app where a selective subset will be wired into the deep-audit operator (post-v1.0 work)
- [Steve Kaplan](https://stevekaplan.ai)

## License

MIT
