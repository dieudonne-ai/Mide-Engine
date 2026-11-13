"""Prompt templates (French / English) for grounded question answering."""

from __future__ import annotations

from collections.abc import Sequence

SYSTEM = {
    "fr": (
        "Tu es MIDE, un assistant d'analyse business local. Réponds en français, "
        "uniquement à partir des extraits fournis. Cite les sources entre crochets, "
        "par exemple [1]. Si les extraits ne contiennent pas la réponse, dis-le."
    ),
    "en": (
        "You are MIDE, a local business analysis assistant. Answer in English, "
        "using only the provided excerpts. Cite sources in square brackets, "
        "e.g. [1]. If the excerpts do not contain the answer, say so."
    ),
}
CONTEXT_LABEL = {"fr": "Extraits", "en": "Excerpts"}
QUESTION_LABEL = {"fr": "Question", "en": "Question"}
ANSWER_LABEL = {"fr": "Réponse", "en": "Answer"}
NO_CONTEXT = {
    "fr": "Aucune donnée indexée ne correspond à la question. Lancez `mide index` d'abord.",
    "en": "No indexed data matches the question. Run `mide index` first.",
}
SOURCES_LABEL = {"fr": "Sources", "en": "Sources"}


def _lang(language: str) -> str:
    return language if language in SYSTEM else "en"


def format_source(metadata: dict) -> str:
    """Human readable reference of a chunk (item, page, lines)."""
    label = str(metadata.get("item") or metadata.get("source") or "?")
    if metadata.get("page") is not None:
        label += f", p.{metadata['page']}"
    if metadata.get("line_start") is not None:
        label += f", l.{metadata['line_start']}-{metadata.get('line_end', metadata['line_start'])}"
    return label


def build_rag_prompt(question: str, passages: Sequence[tuple[str, dict]], language: str) -> str:
    """Build a prompt with numbered excerpts so the model can cite ``[n]``."""
    lang = _lang(language)
    blocks = [f"[{i}] ({format_source(meta)})\n{text}" for i, (text, meta) in enumerate(passages, 1)]
    return (
        f"{SYSTEM[lang]}\n\n{CONTEXT_LABEL[lang]}:\n" + "\n\n".join(blocks)
        + f"\n\n{QUESTION_LABEL[lang]}: {question}\n{ANSWER_LABEL[lang]}:"
    )
