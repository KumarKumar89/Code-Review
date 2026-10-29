"""Shared, non-executing repository scanner used by the CLI and the Colab notebook.

Keeping the implementation in one place removes the previous duplication between
``reviewer_swarm.review`` and the notebook copy of the same logic, which had already
drifted (different excluded directories, missing rules, different evidence handling).

Design goals, in order:

1. **Safety** - never import, execute, or follow symlinks out of the target tree.
2. **Determinism** - identical input yields byte-identical JSON output; findings are
   sorted by ``(file_path, line, rule_id)``.
3. **Speed** - a single walk with directory pruning, literal pre-filters before any
   regex work, bounded per-line and per-file work, and optional parallel file
   processing for large repositories.
"""
from __future__ import annotations

import ast
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from ._rules import (
    EVIDENCE_MAX_CHARS,
    MAX_LINE_CHARS,
    REDACTED_EVIDENCE,
    RULES,
    Rule,
)

SUPPORTED_SUFFIXES = frozenset({
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".java", ".go", ".rs", ".rb", ".php", ".sh", ".bash",
    ".yaml", ".yml", ".json", ".toml", ".ini", ".html", ".css",
})

#: Directories pruned during the walk (never descended into), matched by name.
EXCLUDED_DIRS = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "bower_components",
    "dist", "build", "target", "out", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", ".nox", ".next", ".nuxt", ".idea", ".vscode",
    ".terraform", "site-packages", ".eggs", "coverage", "htmlcov",
})

#: Files skipped by name regardless of suffix.
EXCLUDED_FILES = frozenset({".DS_Store", "Thumbs.db"})

MAX_FILE_BYTES = 1_000_000

#: Maximum number of findings recorded for a single file. A generated bundle full of
#: TODO markers would otherwise dominate memory and report size; when a file hits the
#: cap a single ``SCAN-NOISE-CAP`` finding records how many were dropped.
MAX_FINDINGS_PER_FILE = 5_000

#: Extensions that get Python-syntax analysis.
PYTHON_SUFFIXES = frozenset({".py", ".pyi"})


@dataclass(frozen=True)
class Finding:
    """One structured review observation."""

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


def _title_for(rule: Rule | str) -> str:
    rule_id = rule if isinstance(rule, str) else rule.rule_id
    return rule_id.replace("-", " ").title()


def discover_files(root: Path) -> list[Path]:
    """Return scannable files under ``root`` without following symlinks.

    Uses :func:`os.walk` with top-down pruning so excluded trees (``node_modules``,
    ``.git``, ...) are never descended into - strictly cheaper than the previous
    ``rglob('*')`` + ``is_file()`` approach, which stat'ed every entry first.
    """
    collected: list[Path] = []
    for dir_path, dir_names, file_names in os.walk(root, topdown=True, followlinks=False):
        # Prune in place so os.walk skips these subtrees entirely.
        dir_names[:] = sorted(name for name in dir_names if name not in EXCLUDED_DIRS)
        base = Path(dir_path)
        for name in sorted(file_names):
            if name in EXCLUDED_FILES:
                continue
            path = base / name
            suffix = path.suffix.lower()
            if suffix not in SUPPORTED_SUFFIXES:
                continue
            try:
                if path.is_symlink():
                    continue
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            collected.append(path)
    collected.sort(key=lambda path: path.relative_to(root).as_posix())
    return collected


def _syntax_finding(relative_path: str, line: int, message: str) -> Finding:
    """Build the ``PY-SYNTAX`` finding for a file the AST parser rejected."""
    return Finding(
        rule_id="PY-SYNTAX",
        category="correctness",
        severity="high",
        confidence=1.0,
        file_path=relative_path,
        line=max(1, line),
        title="Python syntax error",
        evidence=(message or "Syntax error")[:EVIDENCE_MAX_CHARS],
        recommendation="Correct the syntax error, then run the relevant tests.",
        verification_status="statically_supported",
    )


