# Make it yours

poteto-mode is one person's style. The machinery underneath—playbooks,
routing, and model roles—works just as well wearing yours. This page covers
generating a personal mode, capturing lessons from a task, authoring a focused
skill, and testing a skill change before you trust it.

## Generate your own mode with `$automate-me`

```text
$automate-me
```

You don't have to describe your style from scratch. When Codex task-history
tools are available, [`$automate-me`](../../skills/automate-me/SKILL.md)
samples recent tasks from the active project and looks for repeated preferences
in replies, delegation, verification, code, prose, and Git process. It never
crawls undocumented session-storage directories. If task history is
unavailable, it uses the current task and evidence you provide.

The skill requires more than one example before treating a behavior as a rule,
then asks which patterns are really you. It invokes Codex's built-in
`$skill-creator` to draft either a repository skill under
`.agents/skills/<your-name>-mode/` or a user skill under
`~/.agents/skills/<your-name>-mode/`. You choose the scope when it is not
already clear. It runs the draft through [`$unslop`](../../skills/unslop/SKILL.md)
and validates it. Committing or opening a PR happens only when you ask.

Run it again whenever your habits drift:

```text
$automate-me update my mode skill with everything since its last edit
```

Update mode keeps rules the newer evidence has not contradicted and adds
sections only for genuinely new patterns.

## Capture a task's lessons with `$reflect`

Right after work that taught you something, run:

```text
$reflect that took way too long. capture what we learned so the next run doesn't repeat it.
```

[`$reflect`](../../skills/reflect/SKILL.md) reviews the current task evidence
from several angles, then a synthesizer sorts proposals into `Accepted`,
`Rejected`, and `Backlog`. It waits for your approval before changing a skill.
Approve a proposal only if it would change a future decision. One unusual task
is an anecdote, not a rule.

## Author a focused skill

When you already know the workflow you want to capture:

```text
$poteto-mode write a skill for verifying database migrations in this repo
```

Writing a skill matches the [Authoring or modifying a skill playbook](../../skills/poteto-mode/playbooks/authoring-a-skill.md),
which invokes Codex's `$skill-creator`, validates the package and links, and
uses the Opening a PR playbook only when repository delivery is part of your
request. Agent-facing prose has a higher bar than human prose because an
unhelpful sentence becomes an instruction a future agent follows.

A skill that drives your app and proves behavior is a verification skill, so
use [`$create-verification-skill`](../../skills/create-verification-skill/SKILL.md)
and [`$maintain-verification-skill`](../../skills/maintain-verification-skill/SKILL.md)
instead. [Verify and ship](./06-verify-and-ship.md#create-a-project-verification-skill)
covers both.

## Write docs to a standard with `$technical-writing`

For docs, RFCs, readmes, PR descriptions, and commit messages:

```text
$technical-writing review the readme changes
```

[`$technical-writing`](../../skills/technical-writing/SKILL.md) selects the
document's mode—tutorial, how-to, reference, or explanation—then works sentence
by sentence toward prose a tired engineer understands on the first read.

## Test a skill change blind

A skill edit affects future tasks, so test it like an experiment:

```text
$poteto-mode run the eval playbook on this skill change. same task for both variants, candidates stay blind.
```

The [Eval playbook](../../skills/poteto-mode/playbooks/eval.md) prevents the
observer effect. Candidate agents get the same organic-looking task in
sanitized directories, never each other's existence. One judge scores neutral
labels, and chain-following is graded from task evidence rather than candidate
self-report.

Read every output yourself before accepting the verdict. If you disagree with
the judge, suspect the rubric before you suspect your judgment.

**Pitfall:** don't edit a skill mid-task because it is misbehaving. Fix it as a
separate change and keep the original task moving. A skill edit tangled into
feature work is invisible to review and difficult to evaluate.

Next: [Recipes and pitfalls](./10-recipes-and-pitfalls.md).
