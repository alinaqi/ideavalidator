# 0009 - Category classification, business models, Business Model Canvas, USP (+ visualization)

**Status:** accepted
**Date:** 2026-11-01
**Spec:** pipeline/categories.py, pipeline/prompts/classify.md, pipeline/schemas/classify.json,
pipeline/stages.py, pipeline/gates.py, pipeline/runner.py, pipeline/report_formats.py

## Context

A phrok.us validation mis-categorized the idea — it scored standalone AI-calling apps (Voyp, Genspark)
as competitors to what is actually an agent **action-layer / connector** (give an existing assistant a
phone). The wrong category produced the wrong incumbent set, which poisoned market, swot and WTP. The
pipeline had no explicit step to (a) name the business category, (b) pin the correct incumbents, (c)
consider the category's range of business models (so business-model innovation is explicit), or (d)
frame the idea with a Business Model Canvas and a sharp USP.

## Decision

- **Category taxonomy** (`pipeline/categories.py`): a `Category` list (dev tools/API, infrastructure,
  AI action-layer/connector, vertical & horizontal SaaS, PLG, marketplace, directory/graph, consumer
  app, data/analytics, fintech, services, hardware, open-core, embedded B2B2C, content/media, regtech),
  each with real-incumbent patterns, common business models and validation notes; plus a `MODELS` list
  of business-model archetypes for model innovation.
- **New stage `classify`** (runs right after `frame`): picks the primary + secondary category, names the
  category's *true* incumbents (and explicitly excludes look-alikes from other categories), enumerates
  candidate business models including a model-innovation option, fills the 9-block **Business Model
  Canvas**, and writes a **USP** + positioning statement + a 2-axis **value-positioning map**.
- **Non-killing / framing**: `classify`'s gate has no critical criteria and is **excluded from the
  GO/PIVOT/KILL rollup** — it informs, it does not veto.
- **Anchors downstream**: the runner injects a compact category context (category + real incumbents +
  USP) into the market/icp/swot/wtp/economics/decision prompts, and those prompts now instruct the model
  to compare only to the identified category's incumbents and to treat platform-bundling as per-platform
  (the phrok failure mode).
- **Visualization**: the html/pdf report renders the Business Model Canvas as a 9-block grid and the
  value-positioning map as an inline-SVG scatter (our point vs incumbents) when `classify` ran.

## Consequences

- Comparisons are anchored to the correct category, preventing category-error competitor sets.
- Business-model innovation is a first-class output, not an afterthought.
- Pipeline grows to ten stages (`classify` is informational); existing dependency graph is unchanged
  because classify context is injected, not made a hard dependency — so subset reruns still work.
