---
name: ideavalidator
description: Validate a business or product idea end to end — problem, market, ICP and beachhead vertical, SWOT, willingness to pay, day-one profitability, risk map and a GO/PIVOT/KILL memo — using Gemini-grounded desk research gated by the Palgu PDLC. Use whenever the user has a startup/business/product idea, asks "is this a good idea", wants market research, an ICP, pricing guidance, or a go/no-go. Interviews the user first if the brief is incomplete.
user-invocable: true
argument-hint: "<one-line idea> (optional; the skill will ask what it needs)"
---

# /ideavalidator — validate a business idea in detail

You are running the Idea Validator workflow. Resolve the repo root (`IDEAVALIDATOR_HOME`, the folder
that contains `pipeline/` and `install.sh`) in this order: (1) the `CLAUDE_PLUGIN_ROOT` environment
variable if it is set and contains `pipeline/cli.py` (set when installed as a plugin); (2) the literal
path `__IDEAVALIDATOR_HOME__` if `install.sh` substituted it (not still the placeholder); (3) otherwise
walk up from this skill file until you find the directory containing `pipeline/cli.py` (from
`skills/ideavalidator/` that is two levels up). Use that as `IDEAVALIDATOR_HOME`; every path below is
relative to it. Read `docs/WORKFLOW.md` there once per session before starting.

Principles you must enforce (from the workflow): desk research never validates; behaviour beats
stated intent; one beachhead, one offer, one channel; profitable from day one means break-even is
reachable through channels the founder already has, with no paid acquisition and no outside capital.

## Step 0 — Environment check (always)

```bash
cd "$IDEAVALIDATOR_HOME" && .venv/bin/python -m pipeline.cli doctor
```
- No `.venv`: run `./install.sh` (creates the venv, installs deps, copies `.env.example`).
- Key missing: the easiest path is Palgu — tell the user to run `palgu login` (sign up at palgu.ai, approve the code) and the pipeline runs on that single key, no Gemini key needed. Otherwise ask for their Google AI Studio key and tell them to put it in `.env`
  as `GEMINI_API_KEY=...` (never paste a key into chat logs or files other than `.env`).
- If `doctor` passes, continue. Do not run the pipeline when it fails.

## Step 0b — URL ingestion (when given a website)

If the user gives a website URL (optionally with an angle, e.g. `typeform.com — a free survey creator`,
or `for typeform.com, a free survey creator`), do NOT run the manual interview. Instead build the brief
agentically:

```bash
cd "$IDEAVALIDATOR_HOME" && .venv/bin/python -m pipeline.cli ingest --url <url> [--idea "<angle>"]
```

This reads the site (Gemini url_context) + search and writes `ideas/<slug>.md`. With no angle it
validates the company's own business; with an angle it validates that new idea FOR the company. Show the
user the generated pitch and thesis spine in two lines, then go straight to Step 2. Only ask follow-ups
if a MANDATORY field came back UNKNOWN.

## Step 1 — Intake interview (ask only what is missing)

Read `ideas/_template.md`. Compare it with what the user already said (the argument, pasted notes,
earlier conversation). Then ask for the gaps with `AskUserQuestion`, at most 4 questions per call,
two or three calls maximum. Mandatory fields; everything else may stay a hypothesis:

1. **Actor** — who exactly has the problem (role, company type/size, geography)?
2. **Job / problem in their words** — what are they trying to get done; what triggers it?
3. **Current workaround and its cost** — what do they do today; what does it cost in money or hours?
4. **Why us** — audience, access, data, domain or distribution the founder already has.
5. **Candidate verticals** — 3-8 segments they could start with (offer to let the research propose more).
6. **Money** — value metric guess, price guess, and the one channel they can reach buyers through today.
7. **Business model & success definition** — is this direct-sales SaaS, PLG/freemium, a directory/
   graph, a marketplace/network, usage/API, or a service? And what counts as success: cash now
   (services), a compounding/defensible product, a PLG/network, or venture-scale? If unsure, say so and
   let the `frame` stage classify it. This steers how every stage scores market size, WTP and economics
   (a PLG/graph model is judged on its funnel and paying fraction, not outbound sales). Also ask whether this is an EXISTING-market idea or an out-of-the-box NEW-market/innovation (set validation_mode: new_market). For new-market ideas the regime differs: absence of competitors/search volume/existing spend is expected, not a kill, and the test is a designed demand-creation experiment (pretotype, fake door, landing+waitlist, Wizard-of-Oz, pre-order), not finding people already paying.
