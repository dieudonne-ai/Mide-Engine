from typer.testing import CliRunner

from mide import cli
from mide.llm.chat import ChatHistory
from mide.llm.prompts import build_rag_prompt
from mide.llm.runtime import FakeLLM
from tests.test_retriever import _indexed


def test_history_keeps_last_turns():
    h = ChatHistory(max_turns=2, max_chars=1000)
    for i in range(4):
        h.add(f"q{i}", f"a{i}")
    assert h.turns == [("q2", "a2"), ("q3", "a3")]


def test_history_truncates_by_characters():
    h = ChatHistory(max_turns=10, max_chars=50)
    h.add("q" * 20, "a" * 20)
    h.add("r" * 10, "b" * 10)
    assert h.turns == [("r" * 10, "b" * 10)]
    h.add("x" * 100, "y" * 100)  # a single oversized turn is cut, not dropped
    assert len(h.turns) == 1 and h._size() <= 50


def test_history_render_and_clear():
    h = ChatHistory()
    assert h.render() == ""
    h.add("hi", "hello")
    assert "Réponse: hello" in h.render("fr") and "Answer: hello" in h.render("en")
    h.clear()
    assert h.turns == []


def test_prompt_includes_history():
    assert "Previous conversation" in build_rag_prompt("q", [], "en", "Question: a\nAnswer: b")
    assert "Previous conversation" not in build_rag_prompt("q", [], "en")


def test_chat_loop_remembers_previous_turn(tmp_path, monkeypatch, fake_embedder):
    src, _ = _indexed(tmp_path, fake_embedder)
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(cli, "_get_embedder", lambda cfg: fake_embedder)
    llm = FakeLLM("Answer one [1].")
    monkeypatch.setattr(cli, "_get_llm", lambda cfg: llm)
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "sources.yaml").write_text(f"sources:\n  - {src}\n")
    runner = CliRunner()
    assert runner.invoke(cli.app, ["index", "--config-dir", str(cfg_dir)]).exit_code == 0
    res = runner.invoke(
        cli.app, ["chat", "--config-dir", str(cfg_dir)],
        input="marketing budget Facebook\nand rice stock?\nexit\n",
    )
    assert res.exit_code == 0, res.output
    assert len(llm.prompts) == 2
    assert "Previous conversation" not in llm.prompts[0] and "Conversation précédente" not in llm.prompts[0]
    assert "marketing budget Facebook" in llm.prompts[1] and "Answer one" in llm.prompts[1]
    assert "Sources:" in res.output


def test_chat_empty_index_fails_cleanly(tmp_path, monkeypatch):
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    assert CliRunner().invoke(cli.app, ["chat"]).exit_code == 1
