# Contributing

Thanks for helping keep pstack native on Codex.

## Development workflow

1. Install Python 3, Git, and Bun.
2. Run `./scripts/sync_upstream.sh --source /path/to/cursor-plugins`.
3. Change `scripts/port_upstream.py` for general transforms or add a narrow file
   under `port/overlays/plugin` for semantic Codex behavior.
4. Regenerate the plugin. Do not hand-edit `plugins/pstack-codex` because the
   next sync overwrites generated content.
5. Run `python3 scripts/validate_port.py`, the Bun tests, and type checking.
6. Commit source changes and generated output together.

Keep upstream wording and structure where they are host-neutral. Codex-specific
changes should be minimal, documented, and testable. A removed upstream feature
must have a reason in the generated exclusion record.

Open bug reports at
[Vextil/pstack-codex/issues](https://github.com/Vextil/pstack-codex/issues).
Include the Codex version and surface, the pstack-codex version, the upstream
commit from `UPSTREAM.json`, the invoked skill, and a minimal reproduction with
secrets removed.
