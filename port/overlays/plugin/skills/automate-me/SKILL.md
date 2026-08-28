---
name: automate-me
description: Create or update a personal Codex mode skill from the user's recurring working preferences. Use for automate me, capture my working style, or refresh my mode skill.
---

# Automate me

Turn the user's recurring conventions into one focused `-mode` skill. Use
Codex's `$skill-creator` for the artifact and `$unslop` for its prose.

1. Search `.agents/skills/**/*-mode/SKILL.md` and
   `~/.agents/skills/*-mode/SKILL.md` for an existing skill. Preserve an
   existing location and update it unless the user explicitly wants a fresh
   start.
2. Read `../poteto-mode/references/codex-runtime.md`. Use Codex task-history
   tools to sample recent tasks from the active project only. For a large
   history, fan out read-only subagents over disjoint time slices. Do not crawl
   undocumented session storage.
3. Look for repeated evidence about response style, autonomy, delegation,
   verification, code/prose discipline, git process, and skill use. Require two
   or more independent examples before treating a mined behavior as a rule.
4. Ask at most two structured questions when the current surface supports them,
   plus one optional free-form question. Focus on genuine preferences the task
   record cannot reveal.
5. Cluster only the rules with real evidence. Read `$poteto-mode` for
   granularity, not content.
6. Invoke `$skill-creator`. Default new repository skills to
   `.agents/skills/<handle>-mode/` and user-level skills to
   `~/.agents/skills/<handle>-mode/`. The user chooses repository versus user
   scope when it is not already clear.
7. Set `agents/openai.yaml` policy `allow_implicit_invocation: false` unless the
   user explicitly wants automatic invocation.
8. Apply `$unslop`, show the draft, iterate on feedback, and run the skill
   validator. Commit or open a PR only when the user asked for that repository
   action.

Do not overfit one conversation, restate other skills, invent generic rules, or
force empty sections for symmetry.
