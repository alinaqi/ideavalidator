# ideavalidator

Validate a business idea in detail, toward **profitable from day one**: problem → market → ICP and
beachhead vertical → SWOT → willingness to pay → day-one economics → risk map → GO/PIVOT/KILL memo.
Gemini (Google-Search-grounded) does the desk research; deterministic gates and PDLC evidence-quality
labels keep it honest; a Claude Code skill (`/ideavalidator`) interviews you and runs the whole thing.

## Install (2 minutes)

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
.venv/bin/python -m pipeline.cli council --idea ideas/my-idea.md    # sounding board (optional)
.venv/bin/python -m pipeline.cli report --idea my-idea              # decision memo
.venv/bin/python -m pipeline.cli stages                             # stage list + dependencies
```

Outputs land in `runs/<slug>/<stage>.json|.md`. Stages: frame → problem → market → icp → swot →
wtp → economics → risks → decision. `--stages a,b` runs a subset (dependencies must exist);
`--deep` uses Gemini Deep Research; `--stop-on-kill` halts at the first KILL gate.

## Development

```bash
pytest --cov=pipeline --cov-report=term-missing      # 80% minimum coverage
```

Code limits: ≤20 lines per function, ≤3 parameters, nesting ≤2, ≤200 lines and ≤10 functions per
file. Tests are written first (RED → GREEN → VALIDATE).

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
