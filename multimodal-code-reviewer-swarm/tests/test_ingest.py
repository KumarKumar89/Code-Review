"""Tests for the public-repository URL ingestion layer (reviewer_swarm.ingest)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from reviewer_swarm.ingest import (
    RepoRef,
    RepositoryInputError,
    fetch_repository,
    normalize_repo_input,
    redact_repo_url,
)
from reviewer_swarm.pipeline import run_review


# ---------------------------------------------------------------------------
# Input parsing / validation
# ---------------------------------------------------------------------------

def test_github_url_normalizes_to_clone_url() -> None:
    ref = normalize_repo_input("https://github.com/psf/requests")
    assert ref == RepoRef(
        url="https://github.com/psf/requests.git",
        host="github.com",
        owner="psf",
        name="requests",
        ref=None,
        is_git_url=True,
    )


def test_trailing_slash_and_dotgit_are_tolerated() -> None:
    a = normalize_repo_input("https://github.com/owner/repo/")
    b = normalize_repo_input("https://github.com/owner/repo.git")
    assert a.url == b.url == "https://github.com/owner/repo.git"


def test_owner_repo_shorthand_expands_to_github() -> None:
    ref = normalize_repo_input("octocat/Hello-World")
    assert ref.url == "https://github.com/octocat/Hello-World.git"
    assert ref.owner == "octocat"


def test_tree_branch_is_captured_and_path_cleaned() -> None:
    ref = normalize_repo_input("https://github.com/owner/repo/tree/dev/src/module")
    assert ref.ref == "dev"
    assert ref.url == "https://github.com/owner/repo.git"


def test_gitlab_and_bitbucket_urls_supported() -> None:
    gitlab = normalize_repo_input("https://gitlab.com/group/project")
    bitbucket = normalize_repo_input("https://bitbucket.org/team/repo")
    assert gitlab.host == "gitlab.com" and gitlab.is_git_url
    assert bitbucket.host == "bitbucket.org" and bitbucket.is_git_url


def test_generic_direct_git_url_accepted() -> None:
    ref = normalize_repo_input("https://code.example.com/team/toolkit.git")
    assert ref.url == "https://code.example.com/team/toolkit.git"
    assert ref.name == "toolkit"


@pytest.mark.parametrize(
    "bad_input",
    [
        "",
        None,
        "ssh://git@github.com/owner/repo.git",       # non-http scheme
        "file:///etc/passwd",                          # local path smuggling
        "https://user:token@github.com/owner/repo",    # embedded credentials
        "https://github.com/",                         # no repository name
        "not a url at all here",                       # whitespace/garbage
    ],
)
def test_invalid_inputs_rejected(bad_input: str | None) -> None:
    with pytest.raises(RepositoryInputError):
        normalize_repo_input(bad_input)


def test_redact_repo_url_masks_placeholders() -> None:
    assert redact_repo_url("https://x@gitlab.com/o/r?token=xxxxx") .count("xxxxx") == 0
    assert "***" in redact_repo_url("https://host/repo?access_token=xxxxxxxxxx")


# ---------------------------------------------------------------------------
# Fetch behaviour (network mocked; unit tests must stay offline & deterministic)
# ---------------------------------------------------------------------------

def _fake_clone_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd, *args, **kwargs):  # noqa: ANN001, ARG001
        destination = Path(cmd[-1])
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "example.py").write_text("eval(user_input)\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)


def test_fetch_repository_uses_shallow_clone(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):  # noqa: ANN001, ARG001
        calls.append(list(cmd))
        destination = Path(cmd[-1])
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "example.py").write_text("eval(user_input)\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    root, ref = fetch_repository("https://github.com/psf/requests", dest_parent=tmp_path)
    assert "--depth" in calls[0] and "--single-branch" in calls[0]
    assert ref.name == "requests"
    assert (root / "example.py").exists()


def test_pipeline_end_to_end_with_mocked_clone(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _fake_clone_ok(monkeypatch)
    report = run_review("", repo_url="https://github.com/psf/requests", checkout_parent=tmp_path)
    assert report["source_url"] == "https://github.com/psf/requests"
    rule_ids = {item["rule_id"] for item in report["static_findings"]}
    assert "SEC-DYNAMIC-EVAL" in rule_ids


def test_pipeline_rejects_both_path_and_url(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not both"):
        run_review(str(tmp_path), repo_url="https://github.com/psf/requests")


def test_pipeline_rejects_empty_url() -> None:
    with pytest.raises(RepositoryInputError):
        run_review("", repo_url="   ")
