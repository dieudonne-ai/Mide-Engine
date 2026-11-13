"""Retrieval + grounded answer generation with source citations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from mide.llm.prompts import NO_CONTEXT, build_rag_prompt, format_source
from mide.llm.runtime import LLM
from mide.rag.embeddings import Embedder
from mide.rag.store import SearchHit, VectorStore


@dataclass
class Answer:
    """An answer and the sources (numbered like the ``[n]`` citations) that back it."""

    text: str
    sources: list[str] = field(default_factory=list)
    hits: list[SearchHit] = field(default_factory=list)


class Retriever:
    """Top-k retrieval over the vector store, optionally restricted to one source."""

    def __init__(self, store: VectorStore, embedder: Embedder, k: int = 5) -> None:
        self.store = store
        self.embedder = embedder
        self.k = k

    def retrieve(self, question: str, source: str | None = None) -> list[SearchHit]:
        return self.store.query(question, self.embedder, k=self.k, source=source)


def answer_question(
    question: str,
    retriever: Retriever,
    llm: LLM,
    language: str = "fr",
    source: str | None = None,
    max_tokens: int = 512,
    history: Sequence[tuple[str, str]] = (),
) -> Answer:
    """Retrieve context, ask the LLM and return the answer with its cited sources."""
    hits = retriever.retrieve(question, source=source)
    if not hits:
        return Answer(NO_CONTEXT.get(language, NO_CONTEXT["en"]))
    prompt = build_rag_prompt(question, [(h.text, h.metadata) for h in hits], language, history)
    text = llm.generate(prompt, max_tokens=max_tokens).strip()
    return Answer(text, [f"[{i}] {format_source(h.metadata)}" for i, h in enumerate(hits, 1)], hits)


class ChatSession:
    """Conversation with a short history (only the last ``max_turns`` turns are kept)."""

    def __init__(
        self, retriever: Retriever, llm: LLM, language: str = "fr", max_turns: int = 4
    ) -> None:
        self.retriever = retriever
        self.llm = llm
        self.language = language
        self.max_turns = max_turns
        self.history: list[tuple[str, str]] = []

    def ask(self, question: str, source: str | None = None) -> Answer:
        answer = answer_question(
            question, self.retriever, self.llm, self.language, source=source,
            history=self.history,
        )
        self.history.append((question, answer.text))
        self.history = self.history[-self.max_turns:]
        return answer

    def reset(self) -> None:
        self.history.clear()
