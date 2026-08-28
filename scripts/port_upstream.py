#!/usr/bin/env python3
"""Build the native Codex pstack plugin from a Cursor plugins checkout.

The generated plugin is intentionally not a shared Cursor/Claude tree. This
compiler copies upstream pstack, removes Cursor-only metadata, translates host
primitives into Codex-native instructions, applies small semantic overlays, and
fails validation when new host-specific language needs a human decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "pstack-codex"
OVERLAY_ROOT = REPO_ROOT / "port" / "overlays" / "plugin"
CODEX_REVISION = 3

EXCLUDED = {
    "automations/benny": (
        "Cursor event-triggered automation bundle. Codex scheduled-task support "
        "needs a separate product-level design; it is not silently emulated."
    ),
    "skills/grokbot/make-bot-ui": (
        "Requires a Cursor Automations webhook, for which Codex has no portable "
        "public-plugin equivalent."
    ),
}

MODEL_REPLACEMENTS = {
    "claude-fable-5-thinking-max": "gpt-5.6-sol` at `xhigh",
    "gpt-5.6-sol-max": "gpt-5.6-sol` at `xhigh",
    "grok-4.6-fast-xhigh": "gpt-5.6-luna` at `xhigh",
    "claude-opus-5-thinking-xhigh": "gpt-5.6-sol` at `xhigh",
    "composer-2.5-fast": "gpt-5.6-luna` at `xhigh",
}

# Upstream intentionally uses four different model families for independent
# candidates and reviewers. Preserve that behavior instead of collapsing every
# panel slot through the single-worker cost/performance map above.
PANEL_MODEL_REPLACEMENTS = {
    "claude-fable-5-thinking-max": "gpt-5.6-sol` at `xhigh",
    "gpt-5.6-sol-max": "gpt-5.6-terra` at `xhigh",
    "grok-4.6-fast-xhigh": "gpt-5.6-luna` at `xhigh",
    "claude-opus-5-thinking-xhigh": "gpt-5.5` at `xhigh",
    "composer-2.5-fast": "gpt-5.6-luna` at `xhigh",
}

PANEL_MODEL_PATHS = {
    "skills/architect/SKILL.md",
    "skills/arena/SKILL.md",
    "skills/how/SKILL.md",
    "skills/interrogate/SKILL.md",
}

LITERAL_REPLACEMENTS = (
    ("~/.cursor/rules/pstack-models.mdc", "~/.codex/pstack-models.json"),
    ("~/.cursor/projects/*/", "Codex task history outside the active workspace"),
    ("~/.cursor/skills/", "~/.agents/skills/"),
    ("~/.cursor/plugins/", "~/.codex/plugins/"),
    (
        "plugin-installed paths under `~/.codex/plugins/`",
        "plugin-installed skill locations surfaced by Codex",
    ),
    (".cursor/skills/", ".agents/skills/"),
    (".cursor/worktrees/", ".codex/worktrees/"),
    ("Cursor's built-in `create-skill` skill", "Codex's built-in `$skill-creator` skill"),
    ("Cursor's built-in `create-skill`", "Codex's built-in `$skill-creator`"),
    ("`create-skill`'s", "`$skill-creator`'s"),
    ("`create-skill` skill", "`$skill-creator` skill"),
    ("via create-skill", "via `$skill-creator`"),
    ("new skill via `$skill-creator`", "new skill via `$skill-creator`"),
    ("The `Task` tool", "Codex's `spawn_agent` collaboration tool"),
    ("the Task tool", "Codex's collaboration tools"),
    ("Task tool", "Codex collaboration tools"),
    ("`Task` calls", "`spawn_agent` calls"),
    ("`Task` call", "`spawn_agent` call"),
    ("Task calls", "subagent spawns"),
    ("Task subagent", "Codex subagent"),
    ("`Task` prompts", "subagent prompts"),
    ("Spawn `Task`", "Spawn one read-only Codex subagent"),
    ("generalPurpose", "a generic Codex subagent"),
    ("subagent_type", "delegation role"),
    ("- `delegation role`: `a generic Codex subagent`", "- Tool: `spawn_agent`"),
    ("`AskQuestion`", "a concise user question"),
    ("AskQuestion", "a user question"),
    ("Cursor's `/loop` command", "Codex's wait or heartbeat automation tools"),
    ("Cursor's built-in babysit skill", "a generic PR-monitoring shortcut"),
    ("Cursor cloud agents", "Codex subagents"),
    ("Cursor cloud agent", "Codex subagent"),
    ("cloud agents", "Codex subagents"),
    ("cloud agent", "Codex subagent"),
    ("Cloud agents", "Codex subagents"),
    ("Cloud agent", "Codex subagent"),
    ("cloud workers", "Codex subagents"),
    ("cloud worker", "Codex subagent"),
    ("cloud concurrency limit", "host concurrency limit"),
    ("cloud-agent URL", "Codex task link"),
    ("cloud agent URL", "Codex task link"),
    ("cloud VM", "isolated worktree"),
    ("cloud spawns", "subagent spawns"),
    ("cloud spawn", "subagent spawn"),
    ("cloud default", "subagent default"),
    ("cloud work", "durable commits, branches, PRs, and explicitly created tasks"),
    ("in cloud", "in an isolated worktree"),
    ("Cursor dashboard", "Codex task status"),
    ("restart Cursor", "restart Codex"),
    ("Cursor restart", "Codex restart"),
    ("Cursor's agent store", "the pstack orchestration store"),
    ("the Cursor agent store", "the pstack orchestration store"),
    ("Cursor environment", "Codex environment"),
    ("Cursor exposes", "Codex exposes"),
    ("Cursor also exposes", "Codex also exposes"),
    ("Cursor's system prompt", "Codex's system prompt"),
    ("Cursor's", "Codex's"),
    ("Cursor", "Codex"),
    ("cursor-team-kit", "available Codex tooling"),
    ("`control-cli`", "the available shell or terminal driver"),
    ("`control-ui`", "the available browser or computer-use driver"),
    ("control-cli", "the available shell or terminal driver"),
    ("control-ui", "the available browser or computer-use driver"),
    (
        "A local root arms each tick as a real terminal `/loop`. The loop uses a "
        "monitored-shell 30-minute sleep and emits an output-notification sentinel. A "
        "cloud root uses the existing cloud-sleeper wake chain instead.",
        "While work is active, wait on the running subagents and audit whenever control "
        "returns. If the user requested recurring monitoring and the surface supports it, "
        "use a Codex heartbeat automation for the 30-minute cadence.",
    ),
    (
        "Arm the 30-minute audit tick. In a local session, a real terminal `/loop`. In a "
        "cloud root, a cloud-sleeper wake chain.",
        "Arm a 30-minute audit only when the user requested recurring monitoring: use a "
        "Codex heartbeat when available; otherwise audit whenever control returns from "
        "active subagents.",
    ),
    ("armed `/goal`", "documented standing objective"),
    ("`/goal`", "standing objective"),
    ("The goal continues", "The standing objective continues"),
    ("currently open files, recent edits, the cursor location", "currently open files and recent edits"),
    ("open files, recent edits, cursor location", "open files and recent edits"),
    ("**create-skill** skill", "**$skill-creator** skill"),
    ("Open a todolist", "Open a Codex plan"),
    ("opens a todolist", "opens a Codex plan"),
    ("todolist", "Codex plan"),
    ("todo list", "Codex plan"),
    ("Glob for", "Use `rg --files` to find"),
    ("Grep for", "use `rg` for"),
    ("(Glob, Grep, Read)", "(`rg --files`, `rg`, and file reads)"),
    ("todo items", "plan items"),
    ("open todos", "open plan items"),
    ("todos", "plan items"),
    ("omit Task `model`", "omit the model override"),
    ("in a single message", "back-to-back before waiting"),
    ("in one message", "back-to-back before waiting"),
)

PATH_REPLACEMENTS: dict[str, tuple[tuple[str, str], ...]] = {
    "skills/swarm/SKILL.md": (
        (
            "Spawn all N workers in one message with `subagent_type: generalPurpose`, "
            "`environment: \"cloud\"`, `run_in_background: true`, and the configured model. "
            "Use `environment: \"local\"` only when the worker needs access to something on "
            "the user's computer.\n\nWhen a worker must start from a non-default pushed branch, "
            "pass `cloud_base_branch`.",
            "Call `spawn_agent` for all N workers back-to-back before waiting. Codex subagents "
            "share the workspace, so give every writer an isolated worktree or branch and every "
            "read-only worker an explicit no-write brief. If work must continue in a separate "
            "user-visible Codex task, create one only when the user explicitly asks for that. "
            "Include a non-default starting branch in the brief instead of relying on hidden "
            "environment fields.",
        ),
        (
            "Spawn all N workers in one message with `delegation role: a generic Codex subagent`, a Codex subagent, asynchronously, and the configured model. Use a Codex subagent with local access only when the worker needs access to something on the user's computer.\n\nWhen a worker must start from a non-default pushed branch, pass the starting branch named in the brief.",
            "Call `spawn_agent` for all N workers back-to-back before waiting. Codex subagents share the workspace, so give every writer an isolated worktree or branch and every read-only worker an explicit no-write brief. Include a non-default starting branch in the brief. Use a separate user-visible Codex task only when the user explicitly asks for one.",
        ),
        (
            "Spawn all N workers back-to-back before waiting with `delegation role: a generic Codex subagent`, a Codex subagent, asynchronously, and the configured model. Use a Codex subagent with local access only when the worker needs access to something on the user's computer.\n\nWhen a worker must start from a non-default pushed branch, pass the starting branch named in the brief.",
            "Call `spawn_agent` for all N workers back-to-back before waiting. Codex subagents share the workspace, so give every writer an isolated worktree or branch and every read-only worker an explicit no-write brief. Include a non-default starting branch in the brief. Use a separate user-visible Codex task only when the user explicitly asks for one.",
        ),
    ),
    "skills/arena/SKILL.md": (
        (
            "Spawn all N subagents in one message with asynchronously,",
            "Call `spawn_agent` for all N candidates back-to-back before waiting,",
        ),
        (
            "Spawn all N subagents back-to-back before waiting with asynchronously,",
            "Call `spawn_agent` for all N candidates back-to-back before waiting,",
        ),
    ),
    "skills/no-comments/SKILL.md": (
        (
            "Spawn `spawn_agent` with `subagent_type: \"Comment Sicko\"`. Pass the scope. Do not restate its rules.",
            "Spawn one read-only Codex subagent and tell it to invoke `$comment-sicko` on the scope. Pass the scope by path or diff reference; do not restate the reviewer's rules.",
        ),
        (
            "Spawn one read-only Codex subagent with `delegation role: \"Comment Sicko\"`. Pass the scope. Do not restate its rules.",
            "Spawn one read-only Codex subagent and tell it to invoke `$comment-sicko` on the scope. Pass the scope by path or diff reference; do not restate the reviewer's rules.",
        ),
    ),
    "skills/poteto-mode/SKILL.md": (
        (
            "**Just do it.** Use any MCP tool. Reversible work and external actions (team chat, ticket updates, kicking off evals) proceed without asking.\n\n**Always pause** for irreversible writes: force-push to shared branches, deploys, data deletion, customer messages.",
            "**Act autonomously inside the user's scope.** Use read-only tools freely and carry out reversible repository work that the request authorizes. External writes such as chat messages, ticket updates, eval launches, PR merges, and deployments require the user's request to place that action in scope; the mode never broadens authorization.\n\n**Always pause** for irreversible or high-impact writes: force-pushes to shared branches, deployments, data deletion, customer messages, and destructive cleanup whose exact target is unclear.",
        ),
        (
            "**Use `delegation role: \"poteto-agent\"` for any subagent you spawn inside a playbook step** (code-writing delegates, ad-hoc helpers). `$poteto-mode` and `poteto-agent` route through the same wrapper. Routed workflow skills (`how`, `why`, `interrogate`, `reflect`, `swarm`) set their own `delegation role` for diverse-model review; respect what the skill prescribes, don't override to `poteto-agent`.\n\n**Defaults for every `spawn_agent` call.** asynchronously, agent mode (read-only strips MCP), file pointers not inlined context, explicit model per role (configurable via `$setup-pstack`; defaults `gpt-5.6-luna` at `xhigh` for code, `gpt-5.6-sol` at `xhigh` for prose and judgment). Code delegates tier by difficulty. The hardest changes (cross-cutting design, gnarly concurrency, subtle algorithms) go to your strongest judgment model (`gpt-5.6-sol` at `xhigh`) when the task needs judgment or the intent is vague, and to your strongest instruction-following model (`gpt-5.6-sol` at `xhigh`) when the work is a precisely specified sequence of steps to execute to the letter; trivial mechanical edits go to your fast code model. Per-role lines in the `$setup-pstack` rule override these defaults and the model choices in the routed skills (`how`, `why`, `arena`, `swarm`, `architect`, `interrogate`, `reflect`); a role with no line keeps its default, and a role line of `inherit-parent` or `auto` runs that role on the parent chat model (omit the model override).",
            "**For a playbook subagent that should use poteto's full style, tell it to invoke `$poteto-mode` before acting.** Routed workflow skills (`$how`, `$why`, `$interrogate`, `$reflect`, `$swarm`) provide their own focused briefs; respect those briefs instead of adding the full wrapper.\n\n**Defaults for every `spawn_agent` call.** Spawn asynchronously, pass file pointers instead of inlining bulk context, isolate every writer in its own worktree or disjoint path, and keep read-only reviewers on a no-write brief. Resolve model and reasoning effort through `references/codex-runtime.md` and `$setup-pstack`. Omit overrides when a configured model is unavailable; never invent a slug.",
        ),
    ),
    "skills/poteto-agent/SKILL.md": (
        (
            "Substituting `a generic Codex subagent` skips that read and drifts.",
            "A worker that skips that read will drift from the mode.",
        ),
        (
            "Resume an existing `poteto-agent` for the conversation rather than spawning a sibling.",
            "Use this as the explicit brief for a Codex subagent that should follow poteto's full style.",
        ),
    ),
    "skills/why/SKILL.md": (
        (
            "Before spawning investigators, list the available MCPs from the Codex environment. Use the available-tools map when present. Otherwise inspect the `mcps/` directory Codex exposes for enabled MCP servers.",
            "Before spawning investigators, inspect the tools and connectors exposed in the current Codex task. Use tool search when the surface provides it. Do not scan generic MCP resource directories to discover apps, and do not assume an unlisted connector is installed.",
        ),
    ),
    "skills/show-me-your-work/SKILL.md": (
        (
            "At the end of the run, before handing back, check the log told the truth. Read this run's transcript under the active workspace's `agent-transcripts/` directory (the system prompt names the path). Don't glob across `Codex task history outside the active workspace`; that reads unrelated private chats. Walk the log against what actually happened:",
            "At the end of the run, before handing back, check that the log told the truth. Use Codex task-history tools for the current task when available; otherwise use the current conversation and tool results. Never crawl unrelated task history. Walk the log against what actually happened:",
        ),
    ),
    "skills/poteto-mode/playbooks/eval.md": (
        (
            "6. **Verify the chain from transcripts, not self-report.** Read each candidate's local transcript under the active workspace's `agent-transcripts/` directory (the system prompt names this path). Do not glob across `Codex task history outside the active workspace`; that crosses workspace boundaries and reads private chats from unrelated projects. Look at which files each candidate actually opened. Citing a principle is not reading its leaf skill, and reading it is not applying it. Grade chain-following from the files it really read plus the shape of the code, never from the candidate's own claims.",
            "6. **Verify the chain from task evidence, not self-report.** Use each candidate's returned tool evidence and Codex task record when available. Look at which files each candidate actually opened. Citing a principle is not reading its leaf skill, and reading it is not applying it. Grade chain-following from observed file access plus the shape of the code, never from the candidate's own claims.",
        ),
    ),
    "skills/poteto-mode/playbooks/session-pickup.md": (
        (
            "1. Locate the prior trail. A local transcript under the active workspace's `agent-transcripts/` directory (the system prompt names the path; do not glob across `Codex task history outside the active workspace`, that crosses workspace boundaries and reads private chats from unrelated projects), a cloud-agent URL, or a pushed branch. Read the metadata overview and last messages first, then scan back for the decision points. Parse a long transcript in a subagent and keep the reduced timeline in the main thread (the **principle-guard-the-context-window** skill).",
            "1. Locate the prior trail: a Codex task link, task-history result, decision log, or pushed branch. Read the task overview and latest turns first, then scan back for decision points. Reduce a long task record in a read-only subagent and keep only the timeline in the main task (the **principle-guard-the-context-window** skill). If task-history tools are unavailable, use git, PR state, and the user's supplied links; never crawl undocumented session storage.",
        ),
        (
            "1. Locate the prior trail. A local transcript under the active workspace's `agent-transcripts/` directory (the system prompt names the path; do not glob across `Codex task history outside the active workspace`, that crosses workspace boundaries and reads private chats from unrelated projects), a Codex task link, or a pushed branch. Read the metadata overview and last messages first, then scan back for the decision points. Parse a long transcript in a subagent and keep the reduced timeline in the main thread (the **principle-guard-the-context-window** skill).",
            "1. Locate the prior trail: a Codex task link, task-history result, decision log, or pushed branch. Read the task overview and latest turns first, then scan back for decision points. Reduce a long task record in a read-only subagent and keep only the timeline in the main task (the **principle-guard-the-context-window** skill). If task-history tools are unavailable, use git, PR state, and the user's supplied links; never crawl undocumented session storage.",
        ),
    ),
    "skills/poteto-mode/playbooks/orchestrate.md": (
        (
            "Agents are spawned, resumed, and drained only through the Codex collaboration tools.",
            "Subagents are spawned, messaged, and drained only through Codex's collaboration "
            "tools (`spawn_agent`, `send_message`, and `wait_agent`).",
        ),
        (
            "Always `environment: \"cloud\"` unless the task needs this machine",
            "Use a Codex subagent; isolate writes in a worktree when the task mutates files",
        ),
        ("`environment: \"cloud\"`,", "a Codex subagent,"),
        ("`environment: \"local\"`,", "a Codex subagent with local access,"),
        ("`cloud_base_branch`", "the starting branch named in the brief"),
        (
            "reading local transcripts under `agent-transcripts/`;",
            "reading prior Codex task history through task tools;",
        ),
        (
            "A track the coordinator can drain itself needs no middle layer: each nested layer re-pays a full orientation preamble, and a blocking sub-coordinator hides its children while the parent idles. Owns its track's units and boards, authors its workers' briefs, spawns its own workers and verifiers (nesting works to depth 3, and a nested spawn has the full Task schema including `environment`).",
            "A track the coordinator can drain itself needs no middle layer: each nested layer re-pays a full orientation preamble, and a blocking sub-coordinator hides its children while the parent idles. It owns its track's units and boards, authors worker briefs, and spawns workers and verifiers only when the current Codex collaboration tools permit nesting.",
        ),
        (
            "Restacks run in an isolated worktree; a local restack at this scale takes the laptop down.",
            "Restacks run in a dedicated worktree so they do not block or corrupt other lanes.",
        ),
        (
            "After a Codex restart: local agents are dead, durable commits, branches, PRs, and explicitly created tasks is not. Re-read the standing orders and `units.tsv`, recompute the frontier, reattach durable commits, branches, PRs, and explicitly created tasks by PR and branch rather than agent id, respawn one sub-coordinator per track from its stored brief plus current state, drain, resume.",
            "After a Codex restart, assume ephemeral subagents are gone. Re-read the standing orders and `units.tsv`, recompute the frontier from commits, branches, PRs, and explicitly created user-visible tasks, then respawn only the lanes still needed from their stored briefs.",
        ),
    ),
    "skills/poteto-mode/playbooks/multi-phase-plan.md": (
        (
            "the armed /goal",
            "the documented standing objective and current plan",
        ),
        (
            "Explore in subagents with `delegation role: \"poteto-agent\"` and an explicit model per the Subagents section",
            "Explore in subagents whose brief begins by invoking `$poteto-mode`, using model settings from the Subagents section",
        ),
        (
            "Each live lane runs on its own isolated worktree at the PR head.",
            "Each live lane runs in its own worktree at the PR head.",
        ),
        (
            "Run `node pstack/skills/poteto-mode/scripts/check-plan.mjs <plan.md>`",
            "Resolve the installed `$poteto-mode` skill directory, then run "
            "`node <skill-directory>/scripts/check-plan.mjs <plan.md>`",
        ),
        (
            "The program runs `pstack/skills/poteto-mode/playbooks/<execution playbook>.md`.",
            "The program follows `<execution playbook>.md` from the installed "
            "`$poteto-mode` skill's `playbooks/` directory.",
        ),
        (
            "`git show origin/main:pstack/skills/poteto-mode/playbooks/<execution playbook>.md`",
            "Re-read the selected execution playbook from the installed `$poteto-mode` skill",
        ),
        (
            "`git show origin/main:pstack/skills/swarm/SKILL.md`",
            "Invoke `$swarm` and re-read its installed `SKILL.md`",
        ),
        (
            "`git show origin/main:pstack/skills/poteto-mode/playbooks/opening-a-pr.md`",
            "Re-read `opening-a-pr.md` from the installed `$poteto-mode` skill",
        ),
        (
            "`git show origin/main:pstack/skills/<each other leaf skill the program uses>`",
            "Invoke and re-read each other installed leaf skill the program uses",
        ),
        (
            "run the swarm per `pstack/skills/swarm/SKILL.md`",
            "run `$swarm` using its installed skill instructions",
        ),
        (
            "Which PRs get `pstack/skills/how/SKILL.md` and `pstack/skills/interrogate/SKILL.md`. "
            "The trail per `pstack/skills/show-me-your-work/SKILL.md`.",
            "Which PRs invoke `$how` and `$interrogate`. The trail follows "
            "`$show-me-your-work`.",
        ),
    ),
    "skills/poteto-mode/playbooks/autopilot-stack.md": (
        (
            "the cloud environment forces",
            "the shared-filesystem subagent model requires",
        ),
        (
            "re-read this playbook from trunk with "
            "`git show origin/main:pstack/skills/poteto-mode/playbooks/autopilot-stack.md`",
            "re-read this installed playbook from its current skill path",
        ),
    ),
    "skills/poteto-mode/playbooks/autopilot-full.md": (
        (
            "re-read this playbook from trunk with "
            "`git show origin/main:pstack/skills/poteto-mode/playbooks/autopilot-full.md`",
            "re-read this installed playbook from its current skill path",
        ),
    ),
    "skills/poteto-mode/playbooks/babysit.md": (
        (
            "a cloud one plus a local one",
            "two independent agents",
        ),
    ),
    "docs/guide/03-understand.md": (
        (
            "[`$recall`](../../skills/recall/SKILL.md) mines your own recent chats plus "
            "the shared record (issues, prior fixes, errors still firing) and hands back a "
            "brief on where things stand and what's next. Use it when you're returning to a "
            "topic cold. If you want to resume one specific chat, that's the Session pickup "
            "playbook below, not `$recall`.",
            "[`$recall`](../../skills/recall/SKILL.md) reads Codex task history scoped to the "
            "active project when task tools are available, then cross-checks the shared "
            "record (issues, prior fixes, errors still firing). If task history is unavailable, "
            "it uses the current task, git and PR state, decision trails, and links you provide. "
            "Use it when you're returning to a topic cold. If you want to resume one specific "
            "task, that's the Session pickup playbook below, not `$recall`.",
        ),
    ),
    "docs/guide/02-poteto-mode.md": (
        ("A long chat accumulates", "A long Codex task accumulates"),
        ("which chats still touch it", "which tasks still touch it"),
    ),
    "docs/guide/05-build-and-clean.md": (
        (
            "`$deslop` ships in the `available Codex tooling` plugin, not in pstack. If you "
            "don't have it, ask for the same outcome in plain words: remove narrating comments, "
            "unsupported guards, dead compatibility paths, and unrelated edits.",
            "`$deslop` ships with pstack-codex. It removes narrating comments, unsupported "
            "guards, dead compatibility paths, and unrelated edits.",
        ),
        (
            "[Comment Sicko](../../agents/comment-sicko.md)",
            "[Comment Sicko](../../skills/comment-sicko/SKILL.md)",
        ),
    ),
    "docs/guide/08-principles.md": (
        (
            "[Never Block on the Human](../../skills/principle-never-block-on-the-human/SKILL.md) "
            "proceeds on reversible work and presents the result.",
            "[Never Block on the Human](../../skills/principle-never-block-on-the-human/SKILL.md) "
            "proceeds on authorized reversible work and presents the result.",
        ),
    ),
    "docs/guide/10-recipes-and-pitfalls.md": (
        (
            '"make it better" gives `Codex heartbeat automation` nothing to check.',
            '"make it better" gives a long-running task or heartbeat nothing to check.',
        ),
        (
            "pinned cards reading $how, $tdd, and Codex heartbeat automation above",
            "pinned cards reading $how, $tdd, and HEARTBEAT above",
        ),
        ("parent chat model", "parent task model"),
    ),
}

RUNTIME_AWARE = {
    "skills/architect/SKILL.md",
    "skills/arena/SKILL.md",
    "skills/how/SKILL.md",
    "skills/interrogate/SKILL.md",
    "skills/no-comments/SKILL.md",
    "skills/poteto-mode/SKILL.md",
    "skills/reflect/SKILL.md",
    "skills/swarm/SKILL.md",
    "skills/why/SKILL.md",
}


def git_output(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout.strip()


def source_digest(source: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        digest.update(path.relative_to(source).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def mirror_tree(source: Path, target: Path) -> None:
    """Mirror source into an existing root without replacing the root itself."""
    target.mkdir(parents=True, exist_ok=True)
    source_names = {child.name for child in source.iterdir()}
    for stale in target.iterdir():
        if stale.name not in source_names:
            remove_path(stale)

    for source_child in source.iterdir():
        target_child = target / source_child.name
        if source_child.is_dir() and not source_child.is_symlink():
            if target_child.exists() and (
                not target_child.is_dir() or target_child.is_symlink()
            ):
                remove_path(target_child)
            mirror_tree(source_child, target_child)
        elif source_child.is_symlink():
            if target_child.is_symlink() and target_child.readlink() == source_child.readlink():
                continue
            remove_path(target_child)
            target_child.symlink_to(source_child.readlink())
        else:
            if (
                target_child.is_file()
                and not target_child.is_symlink()
                and source_child.read_bytes() == target_child.read_bytes()
            ):
                source_mode = source_child.stat().st_mode & 0o777
                target_mode = target_child.stat().st_mode & 0o777
                if source_mode != target_mode:
                    target_child.chmod(source_mode)
                continue
            if target_child.exists() or target_child.is_symlink():
                remove_path(target_child)
            shutil.copy2(source_child, target_child, follow_symlinks=False)


def normalize_frontmatter(text: str) -> tuple[str, bool]:
    if not text.startswith("---\n"):
        return text, False
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unterminated YAML frontmatter")
    lines = text[4:end].splitlines()
    explicit_only = any(line == "disable-model-invocation: true" for line in lines)
    kept: list[str] = []
    for line in lines:
        key = line.split(":", 1)[0]
        if key in {"disable-model-invocation", "mode", "icon", "color", "reminder", "is_background"}:
            continue
        if line.startswith("name:"):
            raw = line.split(":", 1)[1].strip().strip('"\'')
            raw = re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower()
            line = f"name: {raw}"
        kept.append(line)
    return "---\n" + "\n".join(kept) + "\n---\n" + text[end + 5 :], explicit_only


def replace_skill_invocations(text: str, skill_names: set[str]) -> str:
    for name in sorted(skill_names, key=len, reverse=True):
        pattern = rf"(?<![A-Za-z0-9_.-])/{re.escape(name)}(?![A-Za-z0-9_-])"
        text = re.sub(pattern, f"${name}", text)
    return text


def transform_script_text(relative_path: str, text: str) -> str:
    """Apply only syntax-safe rewrites to executable source files."""
    if relative_path == "skills/poteto-mode/scripts/check-plan.mjs":
        text = text.replace(
            "`grok-4.6-fast-xhigh`",
            "`gpt-5.6-luna` at `xhigh`",
        )
        text = text.replace('"/goal"', '"standing objective"')
    return text


def transform_text(relative_path: str, text: str, skill_names: set[str]) -> tuple[str, bool]:
    text, explicit_only = normalize_frontmatter(text)
    text = replace_skill_invocations(text, skill_names)
    model_replacements = (
        PANEL_MODEL_REPLACEMENTS
        if relative_path in PANEL_MODEL_PATHS
        else MODEL_REPLACEMENTS
    )
    for old, new in model_replacements.items():
        text = text.replace(f"`{old}`", f"`{new}`")
        text = text.replace(old, new.replace("`", ""))
    for old, new in LITERAL_REPLACEMENTS:
        text = text.replace(old, new)

    role_names = {
        "arena runners": "arena-runners",
        "arena cross-judge pool": "arena-cross-judge",
        "architect runners": "architect-runners",
        "how explorer": "how-explorer",
        "how explainer": "how-explainer",
        "how critics": "how-critics",
        "interrogate reviewers": "interrogate-reviewers",
        "reflect tooling": "reflect-tooling",
        "reflect judgment": "reflect-judgment",
        "reflect divergent": "reflect-divergent",
        "reflect synthesizer": "reflect-synthesizer",
        "swarm workers": "swarm-workers",
        "why investigators": "why-investigators",
        "why synthesizer": "why-synthesizer",
    }
    for old, new in role_names.items():
        text = text.replace(old, new)

    text = re.sub(
        r"Spawn all ([^\n.]+) in (?:one|a single) message",
        r"Spawn all \1 back-to-back before waiting",
        text,
    )

    text = re.sub(
        r"^- `subagent_type`: `generalPurpose`$",
        "- Tool: `spawn_agent`",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^- `readonly`: `true`$",
        "- Read-only posture: inspect and report; do not edit files.",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^- `readonly`: `false`[^\n]*$",
        "- Tool access: retain normal Codex tools and connectors; the brief forbids writes.",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^- `read-only`: `false`[^\n]*$",
        "- Tool access: retain normal Codex tools and connectors; the brief forbids writes.",
        text,
        flags=re.MULTILINE,
    )
    if relative_path.endswith(".md"):
        text = text.replace("readonly", "read-only")
    text = text.replace("`subagent_type: generalPurpose`", "`spawn_agent`")
    text = text.replace("`subagent_type: \"poteto-agent\"`", "a subagent brief that explicitly invokes `$poteto-mode`")
    text = text.replace("`subagent_type: \"Comment Sicko\"`", "a subagent brief that explicitly invokes `$comment-sicko`")
    text = text.replace("`run_in_background: true`", "asynchronously")
    text = text.replace("`environment: \"cloud\"`", "a Codex subagent")
    text = text.replace("`environment: \"local\"`", "a Codex subagent with local access")
    text = text.replace("`cloud_base_branch`", "the starting branch named in the brief")

    text = text.replace("under `/loop` in dynamic mode", "with a Codex heartbeat automation")
    text = text.replace("as a real terminal `/loop`", "as a Codex heartbeat automation")
    text = text.replace("a real terminal `/loop`", "a Codex heartbeat automation")
    text = text.replace("\"/loop until X\"", "\"keep going until X\"")
    text = text.replace("\"/loop until", "\"keep going until")
    text = text.replace("/loop per component", "iterate per component")
    text = text.replace("/loop", "Codex heartbeat automation")
    text = text.replace("cloud-sleeper wake chain", "Codex task heartbeat")
    text = text.replace("cloud root", "long-running Codex task")
    text = text.replace("local root", "current Codex task")

    for old, new in PATH_REPLACEMENTS.get(relative_path, ()):
        text = text.replace(old, new)

    if relative_path in RUNTIME_AWARE:
        heading = re.search(r"(?m)^# [^\n]+\n", text)
        if heading is None:
            raise ValueError(f"cannot find title in {relative_path}")
        note = (
            "\n\n> Codex runtime: read "
            "[`../poteto-mode/references/codex-runtime.md`](../poteto-mode/references/codex-runtime.md) "
            "before delegating, selecting models, waiting, or inspecting task history. "
            "Its native Codex contract takes precedence over stale host syntax in an upstream change.\n"
        )
        # Fix the relative path for the poteto-mode skill itself.
        if relative_path == "skills/poteto-mode/SKILL.md":
            note = note.replace("../poteto-mode/references/", "references/")
        text = text[: heading.end()] + note + text[heading.end() :]

    return text, explicit_only


def write_invocation_policy(skill_dir: Path) -> None:
    agent_dir = skill_dir / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    skill_name = skill_dir.name
    display_name = skill_name.replace("-", " ").title()
    short_description = "Invoke this pstack workflow explicitly."
    default_prompt = f"Use ${skill_name} for this task."
    (agent_dir / "openai.yaml").write_text(
        "interface:\n"
        f"  display_name: {json.dumps(display_name)}\n"
        f"  short_description: {json.dumps(short_description)}\n"
        f"  default_prompt: {json.dumps(default_prompt)}\n"
        "policy:\n"
        "  allow_implicit_invocation: false\n",
        encoding="utf-8",
    )


def build(source_repo: Path, source_ref: str = "main") -> None:
    source = source_repo / "pstack" if (source_repo / "pstack").is_dir() else source_repo
    manifest_path = source / ".cursor-plugin" / "plugin.json"
    if not manifest_path.is_file():
        raise SystemExit(f"not a pstack source tree: missing {manifest_path}")

    upstream_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = upstream_manifest["version"]
    skill_names = {
        path.parent.name
        for path in (source / "skills").rglob("SKILL.md")
        if "grokbot/make-bot-ui" not in path.as_posix()
    }
    skill_names.update({"comment-sicko", "poteto-agent", "deslop"})

    PLUGIN_ROOT.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="pstack-codex-sync-", dir=PLUGIN_ROOT.parent))
    temp_plugin = temp_root / "pstack-codex"
    temp_skills = temp_plugin / "skills"
    temp_skills.mkdir(parents=True)
    try:
        shutil.copytree(
            source / "skills",
            temp_skills,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("grokbot"),
        )
        shutil.copytree(source / "docs" / "guide", temp_plugin / "docs" / "guide")
        shutil.copytree(source / "agents", temp_plugin / "_agents-source")
        shutil.copytree(source / "agents", temp_skills / "_agent-conversion-source")

        agent_source = temp_plugin / "_agents-source"
        for agent_name in ("poteto-agent", "comment-sicko"):
            src = agent_source / f"{agent_name}.md"
            if not src.exists() and agent_name == "comment-sicko":
                src = agent_source / "comment-sicko.md"
            target = temp_skills / agent_name / "SKILL.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        shutil.rmtree(temp_plugin / "_agents-source")
        shutil.rmtree(temp_skills / "_agent-conversion-source")

        explicit_only_dirs: set[Path] = set()
        for path in sorted(temp_plugin.rglob("*")):
            if not path.is_file() or path.suffix not in {".md", ".sh", ".json", ".ts", ".mjs"}:
                continue
            relative = path.relative_to(temp_plugin).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if path.suffix in {".ts", ".json"}:
                continue
            if path.suffix == ".mjs":
                transformed = transform_script_text(relative, text)
                explicit_only = False
            else:
                transformed, explicit_only = transform_text(relative, text, skill_names)
            path.write_text(transformed, encoding="utf-8")
            if explicit_only and path.name == "SKILL.md":
                explicit_only_dirs.add(path.parent)

        package_path = temp_skills / "poteto-mode" / "scripts" / "package.json"
        if package_path.exists():
            package = json.loads(package_path.read_text(encoding="utf-8"))
            package["name"] = "@pstack-codex/poteto-mode-tools"
            package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
            lock_path = package_path.with_name("bun.lock")
            if lock_path.exists():
                lock_path.write_text(
                    lock_path.read_text(encoding="utf-8").replace(
                        "@cursor-skill/poteto-mode-tools", "@pstack-codex/poteto-mode-tools"
                    ),
                    encoding="utf-8",
                )

        for skill_dir in explicit_only_dirs:
            write_invocation_policy(skill_dir)

        if OVERLAY_ROOT.exists():
            shutil.copytree(OVERLAY_ROOT, temp_plugin, dirs_exist_ok=True)

        shutil.copy2(source / "LICENSE", temp_plugin / "LICENSE")

        for executable in (
            temp_skills / "poteto-mode" / "scripts" / "worktree-audit.sh",
            temp_skills / "poteto-mode" / "scripts" / "watch-pr" / "watch-pr",
            temp_skills / "show-me-your-work" / "scripts" / "log.sh",
        ):
            if executable.exists():
                executable.chmod(executable.stat().st_mode | 0o111)

        manifest = {
            "name": "pstack-codex",
            "version": f"{version}-codex.{CODEX_REVISION}",
            "description": (
                "Native Codex port of pstack: rigorous engineering workflows, deliberate "
                "parallelism, concise prose, simple code, and verified delivery."
            ),
            "author": {
                "name": "Vextil and pstack Codex contributors",
                "url": "https://github.com/Vextil/pstack-codex",
            },
            "homepage": "https://github.com/Vextil/pstack-codex#readme",
            "repository": "https://github.com/Vextil/pstack-codex",
            "license": "MIT",
            "keywords": [
                "pstack",
                "poteto-mode",
                "codex",
                "workflow",
                "review",
                "subagents",
            ],
            "skills": "./skills/",
            "interface": {
                "displayName": "pstack for Codex",
                "shortDescription": "Go deep first: rigorous, parallelizable engineering workflows",
                "longDescription": (
                    "A native Codex port of Lauren Tan's pstack. It packages poteto-mode, "
                    "architecture exploration, adversarial review, root-cause debugging, "
                    "technical writing, and verification as first-class Codex skills."
                ),
                "developerName": "Vextil and pstack Codex contributors",
                "category": "Developer Tools",
                "capabilities": ["Interactive", "Read", "Write"],
                "websiteURL": "https://github.com/Vextil/pstack-codex",
                "defaultPrompt": [
                    "Work on this with $poteto-mode.",
                    "Use $interrogate to stress-test this diff.",
                    "Use $how to explain this subsystem.",
                ],
                "brandColor": "#7C3AED",
            },
        }
        manifest_dir = temp_plugin / ".codex-plugin"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        (manifest_dir / "plugin.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

        existing_manifest = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
        if PLUGIN_ROOT.exists():
            if not existing_manifest.exists():
                raise SystemExit(f"refusing to overwrite unexpected directory at {PLUGIN_ROOT}")
            existing = json.loads(existing_manifest.read_text(encoding="utf-8"))
            if existing.get("name") != "pstack-codex":
                raise SystemExit(f"refusing to overwrite unexpected plugin at {PLUGIN_ROOT}")
        mirror_tree(temp_plugin, PLUGIN_ROOT)

        try:
            commit = git_output(source_repo, "rev-parse", "HEAD")
        except (subprocess.CalledProcessError, FileNotFoundError):
            commit = "unknown"
        status = {
            "repository": "https://github.com/cursor/plugins",
            "subdirectory": "pstack",
            "ref": source_ref,
            "commit": commit,
            "version": version,
            "sourceSha256": source_digest(source),
            "excluded": EXCLUDED,
        }
        (REPO_ROOT / "UPSTREAM.json").write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        shutil.copy2(source / "LICENSE", REPO_ROOT / "LICENSE")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source",
        type=Path,
        help="cursor/plugins checkout root or its pstack subdirectory",
    )
    parser.add_argument(
        "--ref",
        default="main",
        help="upstream ref used for provenance (default: main)",
    )
    args = parser.parse_args()
    build(args.source.resolve(), args.ref)


if __name__ == "__main__":
    main()
