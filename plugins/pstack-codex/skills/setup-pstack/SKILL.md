---
name: setup-pstack
description: Configure Codex models and reasoning effort for pstack roles. Use for $setup-pstack, configuring pstack models, or changing a pstack delegation panel.
---

# Setup pstack

Create or update `~/.codex/pstack-models.json`. This is a pstack-owned override
file, not Codex's main configuration. Skills fall back to the parent model when
the file or a role is absent.

## Steps

1. Read `../poteto-mode/references/codex-runtime.md`.
2. Inspect the current Codex surface's declared collaboration-model metadata.
   Use only model and reasoning-effort combinations that metadata confirms.
   When model metadata is unavailable, offer `inherit-parent`; never guess a
   slug.
3. Read the existing file when present. Validate that it is JSON with a top-level
   `roles` object. Preserve valid roles the user did not ask to change.
4. Show the current role map. Mark unavailable configured values. Ask one concise
   question only if the user has not said which roles to change.
5. Write the complete file atomically. Every role value is either
   `"inherit-parent"`, one model object, or a list of model objects. A model
   object has exactly `model` and `reasoning_effort`.
6. Read the file back, parse it, and verify every explicit value against the
   current host metadata.
7. Report the roles changed and say the next pstack invocation will use them.

## Role keys

Use these stable keys so all skills resolve the same configuration:

```text
feature
refactoring
bug-fix
perf-issue
hillclimb
judgment-prose
hardest-tasks
how-explorer
how-explainer
how-critics
why-investigators
why-synthesizer
reflect-tooling
reflect-judgment
reflect-divergent
reflect-synthesizer
arena-runners
arena-cross-judge
swarm-workers
architect-runners
interrogate-reviewers
```

Panel roles contain lists. Their list length is the fan-out count. Single-model
roles contain one object or `"inherit-parent"`.

## Example

```json
{
  "roles": {
    "bug-fix": {"model": "gpt-5.6-sol", "reasoning_effort": "max"},
    "swarm-workers": {"model": "gpt-5.6-luna", "reasoning_effort": "high"},
    "interrogate-reviewers": [
      {"model": "gpt-5.6-sol", "reasoning_effort": "max"},
      {"model": "gpt-5.6-terra", "reasoning_effort": "xhigh"},
      {"model": "gpt-5.6-luna", "reasoning_effort": "high"},
      {"model": "gpt-5.5", "reasoning_effort": "xhigh"}
    ]
  }
}
```

Do not edit `~/.codex/config.toml` unless the user separately asks to change
Codex itself.
