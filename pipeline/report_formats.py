"""Export a run as md / html / xlsx / pdf. Charts are inline SVG; an optional hero image embeds as a
base64 data URI. PDF renders the HTML via headless Chrome or weasyprint, falling back to the HTML file."""
from __future__ import annotations

import base64
import json
import shutil
import subprocess
from pathlib import Path

from .report import build_memo
from .report_xlsx import write_xlsx
from .stages import STAGES

FORMATS = ("md", "html", "xlsx", "pdf")
_BAR = {"GO": "#1b7a3d", "PIVOT": "#7a5b00", "KILL": "#9c1b1b", "UNKNOWN": "#888"}


def _load(run_dir: Path, sid: str) -> dict:
    p = run_dir / f"{sid}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _svg_bars(run_dir: Path) -> str:
    rows = []
    for i, stage in enumerate(STAGES):
        g = _load(run_dir, stage.id).get("gate", {})
        sc = float(g.get("score") or 0); y = 10 + i * 30
        w = int(sc / 5 * 360); color = _BAR.get(g.get("verdict", "UNKNOWN"), "#888")
        rows.append(
            f'<text x="0" y="{y+14}" font-size="12" fill="currentColor">{stage.id}</text>'
            f'<rect x="90" y="{y}" width="{w}" height="20" fill="{color}" rx="3"/>'
            f'<text x="{98+w}" y="{y+14}" font-size="11" fill="currentColor">'
            f'{g.get("verdict","-")} {sc:g}</text>')
    return f'<svg viewBox="0 0 520 {len(STAGES)*30+20}" width="100%" role="img">{"".join(rows)}</svg>'


def _stage_cards(run_dir: Path) -> str:
    cards = []
    for stage in STAGES:
        d = _load(run_dir, stage.id)
        if not d:
            continue
        g = d.get("gate", {}); c = _BAR.get(g.get("verdict", "UNKNOWN"), "#888")
        cards.append(f'<section><h3><span style="color:{c}">&#9632;</span> {stage.id} — '
                     f'{g.get("verdict","-")} ({g.get("score","-")})</h3><p>{d.get("summary","")}</p></section>')
    return "".join(cards)


def _hero(image_fn, slug: str) -> str:
    if not image_fn:
        return ""
    blob = image_fn(slug)
    if not blob:
        return ""
    b64 = base64.b64encode(blob).decode()
    return f'<img class="hero" alt="" src="data:image/png;base64,{b64}"/>'


def _html(run_dir: Path, image_fn) -> str:
    overall = _load(run_dir, "decision").get("gate", {}).get("verdict", "UNKNOWN")
    css = ("body{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 16px;"
           "color:#1a1a1a;background:#fff}h1{color:#1f3a5f}.hero{width:100%;border-radius:10px;margin:1rem 0}"
           "section{border-top:1px solid #eee;padding:.5rem 0}@media(prefers-color-scheme:dark)"
           "{body{background:#111;color:#eee}h1{color:#9db8dd}section{border-color:#333}}")
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{run_dir.name} — validation</title><style>{css}</style></head><body>"
            f"<h1>{run_dir.name}</h1><p><strong>Overall: {overall}</strong></p>"
            f"{_hero(image_fn, run_dir.name)}<h2>Gate scores</h2>{_svg_bars(run_dir)}"
            f"<h2>Stages</h2>{_stage_cards(run_dir)}</body></html>")


def _render_pdf(html_path: Path, pdf_path: Path) -> bool:
    chrome = shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")
    if chrome:
        try:
            subprocess.run([chrome, "--headless", "--no-pdf-header-footer",
                            f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                           check=True, capture_output=True, timeout=120)
            return pdf_path.exists()
        except Exception:
            pass
    try:
        from weasyprint import HTML

        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        return pdf_path.exists()
    except Exception:
        return False


def export(run_dir: Path, fmt: str, image_fn=None) -> Path:
    """Write the report in `fmt`; return the path. PDF falls back to HTML if no renderer is present."""
    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r}; choose from {', '.join(FORMATS)}")
    if fmt == "md":
        out = run_dir / "report.md"; out.write_text(build_memo(run_dir)); return out
    if fmt == "xlsx":
        return write_xlsx(run_dir, run_dir / "report.xlsx")
    html_path = run_dir / "report.html"
    html_path.write_text(_html(run_dir, image_fn))
    if fmt == "html":
        return html_path
    pdf_path = run_dir / "report.pdf"
    return pdf_path if _render_pdf(html_path, pdf_path) else html_path
