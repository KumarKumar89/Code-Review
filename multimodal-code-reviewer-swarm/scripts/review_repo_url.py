#!/usr/bin/env python3
"""Review any public repository pasted as a URL, from the command line.

Thin wrapper around :func:`reviewer_swarm.pipeline.run_review` that accepts a
public repository link (GitHub / GitLab / Bitbucket page URL, ``owner/repo``
shorthand, or a direct ``*.git`` URL), shallow-clones it into a temporary
directory, runs the deterministic scanner, and writes a JSON report.

Usage examples
--------------
    python scripts/review_repo_url.py https://github.com/psf/requests
    python scripts/review_repo_url.py owner/repo --output report.json
    python scripts/review_repo_url.py https://gitlab.com/gitlab-org/gitlab-shell \\
        --checkout-dir /tmp/checkouts --model --model-name qwen2.5-coder:3b

The fetched repository code is never imported or executed; only cloned files
are read as text by the scanner.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

# Make the in-repo package importable when this script is run directly.
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reviewer_swarm.pipeline import run_review  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Paste a public repository URL; get an evidence-first JSON review report."
    )
    parser.add_argument("repo_url", help="Public repository URL or owner/repo shorthand.")
    parser.add_argument("--output", default=None,
                        help="Report path. Defaults to <repo>_review.json next to CWD.")
    parser.add_argument("--checkout-dir", default=None,
                        help="Parent directory for the clone. Defaults to a temp directory.")
    parser.add_argument("--model", action="store_true",
                        help="Also run optional local Ollama model agents.")
    parser.add_argument("--model-name", default=None, help="Ollama model tag for --model.")
    parser.add_argument("--rust-binary", default=None,
                        help="Optional built Rust scanner executable.")
    args = parser.parse_args()

    checkout_parent = args.checkout_dir or tempfile.mkdtemp(prefix="reviewer-swarm-")
    try:
        report = run_review(
            "",
            repo_url=args.repo_url,
            use_model=args.model,
            model=args.model_name,
            rust_binary=args.rust_binary,
            checkout_parent=checkout_parent,
        )
    except Exception as exc:  # surface a clean single-line failure for CI/notebooks
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    name = Path(report["repository"]).name or "repository"
    output = Path(args.output or f"{name}_review.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Source URL : {report['source_url']}")
    print(f"Checkout   : {report['repository']}")
    print(f"Scanner    : {report['scanner']}")
    print(f"Static findings: {len(report['static_findings'])}")
    if report.get("model_review") is not None:
        print(f"Model hypotheses: {len(report['model_review']['findings'])} "
              f"(errors: {len(report['model_review']['errors'])})")
    print(f"Report written to: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
