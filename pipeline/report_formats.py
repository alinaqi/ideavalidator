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


_CANVAS_BLOCKS = ("customer_segments", "value_propositions", "channels", "customer_relationships",
                  "revenue_streams", "key_resources", "key_activities", "key_partnerships",
                  "cost_structure")


def _canvas_grid(run_dir: Path) -> str:
    canvas = _load(run_dir, "classify").get("business_model_canvas") or {}
    if not canvas:
        return ""
    cells = []
    for key in _CANVAS_BLOCKS:
        b = canvas.get(key) or {}
        cells.append(f'<div class="bmc"><h4>{key.replace("_", " ")}</h4>'
                     f'<p>{b.get("text", "—")}</p></div>')
    return ('<h2>Business Model Canvas</h2><div class="bmcgrid">' + "".join(cells) + "</div>")


def _point(p: dict, color: str) -> str:
    x = 40 + float(p.get("x") or 0) / 100 * 320
    y = 240 - float(p.get("y") or 0) / 100 * 210
    return (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="{color}"/>'
            f'<text x="{x+9:.0f}" y="{y+4:.0f}" font-size="11" fill="currentColor">{p.get("label", "")}</text>')


def _positioning_map(run_dir: Path) -> str:
    vp = _load(run_dir, "classify").get("value_positioning") or {}
    if not vp.get("our_position"):
        return ""
    ax = vp.get("axes") or {}
    pts = _point(vp["our_position"], "#1b7a3d")
    pts += "".join(_point(c, "#9c1b1b") for c in (vp.get("competitors") or []))
    return (f'<h2>Value positioning</h2><svg viewBox="0 0 400 270" width="100%" role="img">'
            f'<line x1="40" y1="240" x2="380" y2="240" stroke="#999"/>'
            f'<line x1="40" y1="30" x2="40" y2="240" stroke="#999"/>'
            f'<text x="200" y="265" font-size="11" text-anchor="middle" fill="currentColor">'
            f'{ax.get("x_label", "")}</text>'
            f'<text x="12" y="135" font-size="11" text-anchor="middle" fill="currentColor" '
            f'transform="rotate(-90 12 135)">{ax.get("y_label", "")}</text>{pts}</svg>')


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
           "section{border-top:1px solid #eee;padding:.5rem 0}"
           ".bmcgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}"
           ".bmc{border:1px solid #ddd;border-radius:8px;padding:8px}.bmc h4{margin:0 0 4px;font-size:12px;"
           "text-transform:capitalize;color:#1f3a5f}.bmc p{margin:0;font-size:13px}"
           "@media(max-width:560px){.bmcgrid{grid-template-columns:1fr}}@media(prefers-color-scheme:dark)"
           "{body{background:#111;color:#eee}h1{color:#9db8dd}section{border-color:#333}"
           ".bmc{border-color:#333}.bmc h4{color:#9db8dd}}")
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{run_dir.name} — validation</title><style>{css}</style></head><body>"
            f"<h1>{run_dir.name}</h1><p><strong>Overall: {overall}</strong></p>"
            f"{_hero(image_fn, run_dir.name)}<h2>Gate scores</h2>{_svg_bars(run_dir)}"
            f"{_canvas_grid(run_dir)}{_positioning_map(run_dir)}"
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
