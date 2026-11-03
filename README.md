# ideavalidator

_This is the validation model [palgu.ai](https://palgu.ai) uses to validate specs._

Validate a business idea in detail, toward **profitable from day one**: problem → market → ICP and
beachhead vertical → SWOT → willingness to pay → day-one economics → risk map → GO/PIVOT/KILL memo.
Gemini (Google-Search-grounded) does the desk research; deterministic gates and PDLC evidence-quality
labels keep it honest; a Claude Code skill (`/ideavalidator`) interviews you and runs the whole thing.

## Install as a Claude Code plugin

The repo is a self-hosted marketplace (no central registry needed). In Claude Code:

```
# one step (Claude Code 2.1.275+)
/plugin install ideavalidator --marketplace alinaqi/ideavalidator

# or two steps
/plugin marketplace add alinaqi/ideavalidator
/plugin install ideavalidator@ideavalidator
```

Terminal equivalents: `claude plugin marketplace add alinaqi/ideavalidator` then
`claude plugin install ideavalidator@ideavalidator`.

**One-time setup after install (required).** Installing copies the plugin but does **not** run any setup
script, and the pipeline needs a Python venv + a `GEMINI_API_KEY`. The skill handles this for you: the
first time you run `/ideavalidator`, its environment check sees there's no venv and runs `install.sh`
in the plugin directory (found via `$CLAUDE_PLUGIN_ROOT`), then asks you to put
`GEMINI_API_KEY=...` in that directory's `.env`. Add any optional provider keys (demand signals,
sounding board) to the same `.env` — any subset works, missing keys are just skipped. New versions:
`/plugin marketplace update ideavalidator` (third-party marketplaces don't auto-update).

> If you'd rather not depend on the plugin cache, the **install from source** path below is the most
> reliable — it clones the repo and installs the `/ideavalidator` skill globally.

## Sign in with Palgu (one key, no setup)

Don't want to collect a Gemini key (and optional provider keys)? Sign up with Palgu and run on a
single key — the same device sign-in [mixture-of-models](https://github.com/alinaqi/mixture-of-models-claude-mod) uses:

```bash
.venv/bin/python -m pipeline.cli palgu login     # opens a code to approve at palgu.ai (sign up there if new)
.venv/bin/python -m pipeline.cli palgu status    # who is signed in, on which plan
```

It mints a per-device key, saves it to `.env` as `PALGU_API_KEY`, and the pipeline then runs the
**grounded** research (real Google-Search citations via Palgu's `/v1/research`) + JSON structuring on
Palgu's gateway — no `GEMINI_API_KEY` needed. If both keys are set, the `PALGU_API_KEY` wins (single-key
mode: research and billing route through Palgu); set only `GEMINI_API_KEY` for a bring-your-own-key run.
Notes: report hero images aren't on Palgu yet, so HTML/PDF imagery stays Gemini-only; and the
demand-signal data APIs (DataForSEO/Reddit) aren't model calls, so they stay optional separate keys.
If the Palgu org runs out of budget, the run prints a clear top-up-at-palgu.ai message instead of a
silent empty result. `doctor` shows the active provider.

## Install from source (2 minutes)

```bash
git clone https://github.com/alinaqi/ideavalidator.git && cd ideavalidator
./install.sh                      # venv, deps, .env, installs the /ideavalidator skill globally
$EDITOR .env                      # GEMINI_API_KEY=... from https://aistudio.google.com/apikey
.venv/bin/python -m pipeline.cli doctor
```

Then in Claude Code, from any directory:

```
/ideavalidator SMS waitlist that fills last-minute cancellations for dental clinics
```

The skill asks only for what the brief is missing (actor, job, current workaround, why you, candidate
verticals, price and channel guess, cost floor), writes `ideas/<slug>.md`, runs the nine stages,
spot-checks citations, presents the memo and records your decision. Without Claude Code, use the CLI
below.

- **Start here:** `docs/WORKFLOW.md` — the procedure we follow for every idea.
- **Frameworks:** `docs/FRAMEWORKS.md` — which idea/validation frameworks we use and when.
- **Decisions:** `docs/adr/` — architecture decision records.
- **Killed ideas:** `docs/KILL_LOG.md`.

## Using it well in Claude Code

The tool is **agentic** — you talk to it in Claude Code and it drives the whole pipeline for you. Three
ways to start:

```
/ideavalidator a tool that turns website scans into a trust seal      # an idea in words
/ideavalidator https://typeform.com                                    # validate a company's own business
/ideavalidator https://typeform.com — a free survey creator            # a new idea FOR that company
/ideavalidator -help                                                  # show all options
```

**What Claude Code does for you, end to end:** interviews you for only the missing brief fields → writes
`ideas/<slug>.md` → runs the ten stages in the background and streams each gate verdict → gathers demand
signals (search volume + Reddit/X) → opens the strongest citations to spot-check them → runs the
self-validation audit → presents the memo → records your decision. You can walk away while it runs; it
reports verdicts as they land and never fabricates a result it hasn't computed.

**To get the most out of it:**

1. **Be specific about the ICP and the "why you".** Name the exact actor (role, company type, geography),
   what they do today, and the one channel you can already reach them through. The more real the brief,
   the less the research has to guess.
2. **State the business model and the market regime.** Say whether it's direct-sales SaaS, PLG/freemium,
   a marketplace, a connector/action-layer, usage/API, or a service — and whether it's an existing market
   or a new/emerging one. This changes how market size, pricing and economics are scored (a PLG/network is
   judged on its funnel, not outbound sales; a new market isn't killed for lacking competitors).
3. **Let it stay focused — it won't over-qualify.** It scores the idea **as stated, for your ICP**. If the
   honest answer is PIVOT/KILL it says so, and any "this is bigger as X" goes in `adjacent_opportunities`
   as a *separate* idea. After each run, skim the **Self-validation** section of the memo (or
   `runs/<slug>/selfcheck.md`): it flags off-ICP drift, inconsistent scores, weak KILLs and unreachable
   citations — verify or ask it to rerun those stages before you trust the verdict.
4. **Ask for the format you want.** Add `-output html|pdf|xlsx` (and `-dest <dir>` to choose where it
   saves). `html`/`pdf` include the Business Model Canvas, a value-positioning map and gate charts — the
   best way to read a full result.
5. **Use the sounding board to enrich a thin idea.** Ask it to "convene the council" for a multi-model
   debate that surfaces disagreements and an enriched thesis (opinion, not evidence — it never moves a gate).
6. **Treat GO as "go run the two-week real-world test," not "go build."** Ask for the GO kit (interview
   guide, prospect list + outreach, pre-sale page + pricing, experiment sheet). Only interviews, deposits
   and paid pilots count as validation.
7. **Come back with results.** After interviews or pre-sales, tell it what happened; it appends them to the
   brief and reruns `wtp,economics,risks,decision` so you can compare against the first run.

**Keys:** `GEMINI_API_KEY` is required (set it in `.env`). The demand-signal sources (DataForSEO, Reddit,
Apify, xAI) and the sounding-board models are all optional — add any subset to `.env` or a `KEYS_FILE`;
`doctor` shows what's active. Nothing breaks if a key is missing — that source is simply skipped.

## Validate a website URL

Point it at any business website and it extracts the context and runs the full cycle:

```bash
# validate the company's own business
.venv/bin/python -m pipeline.cli ingest --url https://typeform.com --run
# validate a NEW idea for that company
.venv/bin/python -m pipeline.cli ingest --url https://typeform.com --idea "a free survey creator" --run
```

In Claude Code this is just `/ideavalidator https://typeform.com — a free survey creator`.

## Output formats

```bash
.venv/bin/python -m pipeline.cli report --idea <slug> --format md|html|xlsx|pdf
```
`md` prints the memo; `html`/`pdf` include inline charts and a Gemini-generated hero image; `xlsx` is a
gate + evidence workbook; `pdf` renders via headless Chrome or weasyprint (falls back to html).

## Sounding board (multi-model debate)

Six personas, each anchored in named thinking frameworks (Cohen, Mom Test/JTBD, Sequoia Arc + 7 Powers,
Van Westendorp + Dunford, Dixon wedge + founding sales, Premortem/Inversion) and seated on different
models (GPT, Claude, Gemini, DeepSeek, Kimi, Grok, GLM, Cerebras, Groq, MiniMax) read the brief and the
evidence ledger, debate turn by turn, get attacked by a Red Team seat, and a Chair synthesises an
**enriched idea**, the real disagreements, claims to verify and a recommendation. Pattern adapted from
eduBITES soundingBoard.

```bash
# keys: point KEYS_FILE in .env at any env file with provider keys, or set them in .env (any subset works)
.venv/bin/python -m pipeline.cli council --idea ideas/my-idea.md --rounds 1
```

## CLI

```bash
cp ideas/_template.md ideas/my-idea.md && $EDITOR ideas/my-idea.md
.venv/bin/python -m pipeline.cli run --idea ideas/my-idea.md        # all nine stages (~20-40 min)
.venv/bin/python -m pipeline.cli signals --idea ideas/my-idea.md    # demand signals (also auto in run)
.venv/bin/python -m pipeline.cli council --idea ideas/my-idea.md    # sounding board (optional)
.venv/bin/python -m pipeline.cli report --idea my-idea --format md  # decision memo (--dest <dir> to save)
.venv/bin/python -m pipeline.cli stages                             # stage list + dependencies
```

Outputs land in `runs/<slug>/<stage>.json|.md`. Stages: frame → classify → problem → market → icp → swot → wtp → economics → risks → decision. `--stages a,b` runs a subset (dependencies must exist);
`--deep` uses Gemini Deep Research; `--stop-on-kill` halts at the first KILL gate.

## Self-validation (anti over-qualification)

After a run, a self-validation layer (`pipeline.cli selfcheck`, and automatically at the end of `run`) audits the pipeline's own output for over-qualification / off-ICP drift (the idea quietly becoming a bigger business the brief never described), score/﻿content inconsistencies, KILLs built on weak evidence, and unreachable (fabricated) citations. Flags are advisory — verify or rerun. The validator scores the idea **as stated, for its stated ICP**; bigger adjacent businesses are recorded separately, never counted as the idea passing.

## Category & business model

The `classify` stage (right after `frame`) names the business **category** from a built-in taxonomy (dev tools/API, AI action-layer/connector, marketplace, vertical SaaS, …) so every downstream stage compares to the *right* incumbents — not look-alikes from another category. It enumerates the category's candidate **business models** (so business-model innovation is explicit), fills a **Business Model Canvas**, and writes a **USP** + value-positioning map. `html`/`pdf` reports render the canvas and positioning map as visuals. `classify` is framing only — it never changes the GO/PIVOT/KILL verdict.

## Demand signals

`run` first gathers demand signals (skip with `--no-signals`): **search volume** via DataForSEO (how the
idea is searched) and **social validation** via the official Reddit API (Apify fallback) and xAI Grok (X). Present signals add a
small, capped bonus (≤+0.5) to the market/problem/decision verdicts; **absent signals never penalise** an
idea — new markets often have none. Every source is best-effort, so missing keys just mean no signal.
Configure `DATAFORSEO_LOGIN`/`DATAFORSEO_PASSWORD`, `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`/`REDDIT_USER_AGENT`, `APIFY_TOKEN`, `XAI_API_KEY` (see `.env.example`);
`doctor` lists which are active.

## Development

```bash
pytest --cov=pipeline --cov-report=term-missing      # 80% minimum coverage
```

Code limits: ≤20 lines per function, ≤3 parameters, nesting ≤2, ≤200 lines and ≤10 functions per
file. Tests are written first (RED → GREEN → VALIDATE).

## Flexible to the business model

Set `business_model` and `success_definition` in the brief (or let `frame` classify them). The objective
(`services_cash` / `compounding_product` / `plg_network` / `venture_scale` / default) reweights the gates:
a PLG/directory/network thesis is sized by its funnel and a small paying fraction of a large free base,
not as outbound per-customer sales, and is not hard-killed on low per-user willingness-to-pay. Every stage
also refuses to silently re-scope the thesis, classifies competitors as substitute/complement/adjacent,
and runs a disconfirmation + source-grading check before any KILL-level blocker. See `docs/WORKFLOW.md` §1b.

## How it judges

Each stage: grounded research pass → schema-constrained JSON → evidence normalised with PDLC labels
(directness, behaviour vs stated, recency, source independence) → gate. Kill flags and critical
criteria below 2 force KILL; mean ≥3.5 is GO; otherwise PIVOT. GO means "go run the two-week
real-world test plan" (interviews, pre-sales, paid pilots), never "go build". Details: `docs/WORKFLOW.md`.

## Layout

```
.claude/skills/      the /ideavalidator skill (install.sh copies it to ~/.claude/skills)
pipeline/            config, stages, prompts, gemini client, evidence, gates, runner, report, cli,
                     providers (multi-model chat), council + council_io (sounding board), personas.json
pipeline/prompts/    one research prompt per stage (+ _common.md rules block)
pipeline/schemas/    JSON output schema per stage
ideas/               idea briefs (start from _template.md)
runs/                per-idea outputs (gitignored)
docs/                WORKFLOW.md, FRAMEWORKS.md, KILL_LOG.md, adr/
tests/               pytest suite with fake Gemini client
```

## License

MIT © 2026 Ali Naqi Shaheen. See [LICENSE](LICENSE).
