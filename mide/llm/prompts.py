"""Prompt templates (French / English) for retrieval-augmented answers."""

from __future__ import annotations

from collections.abc import Sequence

from mide.rag.retriever import Passage

_SYSTEM = {
    "fr": (
        "Tu es MIDE, un assistant d'analyse business. Réponds en français, uniquement à partir "
        "des extraits fournis. Cite tes sources avec leur numéro entre crochets, par exemple [1]. "
        "Si les extraits ne contiennent pas la réponse, dis-le clairement."
    ),
    "en": (
        "You are MIDE, a business analysis assistant. Answer in English, using only the "
        "provided excerpts. Cite your sources with their number in square brackets, e.g. [1]. "
        "If the excerpts do not contain the answer, say so clearly."
    ),
}
_LABELS = {
    "fr": {"excerpts": "Extraits", "question": "Question", "answer": "Réponse", "none": "(aucun extrait)"},
    "en": {"excerpts": "Excerpts", "question": "Question", "answer": "Answer", "none": "(no excerpt)"},
}


def _lang(language: str) -> str:
    return language if language in _SYSTEM else "fr"


def format_passages(passages: Sequence[Passage]) -> str:
    """Render numbered excerpts; the number is the citation id."""
    return "\n\n".join(f"[{p.number}] ({p.citation})\n{p.text}" for p in passages)


def build_rag_prompt(question: str, passages: Sequence[Passage], language: str = "fr") -> str:
    """Build the full prompt sent to the LLM."""
    lang = _lang(language)
    labels = _LABELS[lang]
    context = format_passages(passages) or labels["none"]
    return (
        f"{_SYSTEM[lang]}\n\n{labels['excerpts']}:\n{context}\n\n"
        f"{labels['question']}: {question}\n{labels['answer']}:"
    )


def sources_footer(passages: Sequence[Passage]) -> str:
    """List the cited sources under the answer."""
    if not passages:
        return ""
    lines = [f"[{p.number}] {p.citation}" for p in passages]
    return "Sources:\n" + "\n".join(lines)
