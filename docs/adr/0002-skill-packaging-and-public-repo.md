# 0002 - Package as a Claude Code skill in a public repository

**Status:** accepted
**Date:** 2026-10-31
**Spec:** .claude/skills/ideavalidator/SKILL.md, install.sh
**Deciders:** founder (Ali), Claude Code

## Context

The workflow must be runnable at any time, by the founder and by people they share it with, without
re-explaining the procedure. Claude Code skills are the natural entry point: they can interview the
user, run the CLI, open cited URLs to challenge evidence, and record decisions.

## Decision

- Ship the skill **inside the repo** at `.claude/skills/ideavalidator/SKILL.md` so it is auto-discovered
  when working in a clone, and let `install.sh` copy it to `~/.claude/skills/` with the repo path
  substituted for `__IDEAVALIDATOR_HOME__` so it also works from any directory.
- The skill owns the human loop (intake interview via `AskUserQuestion`, citation spot-checks, founder
  decision, kill log); the Python pipeline owns the deterministic parts (prompts, schemas, gates, files).
- Add `pipeline.cli doctor` so the skill can verify setup before spending API calls.
- Publish at github.com/alinaqi/ideavalidator (public). Secrets stay in `.env` (ignored); run outputs
  stay in `runs/` (ignored) because they may contain a founder's private idea.

## Consequences

- Anyone with a Gemini key can clone, run `./install.sh`, and use `/ideavalidator`.
- Idea briefs under `ideas/` are committed by default; users validating confidential ideas should keep
  their briefs in a private fork or add them to `.gitignore`.
- Preview model names are configurable via `.env` because they rotate.

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| Global-only skill, repo elsewhere | Simple | Clones would not get the skill automatically | Shareability |
| Claude Code plugin with marketplace | Discoverable | Heavier packaging; private marketplace needed | Overkill for now; can wrap later |
| Skill that embeds all logic (no Python) | No install | No deterministic gates, no tests, no reproducibility | Violates ADR 0001 |

## Links

- Supersedes: N/A
- Related: 0001, docs/WORKFLOW.md
