---
name: reflect
description: Review the current Codex task for durable workflow lessons and route approved lessons into concrete skill edits. Use when the user says reflect.
---

# Reflect

Mine the current task for durable lessons, then route them into skill or tooling
changes. Read `../poteto-mode/references/codex-runtime.md` before delegating.

Use this after a complex task landed, a dead end exposed a reusable better path,
or the user corrected the approach. Skip trivial and one-off work.

Unless configured otherwise, all four Reflect roles use `gpt-5.6-sol` at
`xhigh`, matching the native single-worker model policy.

## Process

1. Obtain the current task through Codex task-history tools when available. If
   unavailable, write a compact digest from the active conversation. Do not
   crawl undocumented session files.
2. Spawn three read-only reviewers back-to-back, using the configured
   `reflect-judgment`, `reflect-tooling`, and `reflect-divergent` roles. Use the
   matching templates in `references/`. Give each the task record or digest and
   forbid file writes.
3. Drain the reviewers, then spawn one synthesizer using
   `reflect-synthesizer` and `references/synthesizer.md`. It returns Accepted,
   Rejected, and Backlog lists with evidence.
4. Move any lesson better enforced by a lint, script, metadata flag, or runtime
   check from Accepted to Backlog. Follow the
   `principle-encode-lessons-in-structure` skill.
5. Present the full synthesis and wait for explicit approval before changing a
   skill. Skill changes affect future tasks. Do not auto-apply them.
6. Apply approved trivial edits directly. For substantive edits, new skills, or
   description tuning, invoke `$skill-creator` and follow its validation loop.
7. File backlog items only when an in-scope tracker is available and the user
   has authorized writes there. Otherwise return a ready-to-file item.
8. Validate every touched skill and summarize applied, created, backlogged, and
   rejected items.
