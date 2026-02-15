# Agent Skills

This directory contains skill definitions for Copilot. Each `.md` file describes a domain-specific skill — the rules, data formats, edge cases, and best practices for working in that area.

## Available Skills

| Skill                  | File                        | Description                                                   |
| ---------------------- | --------------------------- | ------------------------------------------------------------- |
| Fetch Garmin Data      | `fetch-garmin-data.md`      | Sync 30+ data types via `scripts/sync.py` CLI                 |
| Analyze Health Data    | `analyze-health-data.md`    | 4-phase analysis workflow (Context → Data → Clarify → Report) |
| Write Summary          | `write-summary.md`          | Hebrew report format, vitalis-meta block, writing rules       |
| Personal Profile       | `personal-profile.md`       | Profile fields, interactive completion, personalisation       |
| Data Layout            | `data-layout.md`            | Folder structure, actual JSON formats, device compatibility   |
| Agent Memory           | `agent-memory.md`           | Summary-based memory protocol, comparison arrows, baselines   |
| Health Recommendations | `health-recommendations.md` | Hebrew recommendations with `[heb/eng]` tags, priority 1-5    |
| Garmin CSV Analysis    | `garmin-csv-analysis.md`    | Parsing rules for manual CSV uploads                          |
| Garmin Data Sync       | `garmin-data-sync.md`       | ~~DEPRECATED~~ — see `fetch-garmin-data.md`                   |

## How Skills Work

When working on domain-specific features, reference the relevant skill file to understand the rules and conventions. Skills are NOT code — they are instructions that guide implementation.

## Analysis Workflow Quick Reference

1. **Phase 1 — Context**: Read latest `data/summaries/*.md` for memory continuity
2. **Phase 2 — Data**: Read `data/profile.yaml` + run `scripts/extract_metrics.py` + read sync files
3. **Phase 3 — Clarify**: Ask user questions in Hebrew for missing profile info or anomalies
4. **Phase 4 — Report**: Generate Hebrew report with English technical terms, write summary
