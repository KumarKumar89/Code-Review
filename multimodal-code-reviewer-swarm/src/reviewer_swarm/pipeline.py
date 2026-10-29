"""Unified review pipeline: static evidence first, optional local model hypotheses."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from reviewer_swarm.review import scan_to_json
from reviewer_swarm.agents import review_with_local_model


def _rust_scan(root: Path, binary: str) -> list[dict[str, Any]] | None:
    """Use the optional Rust scanner if configured and built; otherwise fall back."""
    executable = Path(binary)
    if not executable.exists():
        return None
    result = subprocess.run(
        [str(executable.resolve()), str(root), "-"],
        capture_output=True, text=True, timeout=120, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Rust scanner failed ({result.returncode}): {result.stderr[-1000:]}")
    payload = json.loads(result.stdout)
    if not isinstance(payload, list):
        raise ValueError("Rust scanner returned a non-list JSON payload.")
    return payload


def run_review(
    repository: str | Path,
    *,
    use_model: bool = False,
    model: str | None = None,
    rust_binary: str | None = None,
) -> dict[str, Any]:
    root = Path(repository).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Repository path must be an existing directory: {root}")
    static_findings = None
    scanner = "python"
    candidate_binary = rust_binary or os.getenv("REVIEW_RUST_BINARY")
    if candidate_binary:
        static_findings = _rust_scan(root, candidate_binary)
        if static_findings is not None:
            scanner = "rust-parallel"
    if static_findings is None:
        static_findings = scan_to_json(root)
    model_result = review_with_local_model(root, model=model) if use_model else None
    return {
        "schema_version": "1.0",
        "repository": str(root),
        "scanner": scanner,
        "static_findings": static_findings,
        "model_review": model_result,
        "interpretation": {
            "static_findings": "Deterministic rule or syntax evidence; each still requires contextual review.",
            "model_findings": "Unverified hypotheses, not proof. Verify with tests, data flow, and independent evidence.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-first local code-review pipeline.")
    parser.add_argument("--path", required=True, help="Repository directory to review.")
    parser.add_argument("--output", default="review-report.json", help="Output JSON path.")
    parser.add_argument("--model", action="store_true", help="Run local Ollama specialist agents.")
    parser.add_argument("--model-name", default=None, help="Ollama model tag; defaults to REVIEW_MODEL or qwen2.5-coder:3b.")
    parser.add_argument("--rust-binary", default=None, help="Optional built Rust scanner executable.")
    args = parser.parse_args()
    report = run_review(args.path, use_model=args.model, model=args.model_name, rust_binary=args.rust_binary)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Static findings: {len(report['static_findings'])}")
    if report["model_review"] is not None:
        print(f"Model hypotheses: {len(report['model_review']['findings'])}")
        print(f"Model errors: {len(report['model_review']['errors'])}")
    print(f"Scanner: {report['scanner']} | Report: {output.resolve()}")


if __name__ == "__main__":
    main()
