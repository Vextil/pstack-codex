# Codex runtime contract

This is native Codex behavior shared by pstack's delegation-heavy skills. It is
not a translation table for another host. Follow it whenever a pstack workflow
delegates, selects a model, waits, asks a question, or resumes prior work.

## Plans

Use Codex's plan tool for multi-step work. Keep exactly one plan item in
progress, mark completed work promptly, and leave skipped steps visible with a
reason. Do not create a durable Codex goal unless the user explicitly asks for
one.

## Delegation

- Use `spawn_agent` for bounded subtasks that can run independently. Spawn
  siblings back-to-back before waiting so they run concurrently.
- Subagents share the filesystem. Give every writer a separate git worktree or
  a disjoint output path. Read-only reviewers get an explicit no-write brief.
- Use `send_message` for context that belongs to a running subagent and
  `followup_task` only when an idle existing subagent should start another turn.
- Use `wait_agent` to drain results. Prefer one longer wait to busy polling.
- Use a separate user-visible Codex task only when the user explicitly asks for
  a new task. Do not substitute visible tasks for ordinary subagents.
- To make a worker use poteto's full style, tell it to invoke `$poteto-mode` and
  read the selected playbook before acting. To run the comment reviewer, tell a
  read-only worker to invoke `$comment-sicko`.

If multi-agent tools are unavailable, run the lanes sequentially, preserve the
same independent briefs, and disclose the reduced parallelism.

## Model configuration

Read `~/.codex/pstack-models.json` when it exists. Each role is either one model
specification or a list of them:

```json
{
  "roles": {
    "how-explorer": {"model": "gpt-5.6-luna", "reasoning_effort": "high"},
    "interrogate-reviewers": [
      {"model": "gpt-5.6-sol", "reasoning_effort": "max"},
      {"model": "gpt-5.6-terra", "reasoning_effort": "xhigh"},
      {"model": "gpt-5.6-luna", "reasoning_effort": "high"},
      {"model": "gpt-5.5", "reasoning_effort": "xhigh"}
    ]
  }
}
```

Omit `model` and `reasoning_effort` when a role says `"inherit-parent"` or when
the configured value is unavailable. Never invent a model slug. The portable
fallback is the parent model. For a panel, use distinct available Codex models
when possible; otherwise vary reasoning effort and disclose that model
diversity was reduced.

Recommended defaults, only when the current host confirms they are available:

- Fast/mechanical: `gpt-5.6-luna`, `high`.
- Balanced exploration and judgment: `gpt-5.6-terra`, `xhigh`.
- Deep implementation: `gpt-5.6-sol`, `max`.
- Adversarial alternate: `gpt-5.5`, `xhigh`.

## Questions

Ask only for irreversible actions or genuine product and preference choices
that evidence cannot settle. Use structured user input when the current Codex
surface provides it; otherwise ask one concise plain-text question. Never stop
for a question the repository, a probe, or a safe default can answer.

## Waiting and long-running work

- Wait directly for active subagents or explicit user-visible tasks.
- For a requested recurring monitor or follow-up, use a Codex heartbeat
  automation attached to the current task. Keep notification settings out of
  the automation prompt.
- Do not fake recurrence with shell sleep loops. Do not turn a one-time wait
  into a scheduled automation.
- Checkpoint long work in the plan, a decision trail, commits, and pushed
  branches so a new task can resume from durable evidence.

## Task history

Prefer Codex's task-list and task-read tools when available. Scope searches to
the active project and the user's requested time window. If task-history tools
are unavailable, use the current conversation, git state, PRs, decision trails,
and user-provided links. Do not crawl undocumented session-storage directories.

Treat prior task summaries as historical evidence, not current truth. Verify
branches, commits, PRs, tickets, and runtime state before presenting them as
current.

## Files, terminal, browser, and skills

- Search with `rg` or `rg --files`, run commands through the terminal, and edit
  files with `apply_patch` when available.
- Verify CLI/TUI behavior in the terminal. Verify web or Electron behavior with
  the available browser/computer-use capability. If the required driver is not
  installed, say what could not be observed and give a concrete manual check.
- Create or revise Codex skills through `$skill-creator`. Repository skills live
  under `.agents/skills/`; user skills live under `~/.agents/skills/`.
- Invoke installed pstack skills with `$skill-name`, not slash-command shims.
