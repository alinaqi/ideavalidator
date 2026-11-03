<div align="center">

# ideavalidator

**Validate a business idea end to end — toward _profitable from day one_ — from inside Claude Code.**

Problem → market → ICP & beachhead → SWOT → willingness to pay → day-one economics → risk map → a GO / PIVOT / KILL memo, backed by grounded research and deterministic, evidence-quality gates.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A63D2.svg)](https://docs.claude.com/en/docs/claude-code)
[![Tests](https://img.shields.io/badge/tests-224%20passing-brightgreen.svg)](#development)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen.svg)](#development)

<sub>The validation model <a href="https://palgu.ai">palgu.ai</a> uses to validate specs.</sub>

</div>

---

In Claude Code you just type `/ideavalidator <your idea or a website URL>`. It interviews you for only
what's missing, runs a ten-stage pipeline of **grounded** desk research (real source citations), keeps
contrary evidence and UNKNOWNs visible, and hands you a decision memo with a two-week real-world test
plan. It is built not to flatter: desk research can only justify **GO → test** (interviews, pre-sales,
paid pilots), never **GO → build**.

## Table of contents

- [Why ideavalidator](#why-ideavalidator)
- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [Using it well in Claude Code](#using-it-well-in-claude-code)
- [Configuration (keys)](#configuration-keys)
- [CLI reference](#cli-reference)
- [Output formats](#output-formats)
- [Advanced features](#advanced-features)
- [Development](#development)
- [Project layout](#project-layout)
- [License](#license)

## Why ideavalidator

- **Grounded, not guessed.** Every stage runs a search-grounded research pass and normalises each piece
  of evidence with PDLC quality labels (directness, behaviour-vs-stated, recency, source independence).
- **Deterministic gates.** GO / PIVOT / KILL comes from scored criteria, not vibes — kill flags and weak
  critical criteria force a KILL; the math is in [`pipeline/gates.py`](pipeline/gates.py).
- **Won't over-qualify.** It scores the idea **as stated, for your ICP**. A self-validation layer flags
  off-ICP drift, inconsistent scores, weak KILLs and unreachable (fabricated) citations.
- **Fits the business model.** PLG/freemium, marketplace, usage/API, services or direct-sales SaaS are
  each judged on their own terms (a PLG funnel isn't scored like outbound sales).
- **One key, or your own.** Sign in with Palgu to run on a single key, or bring your own `GEMINI_API_KEY`.
- **Agentic end to end.** It interviews, researches, spot-checks its own citations, and records your
  decision — you can walk away while it runs.

## Quick start

### 1. Install the Claude Code plugin

The repo is a self-hosted marketplace — no central registry needed. In Claude Code:

```
# one step (Claude Code 2.1.275+)
/plugin install ideavalidator --marketplace alinaqi/ideavalidator

# or two steps
/plugin marketplace add alinaqi/ideavalidator
/plugin install ideavalidator@ideavalidator
```

Terminal equivalent: `claude plugin marketplace add alinaqi/ideavalidator` then
`claude plugin install ideavalidator@ideavalidator`.

> **One-time setup (required).** Installing copies the plugin but does **not** run any setup script, and
> the pipeline needs a Python venv + a provider key. The skill handles it: the first time you run
> `/ideavalidator`, it detects there's no venv, runs `install.sh` in the plugin directory, and prompts
> you to sign in with Palgu or add a `GEMINI_API_KEY`. Update later with
> `/plugin marketplace update ideavalidator` (third-party marketplaces don't auto-update).

### 2. Pick a key path

**Easiest — sign in with Palgu (one key):**

```bash
.venv/bin/python -m pipeline.cli palgu login     # approve the code at palgu.ai (sign up there if new)
.venv/bin/python -m pipeline.cli palgu status    # who's signed in, on which plan
```

This mints a per-device key, saves it to `.env` as `PALGU_API_KEY`, and runs the **grounded** research
(real Google-Search citations via Palgu's `/v1/research`) + JSON structuring on Palgu's gateway — no
`GEMINI_API_KEY` needed. If the org runs out of budget the run prints a clear top-up message instead of a
silent empty result.

**Or bring your own Gemini key:**

```bash
git clone https://github.com/alinaqi/ideavalidator.git && cd ideavalidator
./install.sh                      # venv, deps, .env; installs the /ideavalidator skill globally
$EDITOR .env                      # GEMINI_API_KEY=... from https://aistudio.google.com/apikey
.venv/bin/python -m pipeline.cli doctor
```

If both keys are set, `PALGU_API_KEY` wins (single-key mode routes research + billing through Palgu);
set only `GEMINI_API_KEY` for a bring-your-own-key run. `doctor` shows the active provider.

### 3. Run it

From any directory in Claude Code:

```
/ideavalidator SMS waitlist that fills last-minute cancellations for dental clinics
```

It asks only for the missing brief fields, writes `ideas/<slug>.md`, runs the ten stages, spot-checks
citations, presents the memo, and records your decision. Prefer the terminal? See the [CLI](#cli-reference).

## How it works

Each stage runs a grounded research pass → schema-constrained JSON → evidence normalised with PDLC labels
→ a deterministic gate. **Kill flags and any critical criterion below 2 force KILL; mean ≥ 3.5 is GO;
otherwise PIVOT.** Present demand signals add a small capped bonus (≤ +0.5); absent signals never penalise.

| # | Stage | Question it answers |
|---|-------|---------------------|
| 1 | `frame` | Is this a solution-independent opportunity for a specific actor? (writes the fixed thesis spine) |
| 2 | `classify` | What **category** is this (so we compare to the right incumbents), which business models fit, + Business Model Canvas & USP |
| 3 | `problem` | Does the problem exist, recur, and already cost money or behaviour? |
| 4 | `market` | What do buyers do today, who competes, how big is the **reachable** market, what's shifting? |
| 5 | `icp` | Which narrow beachhead has the most urgent, best-funded, most reachable version? |
| 6 | `swot` | For that beachhead, where are we strong/weak — what to exploit or defend? |
| 7 | `wtp` | What do comparable buyers already pay, for which value metric, how to test it behaviourally? |
| 8 | `economics` | How many customers, at what price/CAC, make it profitable from month one? |
| 9 | `risks` | Which assumptions are important and weakly evidenced — what's the smallest test? |
| 10 | `decision` | GO / PIVOT / KILL, with kill conditions and the next two weeks of real-world tests |

`classify` feeds incumbent/model context into later stages but is excluded from the overall verdict.
GO means "go run the two-week real-world test plan," never "go build." Full procedure:
[`docs/WORKFLOW.md`](docs/WORKFLOW.md) · frameworks: [`docs/FRAMEWORKS.md`](docs/FRAMEWORKS.md).

## Using it well in Claude Code

The tool is **agentic** — you talk to it and it drives the whole pipeline. Three ways to start:

```
/ideavalidator a tool that turns website scans into a trust seal      # an idea in words
/ideavalidator https://typeform.com                                    # validate a company's own business
/ideavalidator https://typeform.com — a free survey creator            # a new idea FOR that company
/ideavalidator -help                                                  # show all options
```

**What it does end to end:** interviews you for only the missing brief fields → writes `ideas/<slug>.md`
→ runs the ten stages in the background and streams each gate verdict → gathers demand signals (search
volume + Reddit/X) → opens the strongest citations to spot-check them → runs the self-validation audit →
presents the memo → records your decision. It reports verdicts as they land and never fabricates a result
it hasn't computed.

**To get the most out of it:**

1. **Be specific about the ICP and the "why you".** Name the exact actor (role, company type, geography),
   what they do today, and the one channel you can already reach them through.
2. **State the business model and the market regime.** SaaS, PLG/freemium, marketplace, connector/
   action-layer, usage/API, or service — and whether it's an existing or new/emerging market. This
   changes how market size, pricing and economics are scored.
3. **Let it stay focused — it won't over-qualify.** It scores the idea as stated, for your ICP. Skim the
   **Self-validation** section of the memo (or `runs/<slug>/selfcheck.md`): it flags off-ICP drift,
   inconsistent scores, weak KILLs and unreachable citations — verify or rerun before you trust a verdict.
4. **Ask for the format you want.** Add `-output html|pdf|xlsx` (and `-dest <dir>` to choose where it
   saves). `html`/`pdf` include the Business Model Canvas, a value-positioning map and gate charts.
5. **Use the sounding board to enrich a thin idea.** "Convene the council" for a multi-model debate that
   surfaces disagreements and an enriched thesis (opinion, not evidence — it never moves a gate).
6. **Treat GO as "go run the two-week real-world test," not "go build."** Ask for the GO kit (interview
   guide, prospect list + outreach, pre-sale page + pricing, experiment sheet).
7. **Come back with results.** After interviews or pre-sales, tell it what happened; it appends them to
   the brief and reruns `wtp,economics,risks,decision` so you can compare against the first run.

## Configuration (keys)

You need **one** provider key — either sign in with Palgu (`palgu login`) or set `GEMINI_API_KEY` in
`.env`. Everything else is optional and degrades gracefully: a missing key just means that source is
skipped. `doctor` shows what's active.

| Key | Purpose | Required? |
|-----|---------|-----------|
| `PALGU_API_KEY` | Single-key mode: grounded research + structuring via Palgu (set by `palgu login`) | one of these two |
| `GEMINI_API_KEY` | Bring-your-own-key: grounded research + structuring via Gemini | one of these two |
| `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` | Demand signal: search-volume | optional |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USER_AGENT` | Demand signal: Reddit validation | optional |
| `APIFY_TOKEN` | Demand signal: Reddit fallback | optional |
| `XAI_API_KEY` | Demand signal: X/Twitter via Grok | optional |
| Council provider keys | Multi-model sounding board (any subset) | optional |

See [`.env.example`](.env.example) for the full list. Keys can live in `.env` or a `KEYS_FILE` it points to.

## CLI reference

```bash
cp ideas/_template.md ideas/my-idea.md && $EDITOR ideas/my-idea.md
.venv/bin/python -m pipeline.cli run     --idea ideas/my-idea.md   # all ten stages (~20–40 min)
.venv/bin/python -m pipeline.cli ingest  --url https://typeform.com --run   # build a brief from a site, then run
.venv/bin/python -m pipeline.cli signals --idea ideas/my-idea.md   # demand signals (also auto in run)
.venv/bin/python -m pipeline.cli council --idea ideas/my-idea.md   # sounding board (optional)
.venv/bin/python -m pipeline.cli selfcheck --idea ideas/my-idea.md # self-validation audit (also auto in run)
.venv/bin/python -m pipeline.cli report  --idea my-idea --format md # decision memo (--dest <dir> to save)
.venv/bin/python -m pipeline.cli stages                            # stage list + dependencies
.venv/bin/python -m pipeline.cli doctor                            # check keys, models, active provider
```

Outputs land in `runs/<slug>/<stage>.json|.md`. `--stages a,b` runs a subset (dependencies must exist);
`--deep` uses Gemini Deep Research; `--stop-on-kill` halts at the first KILL gate; `--no-signals` skips
the demand-signal step.

## Output formats

```bash
.venv/bin/python -m pipeline.cli report --idea <slug> --format md|html|xlsx|pdf [--dest <dir>]
```

`md` prints the memo; `html`/`pdf` include inline charts, the Business Model Canvas, a value-positioning
map and a hero image; `xlsx` is a gate + evidence workbook; `pdf` renders via headless Chrome or
weasyprint (falls back to html).

## Advanced features

<details>
<summary><strong>Demand signals</strong> (additive, never a penalty)</summary>

`run` first gathers demand signals (skip with `--no-signals`): **search volume** via DataForSEO and
**social validation** via the official Reddit API (Apify fallback) and xAI Grok (X). Present signals add a
small, capped bonus (≤ +0.5) to the market/problem/decision verdicts; **absent signals never penalise** —
new markets often have none. Every source is best-effort.
</details>

<details>
<summary><strong>Category &amp; business model</strong> (classify stage)</summary>

The `classify` stage names the business **category** from a built-in taxonomy (dev tools/API, AI
action-layer/connector, marketplace, vertical SaaS, …) so every downstream stage compares to the *right*
incumbents. It enumerates candidate **business models**, fills a **Business Model Canvas**, and writes a
**USP** + value-positioning map (rendered as visuals in `html`/`pdf`). It never changes the verdict.
</details>

<details>
<summary><strong>Self-validation</strong> (anti over-qualification)</summary>

After a run, `selfcheck` (automatic at the end of `run`) audits the pipeline's own output for
over-qualification / off-ICP drift, score/content inconsistencies, KILLs built on weak evidence, and
unreachable (fabricated) citations. Flags are advisory — verify or rerun. Bigger adjacent businesses are
recorded separately, never counted as the idea passing.
</details>

<details>
<summary><strong>Sounding board</strong> (multi-model debate)</summary>

Six personas, each anchored in named thinking frameworks (Cohen, Mom Test/JTBD, Sequoia Arc + 7 Powers,
Van Westendorp + Dunford, Dixon wedge + founding sales, Premortem/Inversion) and seated on different
models (GPT, Claude, Gemini, DeepSeek, Kimi, Grok, GLM, …) read the brief and the evidence ledger, debate
turn by turn, get attacked by a Red Team seat, and a Chair synthesises an **enriched idea**, the real
disagreements, claims to verify and a recommendation.

```bash
.venv/bin/python -m pipeline.cli council --idea ideas/my-idea.md --rounds 1
```
</details>

<details>
<summary><strong>Flexible to the business model</strong></summary>

Set `business_model` and `success_definition` in the brief (or let `frame` classify them). The objective
(`services_cash` / `compounding_product` / `plg_network` / `venture_scale` / default) reweights the gates:
a PLG/directory/network thesis is sized by its funnel and a small paying fraction of a large free base,
not as outbound per-customer sales, and isn't hard-killed on low per-user willingness-to-pay. Every stage
also refuses to silently re-scope the thesis, classifies competitors as substitute/complement/adjacent,
and runs a disconfirmation + source-grading check before any KILL-level blocker. See
[`docs/WORKFLOW.md`](docs/WORKFLOW.md) §1b.
</details>

## Development

```bash
pytest --cov=pipeline --cov-report=term-missing      # 80% minimum coverage (currently 97%)
```

Tests are written first (RED → GREEN → VALIDATE). Code limits: ≤ 20 lines per function, ≤ 3 parameters,
nesting ≤ 2, ≤ 200 lines and ≤ 10 functions per file. Architecture decisions are recorded in
[`docs/adr/`](docs/adr/); killed ideas in [`docs/KILL_LOG.md`](docs/KILL_LOG.md).

## Project layout

```
.claude/skills/      the /ideavalidator skill (install.sh copies it to ~/.claude/skills)
commands/            the /ideavalidator slash command
pipeline/            config, stages, prompts, gemini + palgu clients, evidence, gates, runner, report, cli,
                     providers (multi-model chat), council + council_io (sounding board), personas.json
pipeline/prompts/    one research prompt per stage (+ _common.md rules block)
pipeline/schemas/    JSON output schema per stage
ideas/               idea briefs (start from _template.md)
runs/                per-idea outputs (gitignored)
docs/                WORKFLOW.md, FRAMEWORKS.md, KILL_LOG.md, adr/
tests/               pytest suite with fake clients (no real network)
```

## License

MIT © 2026 Ali Naqi Shaheen. See [LICENSE](LICENSE).
