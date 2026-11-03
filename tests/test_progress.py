import json

from pipeline.progress import ProgressStep, write_progress


def test_write_progress_round_trips(tmp_path):
    write_progress(tmp_path, ProgressStep(index=3, total=10, stage="market",
                                          state="done", verdict="GO", score=4.0))
    data = json.loads((tmp_path / "progress.json").read_text())
    assert data["index"] == 3 and data["total"] == 10 and data["stage"] == "market"
    assert data["state"] == "done" and data["verdict"] == "GO" and data["score"] == 4.0
    assert "ts" in data


def test_write_progress_defaults_and_mkdir(tmp_path):
    out = tmp_path / "runs" / "slug"
    write_progress(out, ProgressStep(index=1, total=10, stage="frame"))
    data = json.loads((out / "progress.json").read_text())
    assert data["state"] == "running" and data["verdict"] == "" and data["score"] == 0.0
