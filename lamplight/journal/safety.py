"""Rule-based safety layer.

This runs on every entry, before and independently of any language model, so
helpline numbers never depend on an API being reachable or on a model
noticing the problem. It is deliberately biased toward showing help: a false
alarm costs a student a few seconds, a miss costs far more.

Three levels:
  OK        nothing concerning
  DISTRESS  clear stress, low mood or overwhelm  -> show helplines
  CRISIS    talk of self-harm or not wanting to live -> helplines first, prominent
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import IntEnum


class Level(IntEnum):
    OK = 0
    DISTRESS = 1
    CRISIS = 2


# Idioms that contain scary words but are not about self-harm.
_IDIOMS = re.compile(
    r"\b(?:die|dying|dead)\s+(?:of|from|with)\s+(?:embarrassment|laughter|shame|boredom|cringe)\b"
    r"|\bkilling\s+it\b|\bkilled\s+it\b",
)

_CRISIS_LATIN = [
    r"\bkill(?:ing)?\s+my\s*self\b",
    r"\bsuicid\w*",
    r"\bend(?:ing)?\s+(?:my\s+life|it\s+all)\b",
    r"\bwant(?:ed|s)?\s+to\s+die\b",
    r"\bwish\s+i\s+(?:was|were)\s+dead\b",
    r"\bbetter\s+off\s+(?:dead|without\s+me)\b",
    r"\bno\s+reason\s+to\s+(?:live|go\s+on)\b",
    r"\b(?:do\s*not|dont|don't|do\s*n't)\s+want\s+to\s+(?:live|be\s+alive|exist|be\s+here|wake\s+up)\b",
    r"\bcan(?:not|'?t)\s+go\s+on\b",
    r"\b(?:hurt|harm|cut)(?:ting)?\s+my\s*self\b",
    r"\bself[\s-]*harm\w*",
    r"\btake\s+my\s+(?:own\s+)?life\b",
    r"\bdisappear\s+forever\b",
    # Romanised Hindi / Hinglish
    r"\bkhud\s*kushi\b",
    r"\bmar\s+jaana\s+chah\w*",
    r"\bmarna\s+chah\w*",
    r"\bjeene\s+ka\s+(?:mann|man|mood)\s+nahi\b",
    r"\bjeena\s+nahi\s+chah\w*",
    r"\bzindagi\s+khatam\b",
    r"\bapni\s+jaan\b",
]

# Devanagari has combining marks that \b does not handle, so plain substrings.
_CRISIS_DEVANAGARI = [
    "आत्महत्या",
    "खुदकुशी",
    "मरना चाहत",
    "मर जाना चाहत",
    "जीना नहीं चाहत",
    "जीने का मन नहीं",
    "जान दे",
]

_CRISIS_RE = [re.compile(p) for p in _CRISIS_LATIN]

# (pattern, weight). Weight 2 = strong signal, 1 = ordinary stress word.
_DISTRESS_TERMS: list[tuple[str, int]] = [
    (r"\bhopeless\w*", 2),
    (r"\bworthless\w*", 2),
    (r"\bpanic\w*", 2),
    (r"\bcan(?:not|'?t)\s+(?:cope|breathe|take\s+(?:it|this)|handle)\b", 2),
    (r"\bbreaking\s+down\b|\bbreakdown\b", 2),
    (r"\bgiv(?:e|ing)\s+up\b", 2),
    (r"\buseless\b", 2),
    (r"\bi(?:'m|\s+am)\s+a\s+failure\b", 2),
    (r"\bhate\s+my\s*self\b", 2),
    (r"\b(?:no\s*one|nobody)\s+(?:cares|understands|likes\s+me)\b", 2),
    (r"\bempty\b|\bnumb\b", 2),
    (r"\bburn(?:t|ed)?[\s-]*out\b|\bburnout\b", 2),
    (r"\bfalling\s+apart\b", 2),
    (r"\b(?:so|all)\s+alone\b", 2),
    (r"\bcrying\b|\bcried\b", 2),
    (r"\bdepress\w*", 2),
    (r"\bstress\w*", 1),
    (r"\banxi\w*", 1),
    (r"\boverwhelm\w*", 1),
    (r"\bexhaust\w*", 1),
    (r"\bcan(?:not|'?t)\s+sleep\b|\binsomnia\b", 1),
    (r"\bscared\b|\bafraid\b|\bterrified\b|\bdread\w*", 1),
    (r"\bpressure\b", 1),
    (r"\bworr(?:y|ied|ies)\b", 1),
    (r"\blonely\b|\bloneliness\b", 1),
    (r"\bsad\b|\bupset\b|\bnervous\b", 1),
    (r"\bfail(?:ed|ing|ure)?\b", 1),
    (r"\bbehind\b", 1),
    (r"\bhate\b", 1),
    # Romanised Hindi / Hinglish
    (r"\bghabrahat\b|\bghabra\w*", 2),
    (r"\bakela\b|\bakeli\b", 1),
    (r"\bthak\s+(?:gaya|gayi|gya|gyi)\b", 1),
    (r"\bneend\s+nahi\b", 2),
    (r"\btension\b", 1),
    (r"\bdar\s+lag\w*", 1),
    (r"\bbahut\s+(?:bura|dukh|udaas)\b|\budaas\b", 1),
]
_DISTRESS_RE = [(re.compile(p), w) for p, w in _DISTRESS_TERMS]


@dataclass(frozen=True)
class Assessment:
    level: Level
    score: int = 0
    signals: tuple[str, ...] = field(default_factory=tuple)

    @property
    def needs_helpline(self) -> bool:
        return self.level >= Level.DISTRESS


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("’", "'").replace("‘", "'").replace("`", "'")
    # "sooo sad" -> "soo sad": squash 3+ repeated letters
    text = re.sub(r"(\w)\1{2,}", r"\1\1", text)
    return text


def assess(text: str, mood: int = 3) -> Assessment:
    """Classify one entry. `mood` is the student's own rating, 1 (heavy) to 5 (bright)."""
    t = _IDIOMS.sub(" ", _normalise(text))

    crisis = [m.group(0) for rx in _CRISIS_RE if (m := rx.search(t))]
    crisis += [s for s in _CRISIS_DEVANAGARI if s in t]
    if crisis:
        return Assessment(Level.CRISIS, score=99, signals=tuple(crisis))

    score = 0
    signals: list[str] = []
    for rx, weight in _DISTRESS_RE:
        m = rx.search(t)
        if m:
            score += weight
            signals.append(m.group(0))

    low_mood = mood <= 2
    if score >= 3 or (low_mood and score >= 1) or mood <= 1:
        return Assessment(Level.DISTRESS, score=score, signals=tuple(signals))
    return Assessment(Level.OK, score=score, signals=tuple(signals))
