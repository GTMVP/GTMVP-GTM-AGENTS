# GTMVP-GTM-AGENTS

A Claude Code plugin packaging the GTM intelligence stack used inside [GTMVP](https://gtmvp.ai) — 18 specialist agents, 6 strategic frameworks, and a 28-channel taxonomy — for use in any Claude Code session.

> **Status:** v0.1.0 — foundations only (manifest, channel taxonomy, output schemas). Agents and skills are being added in subsequent passes.

## What's in the box

| Surface | Count | Status |
|---|---|---|
| Subagents (`agents/*.md`) | 18 | Pending — v0.2 |
| Skills (`skills/*/SKILL.md`) | 6 | 1 of 6 (gtm-output-schemas) |
| Slash commands (`commands/*.md`) | 5 | Pending — v0.2 |
| Reference data (`data/*.json`) | 1 | Channel taxonomy ported |

## Macro channels covered

SEO · Content Marketing · Social Media · Email · PPC/Paid Ads · PR & Brand · Affiliate · Partnerships · Analytics

The full breakdown — inputs, outputs, KPIs, tactics, dependencies, and reference solutions per channel — lives in [`data/channel-taxonomy.json`](./data/channel-taxonomy.json).

## Install

### Local (development)

```powershell
New-Item -ItemType SymbolicLink -Path C:\Users\User\.claude\plugins\gtmvp-gtm-agents -Target C:\Users\User\Projects\GTMVP-GTM-AGENTS -Force
```

Then in any Claude Code session:

```
/plugin
```

The plugin should appear in the list.

### Remote (private marketplace)

```
/plugin marketplace add github.com/GTMVP/GTMVP-GTM-AGENTS
/plugin install gtmvp-gtm-agents
```

## Usage

Once installed, agents are invokable via the Task tool's `subagent_type` parameter:

```
Task(subagent_type="competitor-mapper", description="Map Acme's competitive set", prompt="...")
```

Slash commands compose multiple agents into pipelines:

```
/gtm-audit https://acme.com
/competitor-map acme.com
/porters-scan saas-payroll
```

## Origin

Donor material: a private TypeScript reference codebase (`marketing-ai-platform`) that defined 28 marketing micro-channels with structured I/O contracts. The agent prompts in this plugin are written from scratch against those schemas — the schemas tell the agent exactly what to produce.

## Related

- [GTMVP_V0](https://github.com/GTMVP/GTMVP_V0) — the production audit app where a selective subset of these agents is wired into the deep-audit operator
- [Steve Kaplan](https://stevekaplan.ai)

## License

MIT
