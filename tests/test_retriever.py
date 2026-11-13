"""End-to-end RAG tests with FakeLLM and FakeEmbedder (no real model)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from mide.cli import app
from mide.llm.prompts import build_rag_prompt, format_source
from mide.llm.runtime import FakeLLM
from mide.rag.chunking import Chunk
from mide.rag.retriever import Retriever, answer_question
from mide.rag.store import VectorStore


@pytest.fixture
def retriever(tmp_path, fake_embedder):
    store = VectorStore(tmp_path / "idx")
    store.add_document(
        "notes.md",
        [Chunk("The marketing budget for Q3 is 5000 euros.",
               {"source": "s1", "line_start": 1, "line_end": 2})],
        fake_embedder,
    )
    store.add_document(
        "hr.md", [Chunk("Holiday policy and leave days.", {"source": "s2"})], fake_embedder
    )
    return Retriever(store, fake_embedder, k=2)


def test_retrieve_top_k_and_source_filter(retriever):
    assert len(retriever.retrieve("marketing budget")) == 2
    hits = retriever.retrieve("marketing budget", source="s2")
    assert [h.metadata["source"] for h in hits] == ["s2"]


def test_answer_cites_sources_and_prompt_contains_context(retriever):
    seen: list[str] = []
    llm = FakeLLM(lambda p: seen.append(p) or "The budget is 5000 euros [1].")
    answer = answer_question("marketing budget Q3", retriever, llm, "en")
    assert "5000" in answer.text
    assert answer.sources and answer.sources[0].startswith("[1] ")
    assert "notes.md" in " ".join(answer.sources)
    assert "[1]" in seen[0] and "marketing budget for Q3" in seen[0]


def test_french_prompt_and_no_context(tmp_path, fake_embedder):
    prompt = build_rag_prompt("Quoi ?", [("texte", {"item": "a.md", "page": 3})], "fr")
    assert "français" in prompt and "a.md, p.3" in prompt
    empty = Retriever(VectorStore(tmp_path / "e"), fake_embedder)
    answer = answer_question("x", empty, FakeLLM("never"), "fr")
    assert "mide index" in answer.text and answer.sources == []


def test_format_source():
    assert format_source({"item": "f.md", "line_start": 2, "line_end": 4}) == "f.md, l.2-4"


def test_ask_cli_without_model(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = CliRunner().invoke(app, ["ask", "hello"])
    assert result.exit_code == 1
    assert "model not installed" in result.output


def test_chat_history_is_truncated_and_used_in_prompt(retriever):
    from mide.rag.retriever import ChatSession

    prompts: list[str] = []
    llm = FakeLLM(lambda p: prompts.append(p) or f"answer {len(prompts)}")
    session = ChatSession(retriever, llm, "en", max_turns=2)
    for i in range(4):
        session.ask(f"marketing budget question {i}")
    assert len(session.history) == 2
    assert [q for q, _ in session.history] == [
        "marketing budget question 2", "marketing budget question 3"
    ]
    assert "marketing budget question 2" in prompts[-1]
    assert "marketing budget question 0" not in prompts[-1]
    assert "History:" not in prompts[0]
    session.reset()
    assert session.history == []


def test_chat_command_loop(retriever):
    from mide.rag.retriever import ChatSession

    session = ChatSession(retriever, FakeLLM(lambda p: "Budget is 5000 [1]."), "en")
    result = CliRunner().invoke(_chat_app(session), input="marketing budget\n/reset\nexit\n")
    assert "Budget is 5000" in result.output
    assert "Sources" in result.output
    assert session.history == []


def _chat_app(session):
    import typer

    from mide.cli import run_chat

    test_app = typer.Typer()

    @test_app.command()
    def go() -> None:
        run_chat(session)

    return test_app