8. **Day-one constraints** — monthly cost floor, founder hours per week, income target (optional).

Rules: accept "don't know" (record it as UNKNOWN; the research will try to fill it). Offer concrete
options where sensible (B2B/B2C, subscription/per-use/service, geography). Do not pitch or improve
the idea during intake. If the user clearly wants a quick pass, collect 1-4 and 6 only.

Write the brief to `ideas/<slug>.md` using the template headings verbatim (slug: lowercase,
hyphenated, ≤40 chars; the pipeline uses it as the run folder). Show the user the brief in two or
three lines and proceed; do not wait for approval unless they asked to review it.

## Step 2 — Run the pipeline

```bash
cd "$IDEAVALIDATOR_HOME" && .venv/bin/python -m pipeline.cli run --idea ideas/<slug>.md
```
- Full pass is nine stages, roughly 2-4 minutes each. Run it in the background and report each gate
  verdict as it appears (`runs/<slug>/<stage>.md`). Never fabricate a stage result while waiting.
- Use `--stop-on-kill` only if the user asked for a fast screen; by default run all stages so the
  memo shows the whole picture even for a killed idea.
- Use `--deep` (Gemini Deep Research, much slower) for `market` and `icp` when the user asks for
  depth or when a stage returned UNKNOWN.
- A stage can be rerun alone: `--stages wtp,economics,risks,decision` after the brief changes.
- `run` gathers **demand signals** first unless `--no-signals` is passed (see Step 2a).

## Step 2a — Demand signals (automatic, additive)

`run` begins by gathering demand signals (also runnable alone:
`.venv/bin/python -m pipeline.cli signals --idea ideas/<slug>.md`). It checks **search volume**
(DataForSEO — how the idea is actually searched) and **social validation** (Reddit via the official Reddit API with
Apify as fallback, X via xAI Grok — is the problem discussed?), writing `runs/<slug>/signals.json` + `signals.md`. Every source is
best-effort: a missing key or dead source yields no signal and no error. Present signals add a small,
capped bonus (≤+0.5) to the market/problem/decision verdicts; **absent signals never penalise an idea**
— genuinely new markets often have none. `doctor` lists which signal sources are configured. Surface the
numbers to the user (search volume per keyword, notable threads) as supporting, not deciding, evidence.

## Step 2c — Category, business model & USP (automatic, framing)

The `classify` stage runs right after `frame`. It names the business **category** from the built-in taxonomy so later stages compare to the correct incumbents (not look-alikes from another category — e.g. a connector that gives an existing agent a phone is NOT a standalone calling app), lists candidate **business models** (incl. a model-innovation option), fills the **Business Model Canvas**, and writes a **USP** + a value-positioning map. It is framing only and never changes the verdict. Surface the category, chosen model, USP and the corrected incumbent set to the user.

## Step 2b — Convene the sounding board (multi-model debate)

Run it after `risks` has finished (or right after `frame` if the brief is thin and the user wants the
idea enriched before paying for research):

```bash
cd "$IDEAVALIDATOR_HOME" && .venv/bin/python -m pipeline.cli council --idea ideas/<slug>.md --rounds 1
```
It needs provider keys (`doctor` lists callable council models; any subset works). Six framework-based
personas on different models debate, a Red Team attacks the consensus, a Chair synthesises. Read
`runs/<slug>/council.md` and surface to the user: the votes, the 3-5 real disagreements, the Red Team
position and whether the Chair thinks it exposes a real gap, the **enriched idea** (each element marked
EVIDENCED or HYPOTHESIS) and the **claims to verify**. Offer to fold accepted enrichments into the
brief under `## Evidence updates` and rerun `icp,wtp,economics,risks` before `decision` (the decision
stage reads `council.json` automatically when it exists). Board output is opinion, not evidence: it
never changes a gate on its own.

## Step 3 — Challenge the evidence before presenting it

For every finished stage read `runs/<slug>/<stage>.json` and:
1. Spot-check **three of the strongest evidence items** per stage by opening their `source_url`
   (WebFetch). Mark any that do not say what is claimed as INVALID in your summary and lower your
   confidence in the stage; mention it to the user explicitly.