def scan_file(path: Path, root: Path, rules: Sequence[Rule] = RULES) -> list[Finding]:
    """Scan one file and return its findings (empty list when unreadable)."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    try:
        relative_path = path.relative_to(root).as_posix()
    except ValueError:  # defensive: caller passed a path outside root
        relative_path = path.name

    findings: list[Finding] = []

    # AST parsing is by far the most expensive per-file step (it builds a full
    # syntax tree) while the overwhelming majority of Python files are syntactically
    # valid. Skip it for single-statement/blank files, which cannot contain a hidden
    # syntax error; everything else is still parsed in full.
    if path.suffix.lower() in PYTHON_SUFFIXES and "\n" in content.strip():
        try:
            ast.parse(content, filename=relative_path)
        except SyntaxError as exc:
            findings.append(
                _syntax_finding(relative_path, int(exc.lineno or 1), exc.msg or "Syntax error")
            )
        except (ValueError, RecursionError) as exc:  # malformed source we refuse to parse
            findings.append(_syntax_finding(relative_path, 1, str(exc)))

    overflow = 0
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        # Bound the worst case: minified/generated files can carry megabyte lines.
        line = raw_line[:MAX_LINE_CHARS]
        for rule in rules:
            if not rule.matches_line(line):
                continue
            if len(findings) >= MAX_FINDINGS_PER_FILE:
                overflow += 1
                continue
            evidence = (
                REDACTED_EVIDENCE
                if rule.redact_evidence
                else line.strip()[:EVIDENCE_MAX_CHARS]
            )
            findings.append(
                Finding(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    confidence=rule.confidence,
                    file_path=relative_path,
                    line=line_number,
                    title=_title_for(rule),
                    evidence=evidence,
                    recommendation=rule.recommendation,
                )
            )

    if overflow:
        findings.append(
            Finding(
                rule_id="SCAN-NOISE-CAP",
                category="reliability",
                severity="info",
                confidence=1.0,
                file_path=relative_path,
                line=len(content.splitlines()),
                title="Scan Noise Cap",
                evidence=f"{overflow} additional pattern matches suppressed for this file.",
                recommendation=(
                    "This file produced an unusually high number of matches (likely "
                    "generated or minified code). Narrow the scan scope or review it separately."
                ),
                verification_status="statically_supported",
            )
        )
    return findings


def _scan_file_for_worker(args: tuple[str, str]) -> list[Finding]:
    """Module-level helper so results are picklable across processes."""
    root_str, file_str = args
    root = Path(root_str)
    return scan_file(Path(file_str), root)


def resolve_workers(workers: int | None, file_count: int) -> int:
    """Choose a process count. ``None``/``0`` means auto; 1 forces sequential."""
    if workers is not None and workers >= 0:
        if workers == 0:
            pass  # auto
        else:
            return max(1, workers)
    try:
        cpu_count = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1)
    except OSError:
        cpu_count = os.cpu_count() or 1
    # Process pools only pay off once there is real per-file work to overlap.
    if file_count < 64 or cpu_count < 2:
        return 1
    return min(cpu_count, 8, max(1, file_count // 32))


def iter_findings(root: Path, workers: int | None = None) -> Iterator[Finding]:
    """Yield findings for every scannable file under ``root``."""
    files = discover_files(root)
    worker_count = resolve_workers(workers, len(files))
    if worker_count <= 1:
        for path in files:
            yield from scan_file(path, root)
        return

    from concurrent.futures import ProcessPoolExecutor  # imported lazily on purpose

    payload = [(str(root), str(path)) for path in files]
    chunksize = max(1, len(payload) // (worker_count * 8))
    with ProcessPoolExecutor(max_workers=worker_count) as pool:
        for result in pool.map(_scan_file_for_worker, payload, chunksize=chunksize):
            yield from result


def scan_repository(root: str | Path, workers: int | None = None) -> list[Finding]:
    """Run deterministic, non-executing checks and return stable-sorted findings."""
    target = Path(root).expanduser().resolve()
    if not target.exists():
        raise ValueError(f"Repository path does not exist: {target}")
    if not target.is_dir():
        raise ValueError(f"Repository path is not a directory: {target}")
    findings = list(iter_findings(target, workers=workers))
    return sorted(findings, key=lambda item: (item.file_path, item.line, item.rule_id))


def scan_to_json(root: str | Path, workers: int | None = None) -> list[dict[str, object]]:
    """Return JSON-ready findings."""
    return [asdict(finding) for finding in scan_repository(root, workers=workers)]


def build_report(findings: Iterable[Finding], target: Path) -> dict[str, object]:
    """Wrap findings in the versioned report envelope shared by CLI and notebook."""
    materialised = list(findings)
    counts: dict[str, int] = {}
    severities: dict[str, int] = {}
    for finding in materialised:
        counts[finding.category] = counts.get(finding.category, 0) + 1
        severities[finding.severity] = severities.get(finding.severity, 0) + 1
    return {
        "report_version": "1.1",
        "report_type": "deterministic_first_pass",
        "target_directory": str(target),
        "finding_count": len(materialised),
        "counts_by_category": dict(sorted(counts.items())),
        "counts_by_severity": dict(sorted(severities.items())),
        "rules_applied": [rule.rule_id for rule in RULES] + ["PY-SYNTAX"],
        "findings": [asdict(finding) for finding in materialised],
        "limitations": [
            "Pattern matches can be false positives or false negatives.",
            "Target repository code was not executed.",
            "Files above the configured size limit and excluded directories were skipped.",
            "This report is not a security certification.",
        ],
    }


def dump_report(report: dict[str, object]) -> str:
    """Serialise a report deterministically (sorted keys, no volatile timestamps)."""
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


__all__ = [
    "EXCLUDED_DIRS",
    "EXCLUDED_FILES",
    "Finding",
    "MAX_FILE_BYTES",
    "MAX_FINDINGS_PER_FILE",
    "SUPPORTED_SUFFIXES",
    "build_report",
    "discover_files",
    "dump_report",
    "iter_findings",
    "resolve_workers",
    "scan_file",
    "scan_repository",
    "scan_to_json",
]
