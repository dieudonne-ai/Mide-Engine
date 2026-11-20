"""French typography and date helpers shared by the CLI messages and the report."""

from __future__ import annotations

import re
from datetime import date

NBSP = " "

FRENCH_MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                 "août", "septembre", "octobre", "novembre", "décembre")

_SPACE_BEFORE_SIGN = re.compile(r" (?=[:;?!](?:\s|$|[\"'`)]))")
_ISO_DATE = re.compile(r"(?<![\d-])(\d{4})-(\d{2})-(\d{2})(?![\d-])")
_YM = r"(?<![\d-])(\d{4})-(\d{2})(?![\d-])"
_YEAR_MONTH_RANGE = re.compile(_YM + r" -> " + _YM)
_YEAR_MONTH = re.compile(_YM)


def french_spacing(text: str) -> str:
    """Make the space before ':', ';', '?' and '!' non-breaking ('Erreur : x' -> 'Erreur : x').

    Only an ordinary space already written before the sign is replaced, so it is meant
    for message templates (the values filled in later are left as they are). Signs
    without a space before them ('10:30', 'http://', 'a:b') are untouched."""
    return _SPACE_BEFORE_SIGN.sub(NBSP, text)


def french_date(day: date) -> str:
    """Long French date: 2024-10-02 -> '2 octobre 2024', 2024-10-01 -> '1er octobre 2024'."""
    number = "1er" if day.day == 1 else str(day.day)
    return f"{number} {FRENCH_MONTHS[day.month - 1]} {day.year}"


def french_dates(text: str) -> str:
    """Spell out every ISO date in ``text``: 'le 2024-10-02' -> 'le 2 octobre 2024'.

    Year-months ('2024-10') and strings that are not real dates ('2024-13-40') are kept."""
    def spell(m: re.Match[str]) -> str:
        try:
            return french_date(date(int(m[1]), int(m[2]), int(m[3])))
        except ValueError:
            return m[0]
    return _ISO_DATE.sub(spell, text)


def french_month(year: int, month: int) -> str:
    """French month and year: (2024, 10) -> 'octobre 2024'. Raises ValueError for a bad month."""
    if not 1 <= month <= 12:
        raise ValueError(f"invalid month: {month}")
    return f"{FRENCH_MONTHS[month - 1]} {year}"


def french_year_months(text: str) -> str:
    """Spell out ISO year-months in ``text``: '2024-10 -> 2024-12' -> 'octobre 2024 à décembre 2024'.

    A lone year-month ('2024-10') becomes 'octobre 2024'. Full dates ('2024-10-02'),
    invalid months ('2024-13') and longer digit runs are kept."""
    def month(year: str, number: str) -> str:
        return french_month(int(year), int(number))

    def spell_range(m: re.Match[str]) -> str:
        try:
            return f"{month(m[1], m[2])} à {month(m[3], m[4])}"
        except ValueError:
            return m[0]

    def spell(m: re.Match[str]) -> str:
        try:
            return month(m[1], m[2])
        except ValueError:
            return m[0]
    return _YEAR_MONTH.sub(spell, _YEAR_MONTH_RANGE.sub(spell_range, text))
