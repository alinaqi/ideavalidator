---
description: Validate a business or product idea end to end (problem, market, ICP, SWOT, willingness to pay, day-one economics, risk map, GO/PIVOT/KILL) via Gemini-grounded research, PDLC gates and a multi-model sounding board.
argument-hint: "<one-line idea> (optional; it will ask what it needs)"
---

# /ideavalidator — validate a business idea in detail

Validate the idea the user gives (or asks about) through the Idea Validator pipeline and sounding board.

## Usage

```
/ideavalidator <your idea in one line>
```

## Modes

- **Idea text:** `/ideavalidator a tool that turns scans into a trust seal` — interview + validate.
- **Website URL:** `/ideavalidator https://zenloop.com` — ingest the site and validate the company's
  own business. `/ideavalidator https://zenloop.com — a free survey creator` (or `for zenloop.com, a
  free survey creator`) — validate that NEW idea for that company, using the site as context/why-us.
- **Output:** add `-output html|pdf|xlsx|md` (alias `--format`) to export the report; html/pdf include
  Gemini-generated imagery and inline charts. Default is the markdown memo. Add `-dest <dir>` (alias
  `--out-dir`) to save the exported file somewhere other than the run folder.
- **Demand signals:** every run automatically checks how the idea is searched (DataForSEO search
  volume) and whether people discuss the problem on Reddit/X (Apify + xAI Grok). Present signals add a
  small, capped bonus to market/problem/decision; **absent signals never penalise** the idea. Add
  `--no-signals` to skip, or run them alone with `pipeline.cli signals --idea ideas/<slug>.md`.
- **Help:** `/ideavalidator -help` — show this usage and stop.

## Instructions

1. **Resolve the home directory** `IDEAVALIDATOR_HOME` (the folder containing `pipeline/` and
   `install.sh`): use `$CLAUDE_PLUGIN_ROOT` if set and it contains `pipeline/cli.py`; otherwise the
   path `install.sh` wrote into the skill; otherwise walk up from the skill file to the dir holding
   `pipeline/cli.py`.
2. **Help / parse the argument**: if it is `-help`/`--help`/`help`, print the Modes block above and
   stop. Detect a URL (http/https or a bare domain like `zenloop.com`) and any angle after `—`, `-`,
   `:` or `for <url>,`. Detect an output format from `-output`/`--output`/`--format`.
3. **If a URL was given**, build the brief agentically first:
   `cd "$IDEAVALIDATOR_HOME" && .venv/bin/python -m pipeline.cli ingest --url <url> [--idea "<angle>"]`.
   Read the generated `ideas/<slug>.md`, show the user its pitch and thesis spine in two lines, and skip
   the interview unless a MANDATORY field is UNKNOWN (then ask only those).
4. **Load the skill**: read `skills/ideavalidator/SKILL.md` and follow it for the full workflow
   (environment check, pipeline run incl. the concrete willingness-to-pay heuristic, sounding board,
   citation spot-checks, decision memo, recording the decision). Run it fully agentically.
3. **Environment**: run `cd "$IDEAVALIDATOR_HOME" && .venv/bin/python -m pipeline.cli doctor`. If there
   is no `.venv`, run `./install.sh` first. If `GEMINI_API_KEY` is missing, ask the user to put it in
   `$IDEAVALIDATOR_HOME/.env` (never paste a key into chat). Provider keys for the sounding board are
   optional (any subset works).
4. **Do the work** as the skill directs: interview only for missing brief fields (including business
   model, success definition and whether it is an existing-market or out-of-the-box new-market idea),
   write `ideas/<slug>.md`, run the stages, convene the sounding board, challenge the evidence, present
   the memo, and record the founder's decision.
6. **Export** if a format was requested:
   `.venv/bin/python -m pipeline.cli report --idea <slug> --format <fmt>` (html/pdf embed imagery).
   Add `--dest <dir>` if the user named where to save it.
7. **Tell the user** the verdict, the next real-world test, and where outputs are (`runs/<slug>/` and any
   exported `report.<ext>`).

## Example

User: `/ideavalidator a tool that turns security scan results into a trust seal for small SaaS`

Output: an interview for the missing brief fields, then a nine-stage validated run with a GO/PIVOT/KILL
memo, a sounding-board debate, and a two-week real-world test plan in `runs/<slug>/`.
