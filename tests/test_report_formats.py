import json

import pytest

from pipeline.report_formats import FORMATS, export


def _seed(run_dir):
    run_dir.mkdir(parents=True, exist_ok=True)
    stages = {"frame": ("GO", 4.2), "problem": ("GO", 4.4), "market": ("PIVOT", 3.2),
              "icp": ("GO", 4.8), "swot": ("GO", 3.5), "wtp": ("GO", 4.4),
              "economics": ("GO", 5.0), "risks": ("GO", 4.5), "decision": ("GO", 4.5)}
    for sid, (v, sc) in stages.items():
        (run_dir / f"{sid}.json").write_text(json.dumps({
            "stage": sid, "summary": f"summary for {sid}", "scores": {"a": int(sc)},
            "gate": {"stage": sid, "verdict": v, "score": sc, "reasons": ["r"]},
            "evidence": [], "unknowns": []}))
    (run_dir / "decision.md").write_text("# decision\n\nGO to test.\n")


def test_formats_listed():
    assert set(FORMATS) >= {"md", "html", "xlsx", "pdf"}


def test_export_md(tmp_path):
    _seed(tmp_path / "idea"); out = export(tmp_path / "idea", "md")
    assert out.suffix == ".md" and "PIVOT" in out.read_text()


def test_export_html_has_chart_and_stages(tmp_path):
    _seed(tmp_path / "idea"); out = export(tmp_path / "idea", "html")
    html = out.read_text()
    assert out.suffix == ".html"
    assert "<svg" in html and "frame" in html and "economics" in html
    assert "GO" in html


def test_export_html_embeds_image_when_provided(tmp_path):
    _seed(tmp_path / "idea")
    out = export(tmp_path / "idea", "html", image_fn=lambda prompt: b"\x89PNGfake")
    assert "data:image/png;base64," in out.read_text()


def test_export_html_without_image_still_works(tmp_path):
    _seed(tmp_path / "idea")
    out = export(tmp_path / "idea", "html", image_fn=lambda prompt: None)
    assert out.suffix == ".html" and "<svg" in out.read_text()


def test_export_xlsx(tmp_path):
    import openpyxl
    _seed(tmp_path / "idea"); out = export(tmp_path / "idea", "xlsx")
    assert out.suffix == ".xlsx"
    wb = openpyxl.load_workbook(out); assert wb.worksheets


def test_export_pdf_at_least_emits_html(tmp_path):
    _seed(tmp_path / "idea"); out = export(tmp_path / "idea", "pdf")
    assert out.suffix in (".pdf", ".html")  # pdf if a renderer exists, else html fallback


def test_unknown_format_raises(tmp_path):
    _seed(tmp_path / "idea")
    with pytest.raises(ValueError):
        export(tmp_path / "idea", "docx")


def test_cli_report_md_returns_memo(tmp_path):
    from pipeline.report_export import ReportJob, cli_report
    _seed(tmp_path / "idea")
    assert "PIVOT" in cli_report(ReportJob(tmp_path / "idea", "md"))


def test_cli_report_nonmd_writes_and_reports_path(tmp_path):
    from pipeline.report_export import ReportJob, cli_report
    _seed(tmp_path / "idea")
    msg = cli_report(ReportJob(tmp_path / "idea", "html"))
    assert msg.startswith("wrote ") and msg.endswith(".html")


def test_cli_report_writes_to_dest_dir(tmp_path):
    from pipeline.report_export import ReportJob, cli_report
    _seed(tmp_path / "idea")
    dest = tmp_path / "deliverables"
    msg = cli_report(ReportJob(tmp_path / "idea", "html", dest=dest))
    assert msg.startswith("wrote ")
    assert (dest / "report.html").exists()


def test_cli_report_md_with_dest_writes_file(tmp_path):
    from pipeline.report_export import ReportJob, cli_report
    _seed(tmp_path / "idea")
    dest = tmp_path / "out"
    msg = cli_report(ReportJob(tmp_path / "idea", "md", dest=dest))
    assert (dest / "report.md").exists() and "PIVOT" in (dest / "report.md").read_text()
    assert msg.startswith("wrote ")


def test_cli_report_md_no_dest_returns_memo(tmp_path):
    from pipeline.report_export import ReportJob, cli_report
    _seed(tmp_path / "idea")
    assert "PIVOT" in cli_report(ReportJob(tmp_path / "idea", "md"))


def test_cli_report_xlsx_to_dest(tmp_path):
    import openpyxl
    from pipeline.report_export import ReportJob, cli_report
    _seed(tmp_path / "idea")
    dest = tmp_path / "x"
    cli_report(ReportJob(tmp_path / "idea", "xlsx", dest=dest))
    assert openpyxl.load_workbook(dest / "report.xlsx").worksheets


def _seed_classify(run_dir):
    (run_dir / "classify.json").write_text(json.dumps({
        "primary_category": "ai_action_layer", "usp": "Cross-assistant calling connector",
        "business_model_canvas": {
            "customer_segments": {"text": "Indie hackers", "status": "HYPOTHESIS"},
            "value_propositions": {"text": "Give your agent a phone", "status": "HYPOTHESIS"},
            "revenue_streams": {"text": "Usage credits", "status": "HYPOTHESIS"}},
        "value_positioning": {
            "axes": {"x_label": "Breadth of agents", "y_label": "Reliability"},
            "our_position": {"label": "Phrok", "x": 80, "y": 75},
            "competitors": [{"label": "ClawCall", "x": 30, "y": 50},
                            {"label": "Bland", "x": 40, "y": 70}]}}))


def test_html_includes_canvas_and_positioning_when_classify_present(tmp_path):
    _seed(tmp_path / "idea"); _seed_classify(tmp_path / "idea")
    out = export(tmp_path / "idea", "html")
    html = out.read_text()
    assert "Business Model Canvas" in html
    assert "Give your agent a phone" in html and "Usage credits" in html
    assert "Value positioning" in html and "<svg" in html
    assert "Phrok" in html and "ClawCall" in html
    assert "Breadth of agents" in html  # axis label


def test_html_without_classify_omits_canvas(tmp_path):
    _seed(tmp_path / "idea")
    html = export(tmp_path / "idea", "html").read_text()
    assert "Business Model Canvas" not in html
