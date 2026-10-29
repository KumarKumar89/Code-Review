"""Safe, deterministic first-pass repository scanner.

This module reads source files as text. It does not import or execute target code.
Pattern findings are hypotheses and must be verified by a reviewer.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SUPPORTED_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".java", ".go", ".rs", ".rb", ".php", ".sh", ".bash",
    ".yaml", ".yml", ".json", ".toml", ".ini", ".html", ".css",
}
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "dist", "build",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".next",
}
MAX_FILE_BYTES = 1_000_000

RULES: tuple[tuple[str, str, str, re.Pattern[str], str], ...] = (
    (
        "SEC-DYNAMIC-EVAL", "security", "medium",
        re.compile(r"\b(?:eval|exec)\s*\("),
        "Dynamic code evaluation pattern found. Confirm whether input can be influenced by an untrusted source.",
    ),
    (
        "SEC-SHELL-TRUE", "security", "medium",
        re.compile(r"\bshell\s*=\s*True\b"),
        "Subprocess configuration uses shell=True. Review argument construction and untrusted-input flow.",
    ),
    (
        "SEC-HARDCODED-SECRET", "security", "high",
        re.compile(r"""(?i)\b(?:api[_-]?key|secret|password|access[_-]?token)\b\s*[:=]\s*['"][^'"]{8,}['"]"""),
        "Possible hard-coded secret assignment. The matched value is intentionally not copied into the finding.",
    ),
    (
        "MAINT-TODO", "maintainability", "info",
        re.compile(r"\b(?:TODO|FIXME|XXX)\b"),
        "Unresolved TODO/FIXME marker. Determine whether it represents incomplete work.",
    ),
    (
        "RELIABILITY-BARE-EXCEPT", "reliability", "low",
        re.compile(r"^\s*except\s*:\s*(?:#.*)?$"),
        "Bare exception handler may hide unexpected failures. Consider handling explicit exception types.",
    ),
)


@dataclass(frozen=True)
class Finding:
    rule_id: str
    category: str
    severity: str
    confidence: float
    file_path: str
    line: int
    title: str
    evidence: str
    recommendation: str
    verification_status: str = "unverified"


def _iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield path


def scan_repository(root: str | Path) -> list[Finding]:
    """Run deterministic, non-executing checks and return stable-sorted findings."""
    target = Path(root).expanduser().resolve()
    if not target.exists():
        raise ValueError(f"Repository path does not exist: {target}")
    if not target.is_dir():
        raise ValueError(f"Repository path is not a directory: {target}")

    findings: list[Finding] = []
    for path in _iter_files(target):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relative_path = path.relative_to(target).as_posix()
        lines = content.splitlines()

        if path.suffix.lower() in {".py", ".pyi"}:
            try:
                ast.parse(content, filename=relative_path)
            except SyntaxError as exc:
                findings.append(
                    Finding(
                        rule_id="PY-SYNTAX",
                        category="correctness",
                        severity="high",
                        confidence=1.0,
                        file_path=relative_path,
                        line=max(1, int(exc.lineno or 1)),
                        title="Python syntax error",
                        evidence=(exc.msg or "Syntax error")[:300],
                        recommendation="Correct the syntax error, then run the relevant tests.",
                        verification_status="statically_supported",
                    )
                )

        for line_number, line in enumerate(lines, start=1):
            for rule_id, category, severity, pattern, recommendation in RULES:
                if not pattern.search(line):
                    continue
                # Avoid placing secret values or full source lines in reports.
                evidence = (
                    "Potential credential assignment detected; value redacted."
                    if rule_id == "SEC-HARDCODED-SECRET"
                    else line.strip()[:240]
                )
                confidence = {
                    "SEC-DYNAMIC-EVAL": 0.60,
                    "SEC-SHELL-TRUE": 0.65,
                    "SEC-HARDCODED-SECRET": 0.72,
                    "MAINT-TODO": 0.95,
                    "RELIABILITY-BARE-EXCEPT": 0.65,
                }[rule_id]
                findings.append(
                    Finding(
                        rule_id=rule_id,
                        category=category,
                        severity=severity,
                        confidence=confidence,
                        file_path=relative_path,
                        line=line_number,
                        title=rule_id.replace("-", " ").title(),
                        evidence=evidence,
                        recommendation=recommendation,
                    )
                )

    return sorted(findings, key=lambda item: (item.file_path, item.line, item.rule_id))


def scan_to_json(root: str | Path) -> list[dict[str, object]]:
    """Return JSON-ready findings."""
    return [asdict(finding) for finding in scan_repository(root)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the non-executing code-review scanner.")
    parser.add_argument("--path", required=True, help="Directory containing the repository to review.")
    parser.add_argument("--output", default="review-findings.json", help="Output JSON file path.")
    args = parser.parse_args()

    findings = scan_to_json(args.path)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"Findings: {len(findings)}")
    print(f"JSON report: {output_path.resolve()}")


if __name__ == "__main__":
    main()