2. Check the `triangulation` block: a STRONG label with only STATED items is still weak.
3. Compare the brief's assumptions with the stage's `contrary_evidence` / unknowns; call out every
   place the research contradicts the founder.
4. Look for the anti-patterns in `docs/WORKFLOW.md` §10 (request counts as demand, top-down TAM,
   "what would you pay", single design partner, tarpits).

## Step 3b — Export the report (if a format was requested)

Default output is the markdown memo. If the user asked for a format (`-output`/`--format`
`html|pdf|xlsx|md`), export it:

```bash
.venv/bin/python -m pipeline.cli report --idea <slug> --format <fmt> [--dest <dir>]
```
`html` and `pdf` include inline SVG charts and a Gemini-generated hero image; `pdf` renders via headless
Chrome or weasyprint, falling back to `report.html` if neither is present. By default the file is written
into `runs/<slug>/`; pass `--dest <dir>` (alias `--out-dir`) to save it elsewhere. `html`/`pdf` also render the Business Model Canvas (9-block grid) and the value-positioning map when the classify stage ran. Tell the user the file path.

## Step 3c — Self-validation layer (don't over-qualify)

`run` ends by writing `runs/<slug>/selfcheck.{md,json}` (also: `pipeline.cli selfcheck --idea ideas/<slug>.md`). It audits the pipeline's OWN output for: **over-qualification / off-ICP** (a beachhead or category the brief never named — the idea quietly morphing into a bigger business), **score inconsistencies** (a kill_flag or score that contradicts the stage's own numbers), **weak KILLs** (a KILL on one low-directness source), and **unreachable citations** (fabricated URLs). Treat every flag as must-verify: open the cited sources, and **rerun** any stage whose score contradicts its content before trusting it. Never report an over-qualified/adjacent business as the original idea passing — the scored subject is the founder's idea and ICP as stated.

## Step 4 — Present the result

After all stages: `.venv/bin/python -m pipeline.cli report --idea <slug>`. Present, in this order:
- Overall verdict and the per-stage table (one line each: verdict, score, why).
- The three strongest behavioural evidence items and the three strongest contrary items, with URLs.
- The sounding board's recommendation, where it disagreed with the desk research, and the top claims to verify.
- Beachhead ICP, price anchors, break-even customer count and the channel that reaches them.
- The bet record's kill condition and the two-week plan (day one must be a revenue-seeking action).
- What would change our mind.
- The self-validation flags (Step 3c) and what you did about them.
- Judge and present the idea AS STATED for its ICP. List any bigger/adjacent business separately as a DIFFERENT idea to validate on its own — never as the original idea passing.
Keep it under ~400 words plus tables; the full detail is in `runs/<slug>/`.

## Step 5 — Record the decision and hand over

1. Ask the user for their decision (GO to real-world tests / PIVOT: what changes / KILL / PARK).
2. Append a `## Founder decision` section to `runs/<slug>/decision.md` with the decision, date,
   one-paragraph reasoning, and any gate override (an override must state why).
3. KILL or PARK: add a row to `docs/KILL_LOG.md` (date, slug, verdict, killing evidence, revisit trigger).
4. GO: offer to draft the real-world kit from the stage outputs: Mom Test interview guide
   (`problem` stage), 50-prospect list plan and outreach message (`icp` + positioning draft),
   pre-sale offer page and pricing script (`wtp`), and the pre-registered experiment sheet (`risks`).
   Remind them that only interviews, deposits and paid pilots count as validation.
5. PIVOT: update `ideas/<slug>.md` (append `## Evidence updates` with what changed) and rerun the
   affected stages.

## Follow-up runs

When the user returns with interview or pre-sale results, append them to the brief under
`## Evidence updates` labelled BEHAVIOR or STATED, then rerun `wtp,economics,risks,decision`.
Compare the new gates with the old run (copy the old files to `runs/<slug>/archive/` first).

## Guardrails

- Never put the API key anywhere except `.env`. Never commit `.env` or `runs/`.
- Do not soften a KILL. Do not turn an UNKNOWN into a verdict; rerun or research manually.
- Do not generate interview answers, survey responses or "synthetic customers" as evidence
  (see `docs/FRAMEWORKS.md` §4). LLM output is for hypotheses, guides and desk evidence only.
- Keep code changes to `pipeline/` under the repo's TDD and size rules (see README).
