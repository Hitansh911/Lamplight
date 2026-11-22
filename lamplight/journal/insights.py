"""Theme detection and the numbers behind the Patterns tab. No LLM needed."""
from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Iterable

THEMES: dict[str, str] = {
    "Exams and grades": r"\b(?:exam|test|marks|grade|cgpa|gpa|result|backlog|viva|jee|neet|upsc|gate|boards?|syllabus|revision|pariksha|study|studying)\w*",
    "Sleep": r"\b(?:sleep|insomnia|awake|nightmare|neend|tired|exhaust)\w*",
    "Family": r"\b(?:parents?|mom|dad|mother|father|family|sibling|brother|sister|papa|mummy|ghar)\b",
    "Friends and belonging": r"\b(?:friends?|roommate|lonely|alone|left\s+out|crush|relationship|breakup|dost|akela|akeli)\b",
    "Money": r"\b(?:fees?|money|loan|scholarship|rent|afford|paise|expensive)\b",
    "Future and career": r"\b(?:career|future|job|placements?|internship|interview|resume|degree|admission)\w*",
    "Body and health": r"\b(?:headache|sick|ill|appetite|weight|body|chest|health|exercise|eating)\b",
    "Focus and deadlines": r"\b(?:procrastinat\w*|focus|phone|scroll\w*|distract\w*|motivation|lazy|deadline|assignment|submit\w*)\b",
}
_THEME_RE = {name: re.compile(p, re.I) for name, p in THEMES.items()}


def detect_themes(text: str) -> list[str]:
    return [name for name, rx in _THEME_RE.items() if rx.search(text)]


def _day(entry: dict) -> date:
    return datetime.fromisoformat(entry["created_at"]).date()


def streak(entries: Iterable[dict], today: date | None = None) -> int:
    """Consecutive days with at least one page, counting back from today
    (or from yesterday if nothing has been written yet today)."""
    today = today or date.today()
    days = {_day(e) for e in entries}
    cursor = today if today in days else today - timedelta(days=1)
    count = 0
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def mood_by_day(
    entries: Iterable[dict], days: int = 28, today: date | None = None
) -> list[tuple[date, float | None]]:
    """Average mood for each of the last `days` days, oldest first. None = no page."""
    today = today or date.today()
    buckets: dict[date, list[int]] = {}
    for e in entries:
        buckets.setdefault(_day(e), []).append(int(e["mood"]))
    out: list[tuple[date, float | None]] = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        vals = buckets.get(d)
        out.append((d, sum(vals) / len(vals) if vals else None))
    return out


def theme_counts(
    entries: Iterable[dict], days: int = 30, today: date | None = None
) -> list[tuple[str, int]]:
    today = today or date.today()
    cutoff = today - timedelta(days=days - 1)
    c: Counter[str] = Counter()
    for e in entries:
        if _day(e) >= cutoff:
            c.update(e.get("themes") or [])
    return c.most_common()


def weekly_mood(
    entries: Iterable[dict], today: date | None = None
) -> tuple[float | None, float | None]:
    """(average mood in the last 7 days, average in the 7 days before)."""
    today = today or date.today()
    this_w: list[int] = []
    prev_w: list[int] = []
    for e in entries:
        age = (today - _day(e)).days
        if 0 <= age < 7:
            this_w.append(int(e["mood"]))
        elif 7 <= age < 14:
            prev_w.append(int(e["mood"]))
    avg = lambda v: sum(v) / len(v) if v else None  # noqa: E731
    return avg(this_w), avg(prev_w)
