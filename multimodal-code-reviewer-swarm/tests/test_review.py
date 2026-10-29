import json

import pytest

from reviewer_swarm.review import scan_repository, scan_to_json


def test_scanner_finds_dynamic_eval_and_does_not_execute_target(tmp_path):
    source = tmp_path / "unsafe.py"
    source.write_text("value = eval(user_input)\n", encoding="utf-8")
    findings = scan_repository(tmp_path)
    assert any(item.rule_id == "SEC-DYNAMIC-EVAL" for item in findings)


def test_scanner_redacts_possible_secret_value(tmp_path):
    source = tmp_path / "config.py"
    source.write_text('api_key = "supersecretvalue123"\n', encoding="utf-8")
    findings = scan_repository(tmp_path)
    secret = next(item for item in findings if item.rule_id == "SEC-HARDCODED-SECRET")
    assert "supersecretvalue123" not in secret.evidence
    assert "redacted" in secret.evidence.lower()


def test_scanner_reports_python_syntax_error(tmp_path):
    source = tmp_path / "bad.py"
    source.write_text("def incomplete(:\n    pass\n", encoding="utf-8")
    findings = scan_repository(tmp_path)
    assert any(item.rule_id == "PY-SYNTAX" for item in findings)


def test_scanner_skips_virtual_environment_and_large_files(tmp_path):
    ignored = tmp_path / ".venv"
    ignored.mkdir()
    (ignored / "ignored.py").write_text("eval(input())\n", encoding="utf-8")
    big = tmp_path / "large.py"
    big.write_text("x = 1\n" * 600_000, encoding="utf-8")
    assert scan_repository(tmp_path) == []


def test_scan_json_is_serializable(tmp_path):
    (tmp_path / "app.py").write_text("eval(value)\n", encoding="utf-8")
    encoded = json.dumps(scan_to_json(tmp_path))
    assert "SEC-DYNAMIC-EVAL" in encoded


def test_missing_root_is_clear_error(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        scan_repository(tmp_path / "missing")
