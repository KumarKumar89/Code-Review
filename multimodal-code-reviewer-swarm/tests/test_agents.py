from pathlib import Path

from reviewer_swarm.agents import _deduplicate, _read_sources


def test_source_loader_skips_generated_directories_and_caps_files(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "bad.js").write_text("eval(x)", encoding="utf-8")
    result = _read_sources(tmp_path)
    assert [item["path"] for item in result] == ["src/app.py"]


def test_deduplicate_merges_roles() -> None:
    findings = [
        {"file_path": "a.py", "line": 4, "title": "SQL injection", "agent_role": "security"},
        {"file_path": "a.py", "line": 4, "title": " sql injection ", "agent_role": "correctness"},
    ]
    result = _deduplicate(findings)
    assert len(result) == 1
    assert result[0]["agent_role"] == "correctness,security"
