# 0007 - Configurable report output directory

**Status:** accepted
**Date:** 2026-11-01
**Spec:** pipeline/report_export.py, pipeline/report_formats.py, pipeline/cli.py
**Deciders:** Ali Shaheen, Claude

## Context

The exported deliverable (`report.md|html|xlsx|pdf`) was always written inside the run folder
(`runs/<slug>/`), with no way to choose where it lands. Users want to save a report straight into a
project, a shared drive, or a deliverables folder. Separately, `ingest --run` hardcoded the runs base
directory, ignoring a caller-supplied location.

ADR 0006 established the export surface (`export`, `export_with_images`, `cli_report`) but kept all three
signatures flat. Adding a destination parameter to the CLI-facing helpers would exceed the repo's
≤3-parameters-per-function quality gate.

## Decision

- Add `--dest <dir>` (alias `--out-dir`) to the `report` command: the directory the exported report file
  is written into. Default remains the run folder, so existing behaviour is unchanged.
- Introduce a `ReportJob` dataclass (`run_dir, fmt, dest, root`) in a new `pipeline/report_export.py`
  and move the CLI-facing `export_with_images` and `cli_report` there, each taking a single `ReportJob`.
  This keeps functions within the parameter and ≤10-functions-per-file gates and separates "build a
  format" (`report_formats.export`, unchanged) from "export to a chosen place with imagery".
- Export still writes into the run folder first; a `_place` helper copies the produced file into `dest`
  when set (and is a no-op when `dest` equals the source directory). `md` with no `dest` still prints the
  memo to stdout; `md` with a `dest` writes `report.md` there.
- Add `--out` to the `ingest` command and thread it into the chained `--run` so ingestion honours a
  custom runs directory.

## Consequences

- Reports can be saved anywhere without moving files by hand; the default path is unchanged.
- The export API is now dataclass-based; callers construct a `ReportJob`. Internal only — no public
  consumers outside the CLI and tests.
- `pipeline/report_formats.py` is reduced to format builders; destination/imagery wiring lives in
  `pipeline/report_export.py`.
