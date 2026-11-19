# 0014 - Fast requirements check endpoint (`POST /api/v1/requirements/check`)

**Status:** accepted
**Date:** 2026-11-19
**Spec:** srooter#2785 "Contract v1"; web/src/reqcheck*.rs, worker/req_check.py,
pipeline/reqcheck.py, pipeline/reqcheck_prompt.py, pipeline/reqcheck_run.py,
pipeline/prompts/requirements_check.md, pipeline/prompts/requirements_evidence.md

## Context

Palgu Flow drafts a spec for every task, but nothing checks that the requirements are right before code
is written. Palgu will call hosted ideavalidator on every spec (srooter#2785: ask, then fix; blockers
stop the build). The 10-stage validation takes 20-40 minutes. This check has to answer within 45 s, with
p50 under 30 s.

## Decision

- **One route on ideavalidator-web**, the Rust service that is already deployed:
  `POST /api/v1/requirements/check`, contract v1 as in srooter#2785. Request and response bodies are
  the same on both hops, and the gateway relays the response unchanged.
- **The ADR 0013 pattern.** Rust authenticates the caller (Bearer, the short-lived Palgu key the gateway
  mints, scoped to chat and research), validates the body (422 without spawning anything), and spawns
  `python -m worker.req_check` under a hard deadline (`REQ_CHECK_TIMEOUT_MS`, default 45 000). The
  request goes in on stdin and the key in `PALGU_API_KEY`, never on the command line. The worker prints
  one `{"status","body"}` line. `kill_on_drop` stops the child when the deadline passes. A separate
  semaphore (`MAX_CONCURRENT_CHECKS`, default 8) keeps checks apart from the long validation runs.
- **One structured call.** A `json_schema` chat completion on the caller's key judges every requirement.
  Its kinds are `wrong`, `contradiction`, `unclear`, `untestable`, `missing`, `scope_creep`, `off_icp`
  and `unsupported_claim`. It uses the repo's configured Palgu structure model (`PALGU_STRUCTURE_MODEL`,
  default `gemini-3.8-flash`), pinned with `x-srooter-pin` the way `PalguClient` does. No new model ids.
- **Grounded research only for a new product** (`context.existing_app == false`). It runs in parallel
  with the main call: a short `/v1/research` query about the product (long queries took 40 s or more)
  and then a second structured pass that compares the cited facts with the requirements. Its findings
  only keep evidence whose URL is one of the research sources, as in ADR 0010's citation check. When
  research fails or misses the deadline, the main result still returns, and the summary says
  "research skipped: <why>".
- **Deterministic rules after the model.** Severity comes from the kind, never from the model.
  `wrong` and `contradiction` are blockers. `unclear` and `untestable` are majors. Everything else is
  minor. Unknown kinds are dropped, and so are findings without a message. A `req_id` the person never
  sent becomes `null`. The verdict is `blocked` when there is any blocker, `questions` when there is any
  major, and `ok` otherwise.
- **Anti-over-qualification (ADR 0010).** The prompt carries the "judge it AS STATED, for the stated
  ICP" rule and "never invent requirements". `missing` is limited to gaps the intent implies, at most 3.
- **Errors.** 401 when the key is missing or Palgu rejects it (401/403). 402 passes Palgu's body
  through. 422 for an invalid body. 503 for a timeout (`check_timeout`), a worker crash, a Palgu outage,
  unparseable model output, or a malformed worker reply (`check_unavailable`). A check that did not run
  never comes back as `ok`.
- **Logs carry counts only**: the number of requirements, whether it is a new product, the status, the
  verdict, the number of findings and the time taken. They never contain the key or the requirement text.

## Deviations from contract v1 (flagged to the gateway)

- `depth` accepts only `"quick"` (or absent). Contract v1 defines no other depth, so anything else is 422.
- Each requirement's `text` is capped at 4000 characters and ids must be unique (422 otherwise). The
  contract does not state either limit.
- `duration_ms` is the time measured end to end by the Rust route, including the worker spawn.

## Alternatives considered

- **Run the 10-stage pipeline in a "lite" mode.** Rejected because it is still minutes long.
- **Research first, then a single call that sees the evidence.** Rejected because research alone took
  12-41 s, which leaves too little of the 45 s budget. Running it in parallel keeps the check without
  research at about 15 s.
- **Port the handler to the Python `server/`.** Not done. That server is MCP-only, has no REST layer
  and is being retired (ADR 0013), so adding the handler there is not cheap.

## Consequences

- Palgu can check every spec in seconds on the caller's org and budget, and ideavalidator stores no key.
- The deploy is the usual ideavalidator-web image. The worker and prompts ship under `pipeline/` and
  `worker/`, which the Dockerfile already copies.

## Quality-gate notes

- `reqcheck_run.post_json(url, headers, body, timeout)` takes 4 parameters. It is the injected transport
  seam, and tests replace it with a fake. Every other function stays within 3 parameters, because
  `_Ctx` bundles the request, key, options and deadline.
