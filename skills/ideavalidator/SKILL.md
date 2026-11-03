---
name: ideavalidator
description: >-
  Validate a business or product idea end to end — problem, market, ICP and beachhead vertical, SWOT,
  willingness to pay, day-one profitability, risk map and a GO/PIVOT/KILL memo. MCP-first: runs on the
  hosted Idea Validator server (your own Palgu key) when its tools are available, else falls back to the
  local CLI. Use whenever the user has a startup/business/product idea, asks "is this a good idea", wants
  market research, an ICP, pricing guidance, or a go/no-go. Interviews the user first if the brief is thin.
---

# Idea Validator

Validate an idea toward **profitable from day one**. Non-negotiable principles (enforce them, never soften):
- **Desk research is never validation.** A positive result justifies **GO → real-world tests** (interviews,
  pre-sales, paid pilots), never **GO → build**.
- **Behaviour beats stated intent.** Money paid, workarounds built, tools switched > "I would use this".
- **One beachhead, one offer, one channel.** Profitable from day one = break-even reachable through a
  channel the founder already has, no paid acquisition, no outside capital.
- **No flattery.** Do not over-qualify the idea. Score it **as stated, for its stated ICP**; record bigger
  adjacent businesses separately, never as the original idea passing. Do not soften a KILL.

## Preferred path — the MCP tools (hosted server)

If the Idea Validator MCP tools are available (`palgu_status`, `palgu_login`, `validate_idea`,
`get_status`, `get_report`, `list_runs`, `cancel_run`), use them — the validation runs on the hosted
server on the user's own Palgu key.

1. **Sign in.** Call `palgu_status`. If not signed in, call `palgu_login` and show the user the approve
   URL and the code; tell them to approve at palgu.ai, then call `palgu_status` again until signed in.
   Never ask for or paste a raw key into the chat.
2. **Build the brief.** Interview the user only for what is missing (actor; job/problem in their words;
   current workaround + cost; why them; candidate verticals; money = value metric + price + a channel they
   already have; business model + success definition; day-one constraints). Accept "don't know" as UNKNOWN.
3. **Run it.** Call `validate_idea` with a one-sentence pitch (and the gathered context). Tell the user the
   run takes **20–40 minutes**. It returns a `run_id`.
4. **Poll sparingly.** Call `get_status(run_id)` and wait at least the returned `next_poll_seconds` between
   polls. Report each stage's GO/PIVOT/KILL verdict as it lands; never fabricate a result.
5. **Present.** When `state` is `done`, call `get_report(run_id)` and present the memo: overall verdict +
   per-stage table; strongest behavioural and contrary evidence with URLs; beachhead ICP, price anchors,
   break-even customer count and the reaching channel; the kill condition and the two-week test plan
   (day one must be a revenue-seeking action); what would change our mind; the self-validation flags.
   Keep it under ~400 words plus tables.
6. `list_runs` shows this account's runs across sessions; `cancel_run(run_id)` stops one.

## Fallback — the local CLI

If the MCP tools are not available, run the bundled pipeline. Resolve the repo root: use
`$CURSOR_PLUGIN_ROOT` or `$CLAUDE_PLUGIN_ROOT` if set and it contains `pipeline/cli.py`; else walk up from
this file to the directory containing `pipeline/cli.py`. Then:

```bash
cd "$ROOT" && .venv/bin/python -m pipeline.cli doctor        # no .venv → ./install.sh first
# key missing: tell the user to run  .venv/bin/python -m pipeline.cli palgu login  (or set GEMINI_API_KEY in .env)
.venv/bin/python -m pipeline.cli ingest --url <url> [--idea "<angle>"]   # if given a website
.venv/bin/python -m pipeline.cli run --idea ideas/<slug>.md              # 10 stages, ~20-40 min
.venv/bin/python -m pipeline.cli report --idea <slug> --format html      # memo (md|html|xlsx|pdf)
```
Never put a key anywhere except `.env`; never commit `.env` or `runs/`. Challenge the evidence before
presenting (open the strongest citations; flag any that do not say what is claimed).

## Recording the decision
Ask the user for GO / PIVOT / KILL / PARK, note it on the run, and (KILL/PARK) add a row to the kill log.
On GO, offer the real-world kit (Mom Test guide, 50-prospect outreach, pre-sale page + pricing, experiment
sheet) — only interviews, deposits and paid pilots count as validation.
