# ideavalidator

_This is the validation model [palgu.ai](https://palgu.ai) uses to validate specs._

Validate a business idea in detail, toward **profitable from day one**: problem → market → ICP and
beachhead vertical → SWOT → willingness to pay → day-one economics → risk map → GO/PIVOT/KILL memo.
Gemini (Google-Search-grounded) does the desk research; deterministic gates and PDLC evidence-quality
labels keep it honest; a Claude Code skill (`/ideavalidator`) interviews you and runs the whole thing.

## Install as a Claude Code plugin

```
/plugin marketplace add alinaqi/ideavalidator
/plugin install ideavalidator
```

Then run `cd` into the plugin directory once and `./install.sh` to create the Python venv and `.env`
(the skill orchestrates a Python pipeline, so it needs the venv and a `GEMINI_API_KEY`). The command
finds its home via `$CLAUDE_PLUGIN_ROOT` automatically. Add provider keys for the optional multi-model
sounding board in the same `.env` (any subset works).

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

## Validate a website URL

Point it at any business website and it extracts the context and runs the full cycle:

```bash
# validate the company's own business
.venv/bin/python -m pipeline.cli ingest --url https://zenloop.com --run
# validate a NEW idea for that company
.venv/bin/python -m pipeline.cli ingest --url https://zenloop.com --idea "a free survey creator" --run
```

In Claude Code this is just `/ideavalidator https://zenloop.com — a free survey creator`.

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
