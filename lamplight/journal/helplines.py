"""Helplines shown when an entry suggests the student is struggling.

Numbers last checked: November 2026. Helplines change, so re-check them
(especially the secondary ones) before you ship this to real users.
"""
from __future__ import annotations

from dataclasses import dataclass

LAST_CHECKED = "November 2026"


@dataclass(frozen=True)
class Helpline:
    name: str
    display: str  # how the number is shown on screen
    dial: str  # what goes into the tel: link
    note: str
    primary: bool = False


TELE_MANAS = Helpline(
    name="Tele-MANAS",
    display="14416",
    dial="14416",
    note="Government of India. Free, 24x7, in many Indian languages. "
    "Also reachable on 1800-891-4416.",
    primary=True,
)

HELPLINES: tuple[Helpline, ...] = (
    TELE_MANAS,
    Helpline(
        name="Vandrevala Foundation",
        display="+91 9999 666 555",
        dial="+919999666555",
        note="24x7 by call or WhatsApp.",
    ),
    Helpline(
        name="AASRA",
        display="+91 98204 66726",
        dial="+919820466726",
        note="24x7 support for anyone in distress.",
    ),
    Helpline(
        name="KIRAN",
        display="1800-599-0019",
        dial="18005990019",
        note="Toll-free mental health helpline run by the Government of India.",
    ),
    Helpline(
        name="Emergency services",
        display="112",
        dial="112",
        note="If you or someone near you is in immediate danger.",
    ),
)

SECONDARY: tuple[Helpline, ...] = tuple(h for h in HELPLINES if not h.primary)
