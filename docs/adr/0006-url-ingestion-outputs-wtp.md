# 0006 - URL ingestion, output formats, and a concrete willingness-to-pay heuristic

**Status:** accepted
**Date:** 2026-11-01
**Spec:** pipeline/ingest.py, pipeline/report_formats.py, pipeline/images.py, pipeline/prompts/wtp.md
**Deciders:** Ali Shaheen, Claude

## Context

Three capabilities were requested: validate any business website by URL (optionally a new idea *for*
that company), export the result in several formats with imagery, and have the willingness-to-pay stage
produce a concrete, defensible number rather than only a range of comparables.

## Decision

- **URL ingestion** (`pipeline/ingest.py` + `ingest` CLI + Gemini `research_urls` using the `url_context`
  tool with a search fallback): read the site, research the company, and emit a full brief
  (`ideas/<slug>.md`) in the template format, with a thesis spine and a classified business model. With
  an angle the idea is the angle and the site is context/why-us; without one the company's own business
  is the idea. `--run` chains straight into the full pipeline.
- **Output formats** (`pipeline/report_formats.py`, `pipeline/report_xlsx.py`, `pipeline/images.py`):
  `report --format md|html|xlsx|pdf` (alias `--output`/`-output`). HTML is self-contained with inline SVG
  charts and an optional Gemini-generated hero image (`images.py`, best-effort, skips on failure); PDF
  renders the HTML via headless Chrome or weasyprint, falling back to the HTML file; XLSX is a generalized
  gate + evidence workbook for any run.
- **Concrete WTP heuristic** (`prompts/wtp.md` + `schemas/wtp.json` `estimated_wtp`): a single figure
  derived by a blended method — value-based (a defensible fraction of value created/cost saved/revenue
  unblocked), comparable-anchored, and 10x-rule sanity-checked — with the arithmetic shown and inputs
  labelled SOURCED/ESTIMATE. It is a desk estimate to be proven by the pre-sale, never treated as validated.

## Consequences

- `/ideavalidator <url>` runs the whole validation agentically from a website.
- Reports are shareable as HTML/PDF/XLSX; charts are deterministic SVG, imagery is AI and optional.
- The WTP stage now commits to a number with a basis, which the economics and decision stages consume.

## Alternatives Considered

| Option | Why Not |
|--------|---------|
| Scrape sites with a custom crawler | Gemini url_context is simpler, cited, and already in use |
| AI-generate charts too | Charts must be exact; SVG is deterministic. AI is used only for the hero image |
| Leave WTP as a range | The user needs a concrete, defensible figure to test |

## Links

- Related: 0001 (pipeline), 0004 (flexible objectives/modes), 0005 (plugin packaging)
