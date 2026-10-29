"""Fetch a public repository from its URL so it can be reviewed locally.

This module turns a pasted repository link (GitHub, GitLab, Bitbucket, or any
direct ``*.git`` / archive URL) into a local checkout directory. It is shared by
the CLI pipeline and the Colab notebook so both accept exactly the same input.

Safety properties:

1. **Public URLs only.** Credentials embedded in a URL (``https://user:token@…``)
   are rejected outright; private repositories must be cloned outside this tool.
2. **No arbitrary paths.** Only http(s) URLs are accepted; local paths are handled
   directly by :func:`reviewer_swarm.pipeline.run_review`.
3. **Bounded clones.** Shallow single-branch clones with hard timeouts keep the
   download small and predictable.

The fetched tree is then scanned by the deterministic scanner, which never
executes target code - cloning a repository does not run any of its setup,
build, or notebook code.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen

MAX_ARCHIVE_BYTES = 500 * 1000 * 1000  # 500 MB cap for direct-archive downloads
_CLONE_TIMEOUT_SECONDS = int(os.getenv("REVIEW_CLONE_TIMEOUT", "600"))
_DOWNLOAD_TIMEOUT_SECONDS = int(os.getenv("REVIEW_DOWNLOAD_TIMEOUT", "300"))

_GIT_HOSTS = frozenset({"github.com", "www.github.com", "gitlab.com", "bitbucket.org"})
_USERINFO_RE = re.compile(r"://[^/@]*:[^/@]*@")
_PLACEHOLDER_RE = re.compile(r"(?:x{5,}|<[^>]+>|\*{3,})")


class RepositoryInputError(ValueError):
    """Raised when the pasted repository URL is missing, malformed, or unsafe."""


@dataclass(frozen=True)
class RepoRef:
    """A parsed, validated reference to a public git repository."""

    url: str            # normalized clone/archive URL (ends with .git when derivable)
    host: str           # e.g. "github.com" ("" for generic hosts)
    owner: str          # e.g. "octocat" ("" when unknown)
    name: str           # e.g. "hello-world"
    ref: str | None     # branch/tag from a pasted browse URL, if any
    is_git_url: bool    # True when a git clone URL could be constructed

    @property
    def label(self) -> str:
        return f"{self.owner}/{self.name}" if self.owner else self.name


def normalize_repo_input(raw: str | None) -> RepoRef:
    """Parse and validate a pasted repository string into a :class:`RepoRef`.

    Accepts full browser URLs (with or without ``.git``, with ``tree/<ref>/…``
    paths), bare ``owner/name`` shorthand on GitHub, and any direct ``*.git``
    or archive URL on another host. Rejects non-http(s) schemes and URLs that
    embed credentials.
    """
    text = (raw or "").strip().strip("'\"").rstrip("/")
    if not text:
        raise RepositoryInputError("Repository input is empty. Paste a public repository URL.")

    # Bare owner/repo shorthand (no scheme, no spaces, exactly one slash).
    if re.fullmatch(r"[\w.-]+/[\w.-]+", text):
        text = f"https://github.com/{text}"

    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RepositoryInputError(
            "Only public http(s) repository URLs are supported. "
            "Example: https://github.com/owner/repository"
        )
    if parsed.username or _USERINFO_RE.search(text):
        raise RepositoryInputError(
            "The URL contains embedded credentials. Remove them; this tool reviews "
            "public repositories only."
        )
    if any(ch.isspace() for ch in parsed.path):
        raise RepositoryInputError("The URL contains whitespace and cannot be parsed.")

    host = parsed.netloc.lower()
    path_parts = [unquote(part) for part in parsed.path.split("/") if part]

    ref: str | None = None
    if host in _GIT_HOSTS and len(path_parts) >= 2:
        # Strip browse suffixes like /tree/main/src or /blob/HEAD/file.py
        lowered = [part.lower() for part in path_parts]
        for marker in ("tree", "blob", "src"):
            if marker in lowered[2:]:
                index = 2 + lowered[2:].index(marker)
                if index + 1 < len(path_parts):
                    ref = path_parts[index + 1]
                path_parts = path_parts[:index]
                break

    if not path_parts:
        raise RepositoryInputError("Could not determine a repository name from the URL.")

    last = path_parts[-1]
    if last.endswith(".git"):
        last = last[: -len(".git")]
    if not last:
        raise RepositoryInputError("Could not determine a repository name from the URL.")

    owner = path_parts[-2] if len(path_parts) >= 2 else ""
    clean_path = "/".join(path_parts[:2]) if host in _GIT_HOSTS and len(path_parts) >= 2 \
        else "/".join(path_parts)
    base_url = f"{parsed.scheme}://{parsed.netloc}/{clean_path}"
    git_url = base_url if base_url.endswith(".git") else f"{base_url}.git"
    is_git_url = host in _GIT_HOSTS or base_url.endswith(".git")

    return RepoRef(url=git_url, host=host, owner=owner, name=last, ref=ref, is_git_url=is_git_url)


def _run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    if shutil.which("git") is None:
        raise RuntimeError("git executable not found; install git or use the ZIP upload path.")
    env = dict(os.environ)
    # Never let git block on an interactive prompt (auth, SSL errors, ...):
    # fail fast instead so the archive fallback (or a clean error) takes over.
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.setdefault("GIT_ASKPASS", "echo")
    env["GCM_INTERACTIVE"] = "never"
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=_CLONE_TIMEOUT_SECONDS,
        check=False,
        env=env,
    )


def _clone(ref: RepoRef, destination: Path) -> None:
    command = ["clone", "--depth", "1", "--single-branch"]
    if ref.ref:
        command += ["--branch", ref.ref]
    command += ["--", ref.url, str(destination)]
    result = _run_git(command)
    if result.returncode != 0 and ref.ref:
        # The browse path may carry a commit SHA or sub-path segment that is not
        # a valid --branch value; retry the default branch instead.
        fallback = ["clone", "--depth", "1", "--single-branch", "--", ref.url, str(destination)]
        result = _run_git(fallback)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "")[-800:]
        raise RuntimeError(
            f"git clone failed for {ref.url} (exit {result.returncode}). "
            f"Is the repository public? Details: {detail}"
        )


def _safe_extract_zip(archive_path: Path, destination: Path) -> None:
    root_resolved = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if target != root_resolved and root_resolved not in target.parents:
                raise ValueError(f"Unsafe archive path rejected: {member.filename!r}")
            if member.file_size > 10_000_000:
                raise ValueError(f"Archive member is too large: {member.filename!r}")
        archive.extractall(destination)


def _safe_extract_tar(archive_path: Path, destination: Path) -> None:
    root_resolved = destination.resolve()
    with tarfile.open(archive_path) as archive:
        for member in archive.getmembers():
            if not (member.isfile() or member.isdir()):
                raise ValueError(f"Unsafe archive member type: {member.name!r}")
            target = (destination / member.name).resolve()
            if target != root_resolved and root_resolved not in target.parents:
                raise ValueError(f"Unsafe archive path rejected: {member.name!r}")
            if member.isfile() and member.size > 10_000_000:
                raise ValueError(f"Archive member is too large: {member.name!r}")
        archive.extractall(destination)


def _download_archive(ref: RepoRef, destination: Path) -> None:
    """Fallback path: download a source-archive ZIP/tarball over plain HTTP."""
    candidates: list[str] = []
    browse = ref.url[: -len(".git")] if ref.url.endswith(".git") else ref.url
    branch = ref.ref or "HEAD"
    if ref.host in {"github.com", "www.github.com"}:
        candidates.append(f"{browse}/archive/refs/heads/{quote(branch)}.zip")
        candidates.append(f"{browse}/archive/HEAD.zip")
    elif ref.host == "gitlab.com":
        candidates.append(f"{browse}/-/archive/{quote(branch)}/{ref.name}.zip")
        candidates.append(f"{browse}/-/archive/HEAD/{ref.name}.zip")
    elif ref.host == "bitbucket.org":
        candidates.append(f"{browse}/get/{quote(branch)}.zip")
    else:
        candidates.extend([f"{ref.url.replace('.git', '')}.zip", f"{browse}.tar.gz"])

    if not candidates:
        raise RuntimeError(
            f"No archive-download strategy is known for host '{ref.host}' and git is unavailable."
        )

    last_error: Exception | None = None
    for url in candidates:
        try:
            request = Request(url, headers={"User-Agent": "reviewer-swarm-ingest/0.1"})
            with urlopen(request, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response:
                payload = response.read(MAX_ARCHIVE_BYTES + 1)
            if len(payload) > MAX_ARCHIVE_BYTES:
                raise RuntimeError(f"Archive at {url} exceeds the {MAX_ARCHIVE_BYTES} byte limit.")
            suffix = ".tar.gz" if url.endswith((".tar.gz", ".tgz")) else ".zip"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
                handle.write(payload)
                temp_path = Path(handle.name)
            try:
                if suffix == ".zip":
                    _safe_extract_zip(temp_path, destination)
                else:
                    _safe_extract_tar(temp_path, destination)
            finally:
                temp_path.unlink(missing_ok=True)
            return
        except Exception as exc:  # try the next candidate URL
            last_error = exc
    raise RuntimeError(f"All archive download attempts failed. Last error: {last_error}")


def fetch_repository(
    repo_url: str | None,
    *,
    dest_parent: str | Path | None = None,
    clean_existing: bool = True,
) -> tuple[Path, RepoRef]:
    """Clone (or archive-download) a public repository into a fresh local directory.

    Returns ``(checkout_directory, parsed_ref)``. The directory contains only the
    checked-out sources; nothing inside it is executed during the fetch.
    """
    ref = normalize_repo_input(repo_url)
    parent = Path(dest_parent).expanduser().resolve() if dest_parent else Path(tempfile.gettempdir())
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / f"repo_{re.sub(r'[^A-Za-z0-9._-]', '_', ref.name)}"
    if destination.exists() and clean_existing:
        shutil.rmtree(destination)
    if destination.exists():
        raise RepositoryInputError(f"Destination already exists: {destination}")
    destination.mkdir(parents=True)

    git_error: Exception | None = None
    if ref.is_git_url:
        try:
            _clone(ref, destination)
            return destination, ref
        except Exception as exc:
            git_error = exc
    try:
        _download_archive(ref, destination)
        return destination, ref
    except Exception as archive_error:
        if git_error is not None:
            raise RuntimeError(
                f"Clone failed ({git_error}); archive fallback failed ({archive_error})"
            ) from archive_error
        raise


def redact_repo_url(raw: str | None) -> str:
    """Return a display-safe version of a user-entered URL (credentials masked)."""
    text = (raw or "").strip()
    return _PLACEHOLDER_RE.sub("***", text)


# ---------------------------------------------------------------------------
# Self-contained helpers for the Colab notebook
#
# The notebook runs an inline copy of the scanner and must not depend on this
# package being importable, so these functions use only the standard library
# plus ``ipython_pygments_lexers``-free IPython widgets imported lazily.
# ---------------------------------------------------------------------------

def prompt_and_fetch(dest_parent: str | Path | None = None) -> tuple[Path, RepoRef]:
    """Show a text input box in Jupyter/Colab, fetch the pasted repo, return its path.

    Falls back to ``input()`` when IPython is unavailable (plain terminals).
    """
    try:
        from ipywidgets import Textarea  # type: ignore
        from IPython.display import display  # type: ignore

        widget = Textarea(
            value="",
            placeholder="https://github.com/owner/repository  (or owner/repo, GitLab/Bitbucket link, direct .git URL)",
            description="Repo URL:",
            layout={"width": "70%"},
        )
        display(widget)
        raw_input = widget.value
    except Exception:  # pragma: no cover - non-notebook environments
        raw_input = input("Paste a public repository URL: ")

    ref = normalize_repo_input(raw_input)
    print(f"Fetching {ref.url} ...")
    root, fetched_ref = fetch_repository(ref.url, dest_parent=dest_parent)
    print("Checkout directory:", root)
    return root, fetched_ref
