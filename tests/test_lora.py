from pathlib import Path

from typer.testing import CliRunner

from mide import cli
from mide.hardware.profiler import GPUInfo, HardwareReport
from mide.llm.lora import (
    finetune,
    generate_qa_dataset,
    parse_qa,
    split_dataset,
    unavailable_reason,
)
from mide.llm.runtime import FakeLLM

CPU = HardwareReport(8.0, 4, "Linux", None, 50.0, "small")
GPU = HardwareReport(32.0, 8, "Linux", GPUInfo("RTX", 12.0), 50.0, "large")
QA = "Q: What is the margin?\nA: 20 percent.\n\nQ: Who leads sales?\nA: Awa."
DOCS = {"notes.txt": "Margin is 20 percent. Awa leads sales. " * 200}


def _fake_torch(monkeypatch):
    import sys
    import types

    for name in ("torch", "peft", "transformers"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))


def test_unavailable_without_gpu_fr_en():
    assert "RAG" in unavailable_reason(CPU, False, "fr")
    assert "unavailable" in unavailable_reason(CPU, True, "en")


def test_unavailable_when_profile_disallows_lora():
    assert unavailable_reason(GPU, False, "en") is not None


def test_available_with_gpu_and_deps(monkeypatch):
    _fake_torch(monkeypatch)
    assert unavailable_reason(GPU, True, "en") is None


def test_finetune_unavailable_path_never_calls_trainer(tmp_path):
    def boom(*a):
        raise AssertionError("must not be called")

    res = finetune(CPU, False, DOCS, FakeLLM(QA), tmp_path, boom, boom)
    assert res.status == "unavailable" and not (tmp_path / "adapter").exists()


def test_parse_and_split():
    pairs = parse_qa(QA, "s")
    assert len(pairs) == 2 and pairs[0].answer == "20 percent."
    train, hold = split_dataset(pairs * 5)
    assert len(train) == 8 and len(hold) == 2


def test_generate_dataset_caps_pairs():
    assert len(generate_qa_dataset(DOCS, FakeLLM(QA), max_pairs=3)) == 3


def _run(tmp_path, after, monkeypatch):
    _fake_torch(monkeypatch)

    def trainer(train, out: Path) -> Path:
        out.mkdir(parents=True)
        return out

    scorer = lambda hold, adapter: 0.5 if adapter is None else after
    return finetune(GPU, True, DOCS, FakeLLM(QA), tmp_path, trainer, scorer, "en")


def test_adapter_activated_only_if_better(tmp_path, monkeypatch):
    res = _run(tmp_path, 0.8, monkeypatch)
    assert res.status == "activated" and (tmp_path / "active_adapter.json").exists()
    assert (tmp_path / "qa_dataset.jsonl").exists()


def test_adapter_rejected_if_not_better(tmp_path, monkeypatch):
    res = _run(tmp_path, 0.5, monkeypatch)
    assert res.status == "rejected" and not (tmp_path / "active_adapter.json").exists()


def test_not_enough_data_skipped(tmp_path, monkeypatch):
    _fake_torch(monkeypatch)
    res = finetune(GPU, True, {"a": "short"}, FakeLLM("nothing"), tmp_path, None, None)  # type: ignore[arg-type]
    assert res.status == "skipped"


def test_cli_finetune_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "profile_hardware", lambda *a, **k: CPU)
    r = CliRunner().invoke(cli.app, ["finetune", "--config-dir", str(tmp_path)])
    assert r.exit_code == 0 and "RAG" in r.output
