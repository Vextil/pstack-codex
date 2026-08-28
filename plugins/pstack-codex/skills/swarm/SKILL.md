---
name: swarm
description: "Fan out N parallel workers, drain them, and return one report. Use for $swarm, 'swarm this', or parallel coverage, races, gauntlets, and exploration."
---

# Swarm


> Codex runtime: read [`../poteto-mode/references/codex-runtime.md`](../poteto-mode/references/codex-runtime.md) before delegating, selecting models, waiting, or inspecting task history. Its native Codex contract takes precedence over stale host syntax in an upstream change.

Fan out N parallel Codex subagents. They may cover separate slices, race the same brief, or mix both. The parent waits, aggregates, and returns one report.

## Start

Open a Codex plan with one entry per phase before launching anything.

1. Frame
2. Fan out
3. Aggregate
4. Report

## Phase A: Frame

1. State the done predicate and the artifact or report the swarm must return.
2. Choose the shape. Partition into slices, race N workers on identical briefs, or mix both. For a race or mixed shape, declare `first pass`, `rank all`, or `best-of` before spawning.
3. Set N from the user or derive it from the shape. N is total workers, not the host concurrency limit.
4. Pick the worker model from `swarm-workers` in `~/.codex/pstack-models.json` when present. Otherwise use `gpt-5.6-luna` at `high`. For a model race, name each arm's model up front.
5. Give each worker its own writable output when it writes. Use a worktree, branch, or `/tmp/swarm-<slug>/worker-<n>/`.

## Phase B: Fan out

Call `spawn_agent` for all N workers back-to-back before waiting. Codex subagents share the workspace, so give every writer an isolated worktree or branch and every read-only worker an explicit no-write brief. Include a non-default starting branch in the brief. Use a separate user-visible Codex task only when the user explicitly asks for one.

Every brief stands alone. Include the goal, scope, exact slice or race arm, how to verify, and what to report. Reports use `PASS`, `ISSUES`, or `BLOCKED` with evidence.

If a worker drops out, proceed with N-1 and note it.

## Phase C: Aggregate

Read the terminal results. For coverage, every required slice needs a result. For a race, apply the selection rule declared up front. Use first pass, rank all, or best-of. Do not paste raw worker dumps.

Keep a compact result table, one-line evidenced issues, and explicit gaps or dropouts.

## Phase D: Report

Return one consolidated in-chat report with the table, issue one-liners, gaps or dropouts, and the race rule when used.
