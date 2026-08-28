# Set up pstack

In this page you install the plugin, optionally pick which models pstack uses,
and run your first task.

## Install the plugin

Add this repository as a Codex marketplace, then install the plugin:

```bash
codex plugin marketplace add Vextil/pstack-codex --ref main
codex plugin add pstack-codex@pstack-codex
```

Start a new Codex task after installation so the plugin skills are loaded.

## Pick your models

Run:

```text
$setup-pstack
```

[`$setup-pstack`](../../skills/setup-pstack/SKILL.md) reads the models and
reasoning efforts exposed by the current Codex surface, shows each pstack role,
and asks what you want to override. It writes
`~/.codex/pstack-models.json`, a pstack-owned configuration file. It does not
edit Codex's main configuration.

You only override what you care about. A role with no entry keeps pstack's
default. To restore a default later, remove that role from the file or run
`$setup-pstack` again.

A role set to `inherit-parent` or `auto` omits model overrides, so its subagent
inherits the parent task model. Both values mean the same thing; neither is a
model slug. Panel roles contain lists, and their length sets the panel size.
`arena-cross-judge` is the exception: its list is a selection pool for one
judge, preferably from a different model family than the parent.

Model configuration is optional. When the current Codex surface does not
expose a configured model, pstack falls back to the parent model instead of
guessing a replacement.

## Add project verification when it earns its place

If the repository has no reliable way to prove real app behavior, run:

```text
$create-verification-skill
```

[`$create-verification-skill`](../../skills/create-verification-skill/SKILL.md)
can generate a project-local `.agents/skills/verify-<app>/` workflow and prove
it once end to end. This is separate from model setup, so you can add it when a
real task needs it. [Verify and ship](./06-verify-and-ship.md#create-a-project-verification-skill)
explains the tradeoff.

## Run your first task

Pick something real but small, and describe it the way you'd describe it to a
colleague:

```text
$poteto-mode add a --json flag to this command. text output stays byte-identical. verify both.
```

Watch the Codex plan. The first item is always "read the Principles section".
The rest are the matched playbook's steps, the Feature playbook for this
prompt. If `$poteto-mode` skips a step, it leaves the step visible with
`skip: <reason>`, so you can see what it chose not to do.

From here you can type normal follow-ups. `$poteto-mode` stays active for the
task until you opt out or clearly start a new task.

Next: [Route work through `$poteto-mode`](./02-poteto-mode.md).
