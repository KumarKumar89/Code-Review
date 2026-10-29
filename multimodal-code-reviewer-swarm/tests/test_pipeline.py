from pathlib import Path

from reviewer_swarm.pipeline import run_review


def test_pipeline_falls_back_to_python_scanner(tmp_path: Path) -> None:
    (tmp_path / "example.py").write_text("eval(user_input)\n", encoding="utf-8")
    report = run_review(tmp_path)
    assert report["scanner"] == "python"
    assert report["model_review"] is None
    assert any(item["rule_id"] == "SEC-DYNAMIC-EVAL" for item in report["static_findings"])
    assert "not proof" in report["interpretation"]["model_findings"]
