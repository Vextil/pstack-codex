---
name: recall
description: Reconstruct recent working context from Codex task history, live repository state, and shared records. Use for recall my work on X, catch me up, what have I been working on, or where did I leave off.
---

# Recall

Rebuild the user's recent working context and return a tight current-state
brief. Read `../poteto-mode/references/codex-runtime.md` before inspecting task
history or delegating.

1. Route one specific task takeover to poteto-mode's session-pickup playbook.
   Route habit mining to `$automate-me`. If the user already supplied paths,
   branch, and current state, use that capsule instead of mining history.
2. Pin the scope: topic, active project, and time window. Default “recent” to
   seven days. State the scope; never silently shrink “all” to a recent window.
3. Use Codex task-list and task-read tools when available. For more than two
   likely tasks, fan out read-only subagents over disjoint result slices. Each
   returns topic, goal, decisions, open threads, corrections, and artifacts,
   identifying the source task. Keep raw task output out of the parent context.
4. When the topic names a feature, file, subsystem, or bug, run `$why` in
   parallel over the shared record. Ask for current state, prior attempts that
   failed, and remaining reports. Unavailable connectors are explicit gaps.
5. Verify every surfaced branch, commit, PR, and ticket against live state with
   `git`, `gh`, and available connectors. Task summaries are history, not truth.
6. Sanitize private context before any public output and write through `$unslop`.

If task-history tools are unavailable, use the current conversation, decision
trails, git/PR state, and links the user provided. Do not crawl undocumented
Codex storage directories.

## Output contract

- **Capsule.** At most five bullets describing the work and overall state.
- **Threads.** One line each with exactly one status tag: `[merged #N]`,
  `[open PR #N]`, `[in flight <branch>]`, `[verified, uncommitted]`,
  `[reverted #N]`, or `[planned, not started]`.
- **Problems.** At most five recurring problems, including reverted fixes.
- **Next move.** The single most useful concrete action.
