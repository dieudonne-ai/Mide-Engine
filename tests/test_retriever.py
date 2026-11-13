from typer.testing import CliRunner

from mide import cli
from mide.llm.prompts import build_rag_prompt, sources_footer
from mide.llm.runtime import FakeLLM
from mide.rag.indexer import index_sources
from mide.rag.retriever import Retriever
from mide.rag.store import VectorStore


def _indexed(tmp_path, fake_embedder):
    src = tmp_path / "docs"
    src.mkdir()
    (src / "meeting.txt").write_text("The marketing budget for Facebook ads will be increased in March.")
    (src / "stock.txt").write_text("Warehouse inventory of rice is running low in Kinshasa.")
    idx = tmp_path / "idx"
    index_sources([str(src)], idx, fake_embedder)
    return src, idx


def test_retrieve_top_k_and_source_filter(tmp_path, fake_embedder):
    _, idx = _indexed(tmp_path, fake_embedder)
    r = Retriever(VectorStore(idx), fake_embedder, k=2)
    passages = r.retrieve("marketing budget Facebook")
    assert len(passages) == 2 and passages[0].citation.startswith("meeting.txt")
    assert [p.number for p in passages] == [1, 2]
    only = r.retrieve("marketing budget", source=passages[1].metadata["item"])
    assert {p.source for p in only} == {passages[1].source}


def test_prompt_is_bilingual_and_numbered(tmp_path, fake_embedder):
    _, idx = _indexed(tmp_path, fake_embedder)
    ps = Retriever(VectorStore(idx), fake_embedder).retrieve("rice")
    assert "Réponds en français" in build_rag_prompt("q?", ps, "fr")
    en = build_rag_prompt("q?", ps, "en")
    assert "Answer in English" in en and "[1]" in en
    assert sources_footer([]) == ""


def test_ask_end_to_end_cites_sources(tmp_path, monkeypatch, fake_embedder):
    src, _ = _indexed(tmp_path, fake_embedder)
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(cli, "_get_embedder", lambda cfg: fake_embedder)
    llm = FakeLLM("Budget goes up [1].")
    monkeypatch.setattr(cli, "_get_llm", lambda cfg: llm)
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "sources.yaml").write_text(f"sources:\n  - {src}\n")
    runner = CliRunner()
    assert runner.invoke(cli.app, ["index", "--config-dir", str(cfg_dir)]).exit_code == 0
    res = runner.invoke(cli.app, ["ask", "marketing budget Facebook", "--config-dir", str(cfg_dir)])
    assert res.exit_code == 0, res.output
    assert "Budget goes up [1]." in res.output
    assert "Sources:" in res.output and "meeting.txt" in res.output
    assert "marketing budget for Facebook" in llm.prompts[0]


def test_ask_with_empty_index_fails_cleanly(tmp_path, monkeypatch):
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    res = CliRunner().invoke(cli.app, ["ask", "hello"])
    assert res.exit_code == 1
