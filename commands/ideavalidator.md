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

## Instructions

1. **Resolve the home directory** `IDEAVALIDATOR_HOME` (the folder containing `pipeline/` and
   `install.sh`): use `$CLAUDE_PLUGIN_ROOT` if set and it contains `pipeline/cli.py`; otherwise the
   path `install.sh` wrote into the skill; otherwise walk up from the skill file to the dir holding
   `pipeline/cli.py`.
2. **Load the skill**: read `skills/ideavalidator/SKILL.md` under that home and follow it exactly. It
   owns the full workflow (environment check, intake interview, pipeline run, sounding board, citation
   spot-checks, decision memo, recording the decision).
3. **Environment**: run `cd "$IDEAVALIDATOR_HOME" && .venv/bin/python -m pipeline.cli doctor`. If there
   is no `.venv`, run `./install.sh` first. If `GEMINI_API_KEY` is missing, ask the user to put it in
   `$IDEAVALIDATOR_HOME/.env` (never paste a key into chat). Provider keys for the sounding board are
   optional (any subset works).
4. **Do the work** as the skill directs: interview only for missing brief fields (including business
   model, success definition and whether it is an existing-market or out-of-the-box new-market idea),
   write `ideas/<slug>.md`, run the stages, convene the sounding board, challenge the evidence, present
   the memo, and record the founder's decision.
5. **Tell the user** where the outputs are (`runs/<slug>/`) and what the verdict and next test are.

## Example

User: `/ideavalidator a tool that turns security scan results into a trust seal for small SaaS`

Output: an interview for the missing brief fields, then a nine-stage validated run with a GO/PIVOT/KILL
memo, a sounding-board debate, and a two-week real-world test plan in `runs/<slug>/`.
