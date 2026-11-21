"""Deterministic quality gates for AI-tailored resume drafts.

These checks are conservative: when a draft drops source facts or adds unsupported
skills, the caller should use the evidence-preserving local fallback.
"""
import re
from dataclasses import dataclass

from app.services.matcher import extract_skills


@dataclass(frozen=True)
class ResumeQualityResult:
    passed: bool
    issues: tuple[str, ...]


DATE_RE = re.compile(
    r"(?i)\b(?:19|20)\d{2}\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
    r"\s+\d{4}\b|\b\d{1,2}[/-]\d{4}\b"
)
NUMBER_RE = re.compile(r"(?<!\w)(?:\d+(?:[.,]\d+)?\s?(?:%|x|k|m|gb|mb|ms|s|hours?|days?|users?|records?)?)(?!\w)", re.I)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>]+")


def validate_tailored_resume(source_text: str, tailored_text: str) -> ResumeQualityResult:
    """Reject empty, unsupported-skill, or material-fact-dropping AI drafts."""
    issues = []
    source = source_text or ""
    draft = tailored_text or ""
    if len(draft.strip()) < 250:
        issues.append("Draft is too short to be a complete resume.")

    source_skills = set(extract_skills(source))
    draft_skills = set(extract_skills(draft))
    unsupported = sorted(draft_skills - source_skills)
    if unsupported:
        issues.append("Draft introduces skills not evidenced in the source: " + ", ".join(unsupported))

    source_dates = set(DATE_RE.findall(source))
    draft_dates = set(DATE_RE.findall(draft))
    missing_dates = sorted(source_dates - draft_dates)
    if missing_dates:
        issues.append("Draft omits source dates: " + ", ".join(missing_dates))

    source_numbers = set(NUMBER_RE.findall(source))
    draft_numbers = set(NUMBER_RE.findall(draft))
    missing_numbers = sorted(source_numbers - draft_numbers)
    if missing_numbers:
        issues.append("Draft omits source metrics or numeric facts: " + ", ".join(missing_numbers[:12]))

    source_emails = {value.casefold() for value in EMAIL_RE.findall(source)}
    draft_emails = {value.casefold() for value in EMAIL_RE.findall(draft)}
    if source_emails - draft_emails:
        issues.append("Draft omits one or more source email addresses.")

    source_urls = {value.rstrip(".,;:)").casefold() for value in URL_RE.findall(source)}
    draft_urls = {value.rstrip(".,;:)").casefold() for value in URL_RE.findall(draft)}
    if source_urls - draft_urls:
        issues.append("Draft omits one or more source profile or portfolio URLs.")

    return ResumeQualityResult(passed=not issues, issues=tuple(issues))
