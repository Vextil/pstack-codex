# pstack for Codex

`pstack-codex` is a native, source-generated Codex port of
[pstack](https://github.com/cursor/plugins/tree/main/pstack). It packages the
upstream engineering workflows as first-class Codex skills instead of sharing
another agent host's files or routing its commands through a compatibility
shim.

The generated plugin currently contains 47 skills, including `poteto-mode`,
`interrogate`, `how`, `architect`, `swarm`, `tdd`, and `technical-writing`.
`UPSTREAM.json` records the exact upstream version, Git commit, source digest,
and deliberate exclusions for each generated revision.

## Install

Install the published marketplace directly from GitHub:

```bash
codex plugin marketplace add Vextil/pstack-codex --ref main
codex plugin add pstack-codex@pstack-codex
```

Start a new Codex task after installing so its skills are loaded. To pick up a
new release later:

```bash
codex plugin marketplace upgrade pstack-codex
codex plugin add pstack-codex@pstack-codex
```

For local development, point Codex at this repository root:

```bash
codex plugin marketplace add /absolute/path/to/pstack-codex
codex plugin add pstack-codex@pstack-codex
```

Invoke a workflow explicitly with, for example:

```text
$poteto-mode implement this plan and verify the result
$interrogate review this diff adversarially
$how explain how this subsystem works
$setup-pstack configure the optional pstack model roles
```

## Update from upstream

Pull and regenerate from the latest upstream `main`:

```bash
./scripts/sync_upstream.sh
```

Pin a release or commit when reproducibility matters:

```bash
./scripts/sync_upstream.sh --ref <tag-or-commit>
```

Use an existing checkout while developing the converter:

```bash
./scripts/sync_upstream.sh \
  --source /path/to/cursor-plugins \
  --ref <checked-out-ref>
```

The scheduled GitHub Actions workflow checks upstream daily, regenerates the
plugin, validates it, runs the bundled tool tests, and opens or updates a pull
request when the generated result changes. Reviewing that PR is the release
gate; upstream changes are never silently published.

## What makes the port native

- Upstream skills become Codex `SKILL.md` packages with Codex invocation
  metadata.
- Upstream agent definitions become independently invocable Codex skills.
- Delegation, model selection, task history, waiting, and questions use a
  documented Codex runtime contract.
- Host-specific slash commands become `$skill-name` invocations.
- Semantic overlays replace workflows that need more than a mechanical rewrite.
- Validation rejects leftover host paths, tool fields, commands, prompt
  trampolines, and routing shims.

The conversion architecture and exception policy are documented in
[`PORTING.md`](PORTING.md). Generated plugin files live under
`plugins/pstack-codex`; edit the converter or `port/overlays`, then regenerate,
rather than hand-editing generated files.

## Compatibility boundary

Three upstream components are deliberately excluded:

- `automations/benny`, because its event automation needs a separate Codex
  product-level design.
- `docs/guide`, because it is a host-specific UI tutorial.
- `skills/grokbot/make-bot-ui`, because it depends on a host automation webhook
  without a portable public-plugin equivalent.

Every exclusion is machine-readable in `UPSTREAM.json`. New unsupported host
syntax fails CI so it must be ported or explicitly excluded.

## License and attribution

pstack is Copyright © 2026 Lauren Tan and distributed under the MIT License.
This derivative port preserves the upstream license and identifies generated
provenance in `UPSTREAM.json`. See [`NOTICE.md`](NOTICE.md).
