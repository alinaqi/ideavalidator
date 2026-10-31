"""Generalised xlsx export for any run directory: gates + per-stage scores + evidence."""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .stages import STAGES

_FILL = {"GO": "C6EFCE", "PIVOT": "FFEB9C", "KILL": "F4C7C3"}
_HEAD = PatternFill("solid", fgColor="1F3A5F")
_WRAP = Alignment(wrap_text=True, vertical="top")


def _load(run_dir: Path, sid: str) -> dict:
    p = run_dir / f"{sid}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _header(ws, cols, widths) -> None:
    for i, (c, w) in enumerate(zip(cols, widths), 1):
        cell = ws.cell(row=1, column=i, value=c)
        cell.fill = _HEAD; cell.font = Font(color="FFFFFF", bold=True); cell.alignment = _WRAP
        ws.column_dimensions[get_column_letter(i)].width = w


def _gates_sheet(wb, run_dir: Path) -> None:
    ws = wb.active; ws.title = "Gates"
    _header(ws, ["Stage", "Verdict", "Score", "Summary"], [16, 12, 8, 90])
    for r, stage in enumerate(STAGES, 2):
        d = _load(run_dir, stage.id); g = d.get("gate", {})
        ws.cell(row=r, column=1, value=stage.id)
        v = ws.cell(row=r, column=2, value=g.get("verdict", "-"))
        if g.get("verdict") in _FILL:
            v.fill = PatternFill("solid", fgColor=_FILL[g["verdict"]])
        ws.cell(row=r, column=3, value=g.get("score"))
        ws.cell(row=r, column=4, value=(d.get("summary", "") or "")[:500]).alignment = _WRAP


_EV_KEYS = ("claim", "behavior_vs_stated", "directness", "recency", "source_url")


def _evidence_rows(run_dir: Path):
    for stage in STAGES:
        for e in _load(run_dir, stage.id).get("evidence", []) or []:
            yield stage.id, e


def _write_ev_row(ws, row: int, item: tuple) -> None:
    sid, e = item
    ws.cell(row=row, column=1, value=sid)
    for col, key in enumerate(_EV_KEYS, 2):
        ws.cell(row=row, column=col, value=e.get(key, "")).alignment = _WRAP


def _evidence_sheet(wb, run_dir: Path) -> None:
    ws = wb.create_sheet("Evidence")
    _header(ws, ["Stage", "Claim", "Behav/Stated", "Direct", "Recency", "Source"], [12, 60, 14, 10, 10, 50])
    for r, item in enumerate(_evidence_rows(run_dir), 2):
        _write_ev_row(ws, r, item)


def write_xlsx(run_dir: Path, out_path: Path) -> Path:
    wb = Workbook()
    _gates_sheet(wb, run_dir)
    _evidence_sheet(wb, run_dir)
    wb.save(out_path)
    return out_path
