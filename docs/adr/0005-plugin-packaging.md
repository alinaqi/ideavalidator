# 0005 - Package as an installable Claude Code plugin

**Status:** accepted
**Date:** 2026-11-01
**Spec:** .claude-plugin/plugin.json, .claude-plugin/marketplace.json, commands/ideavalidator.md
**Deciders:** Ali Shaheen, Claude

## Context

The tool was a research project that happened to contain a skill under `.claude/skills/`. To share
`/ideavalidator` cleanly, it needs the standard Claude Code plugin structure so others can add it with
`/plugin marketplace add` and `/plugin install`, without hand-copying files.

## Decision

- Add a plugin manifest (`.claude-plugin/plugin.json`) and a single-plugin marketplace
  (`.claude-plugin/marketplace.json`) at the repo root, so the whole repo is the plugin.
- Canonical skill lives at `skills/ideavalidator/SKILL.md` (the plugin convention); `commands/
  ideavalidator.md` defines the `/ideavalidator` slash command.
- The skill orchestrates the Python pipeline, so the plugin carries `pipeline/` and `install.sh`. The
  command resolves its home via `$CLAUDE_PLUGIN_ROOT` (set for installed plugins), then the
  install.sh-substituted path, then by walking up to the dir containing `pipeline/cli.py`. `install.sh`
  still creates the venv and `.env` and also installs the skill into `~/.claude/skills` for clone users.
- Both install paths are supported and documented: plugin (`/plugin …`) and clone + `install.sh`.

## Consequences

- Installable and discoverable as a plugin; no manual file copying.
- The Python venv + `GEMINI_API_KEY` step remains (the tool is not a pure prompt-skill); documented.
- One canonical skill file; `install.sh` reads from `skills/` to avoid drift between copies.

## Alternatives Considered

| Option | Why Not |
|--------|---------|
| Pure prompt-only skill (no Python) | Loses the deterministic gates, schemas, tests and reproducibility (ADR 0001) |
| Separate plugin-only repo | Would still need the pipeline; fragments one codebase into two |
| Keep clone + install.sh only | Not discoverable/installable via the plugin system |

## Links

- Related: 0001 (pipeline), 0002 (skill-in-repo), 0003 (sounding board), 0004 (flexible objectives)
