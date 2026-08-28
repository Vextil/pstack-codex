#!/usr/bin/env python3
"""Static validation for the generated Codex port and marketplace."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "pstack-codex"
SKILLS = PLUGIN / "skills"

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
BANNED_RUNTIME = {
    re.compile(r"\bCursor\b", re.IGNORECASE): "Cursor product language",
    re.compile(r"\bClaude\b", re.IGNORECASE): "Claude product language",
    re.compile(r"\bGrok\b", re.IGNORECASE): "Grok model language",
    re.compile(r"\.cursor(?:/|\\)", re.IGNORECASE): "Cursor path",
    re.compile(r"agent-transcripts", re.IGNORECASE): "Cursor transcript path",
    re.compile(r"pstack/skills/", re.IGNORECASE): "upstream repository skill path",
    re.compile(r"~/\.codex/plugins/", re.IGNORECASE): "undocumented plugin cache path",
    re.compile(r"subagent_type", re.IGNORECASE): "non-Codex subagent field",
    re.compile(r"run_in_background", re.IGNORECASE): "non-Codex background field",
    re.compile(r"cloud_base_branch", re.IGNORECASE): "non-Codex cloud field",
    re.compile(r"`Task`|Task tool"): "non-Codex Task tool",
    re.compile(r"AskQuestion"): "non-Codex question tool",
    re.compile(r"(?<![A-Za-z0-9_.-])/(?:loop|goal)(?![A-Za-z0-9_-])"): "Cursor slash primitive",
}


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def parse_frontmatter(path: Path, errors: list[str]) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        fail(f"{path.relative_to(ROOT)}: missing YAML frontmatter", errors)
        return {}
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.startswith(" "):
            continue
        if ":" not in line:
            fail(f"{path.relative_to(ROOT)}: malformed frontmatter line {line!r}", errors)
            continue
        key, value = line.split(":", 1)
        values[key] = value.strip().strip('"\'')
    for required in ("name", "description"):
        if not values.get(required):
            fail(f"{path.relative_to(ROOT)}: missing {required}", errors)
    unsupported = {
        "disable-model-invocation",
        "mode",
        "icon",
        "color",
        "reminder",
        "is_background",
        "user-invocable",
    }.intersection(values)
    if unsupported:
        fail(
            f"{path.relative_to(ROOT)}: unsupported host metadata {sorted(unsupported)}",
            errors,
        )
    return values


def validate_links(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        target = target.split("#", 1)[0]
        if (
            not target
            or target.startswith(("http://", "https://", "mailto:"))
            or ("/" not in target and "." not in target)
            or "<" in target
            or ">" in target
        ):
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(PLUGIN.resolve())
        except ValueError:
            fail(f"{path.relative_to(ROOT)}: link escapes plugin: {target}", errors)
            continue
        if not resolved.exists():
            fail(f"{path.relative_to(ROOT)}: broken relative link: {target}", errors)


def main() -> int:
    errors: list[str] = []

    manifest_path = PLUGIN / ".codex-plugin" / "plugin.json"
    marketplace_path = ROOT / ".agents" / "plugins" / "marketplace.json"
    upstream_path = ROOT / "UPSTREAM.json"
    for required in (manifest_path, marketplace_path, upstream_path, PLUGIN / "LICENSE"):
        if not required.is_file():
            fail(f"missing required file: {required.relative_to(ROOT)}", errors)

    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("name") != "pstack-codex":
            fail("plugin name must be pstack-codex", errors)
        if not SEMVER_RE.match(str(manifest.get("version", ""))):
            fail(f"invalid plugin semver: {manifest.get('version')!r}", errors)
        if manifest.get("skills") != "./skills/":
            fail("plugin skills path must be ./skills/", errors)
        prompts = manifest.get("interface", {}).get("defaultPrompt", [])
        if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
            fail("interface.defaultPrompt must contain one to three strings", errors)

    if upstream_path.is_file():
        upstream = json.loads(upstream_path.read_text(encoding="utf-8"))
        if not re.fullmatch(r"[0-9a-f]{40}|unknown", str(upstream.get("commit", ""))):
            fail("UPSTREAM.json commit must be a full Git SHA or unknown", errors)
        if not re.fullmatch(r"[0-9a-f]{64}", str(upstream.get("sourceSha256", ""))):
            fail("UPSTREAM.json sourceSha256 must be a SHA-256 digest", errors)
        if not upstream.get("excluded"):
            fail("UPSTREAM.json must record compatibility exclusions", errors)
        if manifest_path.is_file():
            expected_prefix = f"{upstream.get('version')}-codex."
            if not str(manifest.get("version", "")).startswith(expected_prefix):
                fail("plugin version must track the recorded upstream version", errors)

    if marketplace_path.is_file():
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        if marketplace.get("name") != "pstack-codex":
            fail("marketplace name must be pstack-codex", errors)
        entries = marketplace.get("plugins", [])
        if len(entries) != 1 or entries[0].get("name") != "pstack-codex":
            fail("marketplace must contain exactly the pstack-codex entry", errors)
        elif entries[0].get("source", {}).get("path") != "./plugins/pstack-codex":
            fail("marketplace source path must be ./plugins/pstack-codex", errors)

    skill_files = sorted(SKILLS.glob("*/SKILL.md"))
    if len(skill_files) < 40:
        fail(f"expected at least 40 top-level skills, found {len(skill_files)}", errors)
    seen: set[str] = set()
    for skill_file in skill_files:
        values = parse_frontmatter(skill_file, errors)
        name = values.get("name", "")
        if name and not NAME_RE.match(name):
            fail(f"{skill_file.relative_to(ROOT)}: invalid skill name {name!r}", errors)
        if name and name != skill_file.parent.name:
            fail(
                f"{skill_file.relative_to(ROOT)}: name {name!r} does not match directory",
                errors,
            )
        if name in seen:
            fail(f"duplicate skill name: {name}", errors)
        seen.add(name)

        agent_config = skill_file.parent / "agents" / "openai.yaml"
        if agent_config.is_file():
            config = agent_config.read_text(encoding="utf-8")
            for required in (
                "interface:\n",
                "  display_name:",
                "  short_description:",
                "  default_prompt:",
                "policy:\n",
                "  allow_implicit_invocation: false",
            ):
                if required not in config:
                    fail(
                        f"{agent_config.relative_to(ROOT)}: missing {required.strip()!r}",
                        errors,
                    )
            if f"${name}" not in config:
                fail(
                    f"{agent_config.relative_to(ROOT)}: default prompt must invoke ${name}",
                    errors,
                )

    known_skill_pattern = re.compile(
        r"(?<![A-Za-z0-9_.-])/((?:" + "|".join(map(re.escape, sorted(seen, key=len, reverse=True))) + r"))(?![A-Za-z0-9_-])"
    )
    for path in sorted(PLUGIN.rglob("*")):
        if (
            not path.is_file()
            or path.suffix not in {".md", ".sh"}
            or "node_modules" in path.parts
        ):
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, label in BANNED_RUNTIME.items():
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                fail(f"{path.relative_to(ROOT)}:{line}: {label}: {match.group(0)!r}", errors)
        match = known_skill_pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            fail(
                f"{path.relative_to(ROOT)}:{line}: slash shim remains for skill {match.group(1)!r}",
                errors,
            )
        if path.suffix == ".md":
            validate_links(path, errors)

    for forbidden in (
        SKILLS / "grokbot" / "make-bot-ui",
        PLUGIN / "agents",
        PLUGIN / "commands",
        PLUGIN / ".codex-plugin" / "prompts",
    ):
        if forbidden.exists():
            fail(f"non-native compatibility artifact exists: {forbidden.relative_to(ROOT)}", errors)

    runtime = SKILLS / "poteto-mode" / "references" / "codex-runtime.md"
    if not runtime.is_file():
        fail("missing native Codex runtime contract", errors)

    panel_roster = (
        "`gpt-5.6-sol` at `xhigh`, `gpt-5.6-terra` at `xhigh`, "
        "`gpt-5.6-luna` at `xhigh`, `gpt-5.5` at `xhigh`"
    )
    for relative in (
        "architect/SKILL.md",
        "arena/SKILL.md",
        "how/SKILL.md",
    ):
        path = SKILLS / relative
        if path.is_file() and panel_roster not in path.read_text(encoding="utf-8"):
            fail(f"{path.relative_to(ROOT)}: four-family panel roster drifted", errors)

    interrogate = SKILLS / "interrogate" / "SKILL.md"
    if interrogate.is_file():
        interrogate_text = interrogate.read_text(encoding="utf-8")
        for model in (
            "`gpt-5.6-sol` at `xhigh`",
            "`gpt-5.6-terra` at `xhigh`",
            "`gpt-5.6-luna` at `xhigh`",
            "`gpt-5.5` at `xhigh`",
        ):
            if model not in interrogate_text:
                fail(
                    f"{interrogate.relative_to(ROOT)}: panel is missing {model}",
                    errors,
                )

    stale_effort = re.compile(r"`gpt-5\.6-(?:sol|luna)` at `(?:max|high)`")
    for path in sorted(PLUGIN.rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".mjs"}:
            continue
        match = stale_effort.search(path.read_text(encoding="utf-8"))
        if match:
            fail(
                f"{path.relative_to(ROOT)}: stale model effort {match.group(0)!r}",
                errors,
            )

    if errors:
        print("validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"validated pstack-codex: {len(skill_files)} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
