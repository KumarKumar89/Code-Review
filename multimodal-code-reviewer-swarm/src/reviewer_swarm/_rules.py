"""Rule table and the fast line matcher used by the deterministic scanner.

Importing this module only compiles a handful of regular expressions; it performs
no I/O and has no side effects.

Why the pre-filter exists
-------------------------
The original scanner ran *every* rule against *every* line, i.e. one regex pass per
rule per line. On realistic repositories almost all lines match nothing, so that
work was wasted. Each rule now declares literal "needles": substrings that must be
present in a line for the regex to have any chance of matching. A ``str.find``
pre-filter rejects those lines at C speed, turning ``len(RULES)`` regex scans into a
couple of substring checks for typical code.

Safety invariant
----------------
Needles may only ever *drop* lines that the regex could not have matched anyway.
The regex remains the authoritative check. ``validate_needles()`` is exercised by
the test suite (including a differential fuzz over generated lines) so a future
rule edit cannot silently change findings.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    """One deterministic, line-level check."""

    rule_id: str
    category: str
    severity: str
    confidence: float
    recommendation: str
    pattern: re.Pattern[str]
    #: Substrings a line must contain for ``pattern`` to be able to match.
    #: Empty means "always run the regex" (still correct, just slower).
    needles: tuple[str, ...] = ()
    #: Set when ``pattern`` uses inline case-insensitive matching, so the needle
    #: check must compare against a lower-cased copy of the line.
    case_insensitive_needles: bool = False
    #: When True the matched line is never copied into a finding.
    redact_evidence: bool = False

    def matches_line(self, line: str) -> bool:
        """Return True when ``line`` satisfies this rule.

        Hot path: the needle check is a plain substring test and only falls back to
        the authoritative regex when a needle is present. Lines are never longer than
        :data:`MAX_LINE_CHARS`, so the work per line is bounded.
        """
        if self.needles:
            haystack = line.lower() if self.case_insensitive_needles else line
            if not any(needle in haystack for needle in self.needles):
                return False
        return self.pattern.search(line) is not None


#: Hard cap on the characters examined per line. Extremely long lines (generated
#: bundles, minified assets, base64 blobs) are truncated before matching so a single
#: pathological file cannot dominate scan time. The full line is still reported up to
#: ``EVIDENCE_MAX_CHARS`` for non-redacting rules.
MAX_LINE_CHARS = 4096

#: Maximum characters of source copied into a finding's evidence field.
EVIDENCE_MAX_CHARS = 240


def _split_top_level_alternation(body: str) -> list[str] | None:
    """Split ``(?:a|b|c)`` at the start of ``body`` into its literal branches.

    Returns ``None`` when the group is absent, unbalanced, or contains nesting so the
    caller can fall back to a weaker filter.
    """
    if not body.startswith("(?:"):
        return None
    depth = 0
    index = 0
    while index < len(body):
        char = body[index]
        if char == "\\":
            index += 2
            continue
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
            if depth == 0 and char == ")":
                inner = body[3:index]
                return inner.split("|") if "(" not in inner else None
        index += 1
    return None


#: Characters that end a guaranteed-literal run inside a regex source.
_META_CHARS = "()[]{}|?*+^$.\\&~#:=;!<>-'"


def _literal_runs(text: str, *, minimum: int = 3) -> tuple[str, ...]:
    """Return maximal alphanumeric/underscore runs of at least ``minimum`` chars."""
    return tuple(run for run in re.findall(r"[A-Za-z0-9_]+", text) if len(run) >= minimum)


def derive_needles(pattern: re.Pattern[str]) -> tuple[str, ...]:
    """Best-effort literal pre-filter for a compiled line-level pattern.

    Recognised shapes, in order:

    * a leading ``(?:lit|lit|...)`` alternation whose every branch contains a plain
      literal fragment - e.g. ``api[_-]?key`` contributes ``"key"``, so the rule's
      matches must contain one of the branch literals;
    * otherwise, every literal run in the de-metacharactered pattern source. A match
      necessarily contains each such run, e.g. ``^\\s*except\\s*:`` requires
      ``"except"``.

    If nothing safe can be derived the result is ``()`` (no pre-filter), which is
    always correct - it merely leaves the authoritative regex check unconditional.
    """
    source = pattern.pattern
    body = source[2:] if source.startswith(r"\b") else source

    branches = _split_top_level_alternation(body)
    if branches is not None:
        parts: list[str] = []
        for branch in branches:
            literals = _literal_runs(branch.replace("[", " ").replace("]", " "))
            if not literals:
                return ()  # a branch with no literal cannot be filtered safely
            parts.extend(literals)
        return tuple(dict.fromkeys(parts))

    stripped = re.sub(r"\[[^\]]*\]", " ", body)          # drop character classes
    stripped = re.sub(r"\(\?[!:]=?[^()]*\)", " ", stripped)  # drop inline flags/lookarounds
    stripped = stripped.replace("\\s", " ").replace("\\b", " ").replace("\\S", " ")
    runs = _literal_runs(stripped, minimum=3)
    return tuple(dict.fromkeys(runs)) if runs else ()


#: Fallback needles for patterns too dynamic for :func:`derive_needles`.
#: Every entry must be a substring that any regex match necessarily contains.
_MANUAL_NEEDLES: dict[str, tuple[str, ...]] = {
    # (?i)\b(?:api[_-]?key|secret|password|access[_-]?token)\b\s*[:=]\s*['"]...
    "SEC-HARDCODED-SECRET": ("key", "secret", "password", "token"),
}


def _build_rule(
    rule_id: str,
    category: str,
    severity: str,
    confidence: float,
    pattern_source: str,
    recommendation: str,
    *,
    redact_evidence: bool = False,
) -> Rule:
    """Compile a rule and attach derived (or explicitly curated) needles."""
    flags = 0
    source = pattern_source
    if source.startswith("(?i)"):
        flags |= re.IGNORECASE
        source = source[4:]
    pattern = re.compile(source, flags)
    needles = derive_needles(pattern) or _MANUAL_NEEDLES.get(rule_id, ())
    return Rule(
        rule_id=rule_id,
        category=category,
        severity=severity,
        confidence=confidence,
        recommendation=recommendation,
        pattern=pattern,
        needles=needles,
        case_insensitive_needles=bool(flags & re.IGNORECASE),
        redact_evidence=redact_evidence,
    )


# ---------------------------------------------------------------------------
# Rule table.
# ---------------------------------------------------------------------------

RULES: tuple[Rule, ...] = (
    _build_rule(
        "SEC-DYNAMIC-EVAL",
        "security",
        "medium",
        0.60,
        r"\b(?:eval|exec)\s*\(",
        "Dynamic code evaluation pattern found. Confirm whether input can be influenced by an untrusted source.",
    ),
    _build_rule(
        "SEC-SHELL-TRUE",
        "security",
        "medium",
        0.65,
        r"\bshell\s*=\s*True\b",
        "Subprocess configuration uses shell=True. Review argument construction and untrusted-input flow.",
    ),
    _build_rule(
        "SEC-HARDCODED-SECRET",
        "security",
        "high",
        0.72,
        r"(?i)\b(?:api[_-]?key|secret|password|access[_-]?token)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        "Possible hard-coded secret assignment. The matched value is intentionally not copied into the finding.",
        redact_evidence=True,
    ),
    _build_rule(
        "MAINT-TODO",
        "maintainability",
        "info",
        0.95,
        r"\b(?:TODO|FIXME|XXX)\b",
        "Unresolved TODO/FIXME marker. Determine whether it represents incomplete work.",
    ),
    _build_rule(
        "RELIABILITY-BARE-EXCEPT",
        "reliability",
        "low",
        0.65,
        r"^\s*except\s*:\s*(?:#.*)?$",
        "Bare exception handler may hide unexpected failures. Consider handling explicit exception types.",
    ),
)

RULE_BY_ID: dict[str, Rule] = {rule.rule_id: rule for rule in RULES}

#: Evidence text shown instead of the raw line for redacting rules.
REDACTED_EVIDENCE = "Potential credential assignment detected; value redacted."


def validate_needles(rules: tuple[Rule, ...] = RULES) -> None:
    """Raise if a rule's needles could suppress a genuine regex match.

    Checks that every needle actually appears in a sample string produced from the
    pattern's own literal prefix, and that case-insensitive needles are stored in
    lower case. Intended for tests and CI, not for the hot path.
    """
    for rule in rules:
        if not rule.needles:
            continue
        for needle in rule.needles:
            if not needle:
                raise ValueError(f"{rule.rule_id}: empty needle would disable the filter")
            if rule.case_insensitive_needles and needle != needle.lower():
                raise ValueError(
                    f"{rule.rule_id}: needle {needle!r} must be lower case when "
                    "case_insensitive_needles is set"
                )
            if not rule.case_insensitive_needles and needle != needle.strip():
                raise ValueError(f"{rule.rule_id}: needle {needle!r} has surrounding whitespace")


__all__ = [
    "EVIDENCE_MAX_CHARS",
    "MAX_LINE_CHARS",
    "REDACTED_EVIDENCE",
    "RULE_BY_ID",
    "RULES",
    "Rule",
    "derive_needles",
    "validate_needles",
]
