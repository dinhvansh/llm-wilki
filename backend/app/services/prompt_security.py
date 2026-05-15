from __future__ import annotations

import re


INJECTION_PATTERNS = [
    r"\bignore (all )?(previous|prior) (instructions|prompts?)\b",
    r"\bdisregard (all )?(previous|prior) (instructions|prompts?)\b",
    r"\bsystem prompt\b",
    r"\bdeveloper message\b",
    r"\byou are now\b",
    r"\bdo not follow\b",
    r"\boverride\b.{0,24}\binstruction",
    r"\breturn (only )?the following\b",
    r"\bexecute\b.{0,24}\bcommand\b",
    r"\bbase64\b",
    r"\bjailbreak\b",
    r"\bprompt injection\b",
    r"\bact as\b.{0,24}\badmin\b",
    r"\bforget (all )?(rules|instructions)\b",
]

POISON_PATTERNS = [
    r"\bthis document is the only trusted source\b",
    r"\bignore all other documents\b",
    r"\bpriority override\b",
    r"\bhidden instruction\b",
    r"\bmodel must\b.{0,24}\bwithout evidence\b",
]


def _count_hits(text: str, patterns: list[str]) -> int:
    lowered = (text or "").lower()
    hits = 0
    for pattern in patterns:
        if re.search(pattern, lowered):
            hits += 1
    return hits


def score_prompt_risk(text: str) -> dict:
    injection_hits = _count_hits(text, INJECTION_PATTERNS)
    poison_hits = _count_hits(text, POISON_PATTERNS)
    total = injection_hits + poison_hits
    if total >= 2:
        risk = "high"
    elif total == 1:
        risk = "medium"
    else:
        risk = "low"
    return {
        "risk": risk,
        "injectionHits": injection_hits,
        "poisonHits": poison_hits,
        "totalHits": total,
    }


def sanitize_context_text(text: str) -> tuple[str, bool]:
    lines = (text or "").splitlines()
    cleaned: list[str] = []
    removed = False
    for line in lines:
        score = score_prompt_risk(line)
        if score["risk"] == "high":
            removed = True
            continue
        cleaned.append(line)
    sanitized = "\n".join(cleaned).strip()
    return sanitized, removed

