"""French typography helpers shared by the CLI messages."""

from __future__ import annotations

import re

NBSP = " "

_SPACE_BEFORE_SIGN = re.compile(r" (?=[:;?!](?:\s|$|[\"'`)]))")


def french_spacing(text: str) -> str:
    """Make the space before ':', ';', '?' and '!' non-breaking ('Erreur : x' -> 'Erreur : x').

    Only an ordinary space already written before the sign is replaced, so it is meant
    for message templates (the values filled in later are left as they are). Signs
    without a space before them ('10:30', 'http://', 'a:b') are untouched."""
    return _SPACE_BEFORE_SIGN.sub(NBSP, text)
