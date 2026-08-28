# Porting architecture

This repository treats the Codex plugin as a generated artifact. The design
keeps upstream ingestion repeatable while giving host-specific behavior an
explicit, reviewable home.

## Pipeline

1. `scripts/sync_upstream.sh` obtains the requested revision of
   `cursor/plugins`, using a sparse checkout when no local source is supplied.
2. `scripts/port_upstream.py` copies the upstream pstack sources into a fresh
   temporary plugin tree.
3. Mechanical transforms normalize skill metadata, convert direct invocations
   to `$skill-name`, translate stable terminology, and turn the two upstream
   agent definitions into Codex skills.
4. Files in `port/overlays/plugin` replace the small set of workflows that need
   semantic, Codex-native implementations.
5. The converter writes `.codex-plugin/plugin.json` and `UPSTREAM.json`, then
   mirrors the generated tree in place. The stable root avoids file-coordination
   conflicts while stale generated files are still removed.
6. `scripts/validate_port.py` fails on invalid packaging, broken internal
   links, non-native runtime syntax, compatibility shims, or undocumented
   exclusions.

This follows OpenAI's migration guidance: commands and agents become skills,
provider-specific references are replaced, and unsupported host automation is
handled explicitly rather than emulated.

## Source-to-Codex mapping

| Upstream source | Generated Codex component |
| --- | --- |
| `.cursor-plugin/plugin.json` | `.codex-plugin/plugin.json` |
| `skills/*/SKILL.md` | `skills/*/SKILL.md` |
| explicit-only skill metadata | `skills/*/agents/openai.yaml` policy |
| `agents/poteto-agent.md` | `skills/poteto-agent/SKILL.md` |
| `agents/comment-sicko.md` | `skills/comment-sicko/SKILL.md` |
| host slash invocations | `$skill-name` invocations |
| delegation and task primitives | `poteto-mode/references/codex-runtime.md` |

There is intentionally no `commands/` directory, `.codex-plugin/prompts`
directory, Claude settings file, command router, or shared cross-host skill
tree.

## Model policy

Single-worker roles map upstream judgment and implementation models to
`gpt-5.6-sol` at `xhigh`, and upstream fast fan-out models to `gpt-5.6-luna`
at `xhigh`. The current upstream version does not use its Composer model slot,
but the converter maps it to Luna for forward compatibility.

Upstream intentionally uses four model families for independent candidates and
reviewers. Arena, Architect, Interrogate, and How critics therefore preserve a
four-family Codex roster: Sol, Terra, Luna, and GPT-5.5, all at `xhigh`. Arena's
cross-judge uses the same roster as a selection pool, spawns one judge, and
prefers a family different from the parent. This panel-specific policy prevents
the single-worker mapping from collapsing upstream's diversity.

## Semantic overlays

The overlay layer contains independently authored Codex behavior for:

- `setup-pstack`: optional native model-role configuration.
- `recall`: task history through supported Codex task tools.
- `reflect`: evidence gathering and durable learning in Codex.
- `automate-me`: native automation and skill boundaries.
- `deslop`: a self-contained implementation so the public plugin has no
  undeclared skill dependency.
- `poteto-mode/references/codex-runtime.md`: shared rules for plans,
  delegation, questions, waiting, model availability, and task history.
- `worktree-audit.sh`: repository-based checks without undocumented session
  storage.

Prefer a narrow overlay over a large fork. If a semantic transform applies to
many upstream files, promote it into the converter and add a validation rule.

## Exclusion policy

An upstream path may be excluded only when it depends on a host product surface
that a portable Codex plugin cannot provide. Add the path and reason to
`EXCLUDED` in `scripts/port_upstream.py`; the generated `UPSTREAM.json` is the
public compatibility record.

Do not silently drop a component, pretend an unsupported feature works, or add
a command shim. If Codex gains the required surface later, replace the
exclusion with a native implementation and a test.

## Updating the port

Run:

```bash
./scripts/sync_upstream.sh --ref <upstream-ref>
git diff -- UPSTREAM.json plugins/pstack-codex
```

Review in this order:

1. `UPSTREAM.json` version, commit, digest, and exclusions.
2. New or removed skills and manifest changes.
3. Converter failures caused by new host-specific syntax.
4. Semantic diffs in delegation-heavy skills and playbooks.
5. Tool tests and type checking under
   `plugins/pstack-codex/skills/poteto-mode/scripts`.

Commit the converter or overlay change together with the regenerated plugin.
Use the upstream version as the plugin version prefix and increment the
`CODEX_REVISION` value in `scripts/port_upstream.py` when the port changes
without a new upstream version.

## Maintainer checks

```bash
python3 scripts/validate_port.py
cd plugins/pstack-codex/skills/poteto-mode/scripts
bun install --frozen-lockfile
bun run test
bun run typecheck
```

Codex's bundled plugin validator is also run during local release validation.
The repository validator remains dependency-free so sync PRs fail early in any
ordinary Python 3 environment.

## Relevant Codex documentation

- [Plugins](https://learn.chatgpt.com/docs/plugins)
- [Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Convert a Claude Code plugin](https://developers.openai.com/plugins/guides/submit-claude-plugin)
- [Build and package plugins](https://developers.openai.com/plugins/build/plugins)
