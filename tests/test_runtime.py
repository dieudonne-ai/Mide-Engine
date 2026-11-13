from __future__ import annotations

import pytest

from mide.hardware.profiler import GPUInfo, HardwareReport
from mide.llm.runtime import (
    FakeLLM,
    LlamaCppLLM,
    LLMError,
    RuntimeParams,
    params_for_hardware,
)


def report(profile="small", cores=8, gpu=None):
    return HardwareReport(
        ram_gb=8, cpu_cores=cores, os_name="Linux", gpu=gpu, disk_free_gb=50, profile=profile
    )


def test_params_scale_with_profile():
    assert params_for_hardware(report("tiny")).n_ctx < params_for_hardware(report("large")).n_ctx


def test_params_threads_and_gpu():
    p = params_for_hardware(report(cores=8))
    assert p.n_threads == 7 and p.n_gpu_layers == 0
    assert params_for_hardware(report(cores=1)).n_threads == 1
    g = params_for_hardware(report("large", gpu=GPUInfo("RTX", 12.0)))
    assert g.n_gpu_layers == -1


def test_fake_llm_generate_and_stream():
    llm = FakeLLM("hello big world")
    assert llm.generate("hi") == "hello big world"
    assert "".join(llm.stream("hi")) == "hello big world"
    assert llm.prompts == ["hi", "hi"]


def test_fake_llm_callable_reply():
    assert FakeLLM(lambda p: p.upper()).generate("abc") == "ABC"


def test_llamacpp_missing_file(tmp_path):
    with pytest.raises(LLMError):
        LlamaCppLLM(tmp_path / "nope.gguf", RuntimeParams(512, 2, 0), loader=lambda **k: None)


def test_llamacpp_wrapper_with_mock_loader(tmp_path):
    model = tmp_path / "m.gguf"
    model.write_bytes(b"x")
    seen = {}

    def loader(**kwargs):
        seen.update(kwargs)

        def call(prompt, **kw):
            if kw.get("stream"):
                return iter([{"choices": [{"text": "a"}]}, {"choices": [{"text": "b"}]}])
            return {"choices": [{"text": "answer"}]}

        return call

    llm = LlamaCppLLM(model, RuntimeParams(1024, 3, 0), loader=loader)
    assert seen["n_ctx"] == 1024 and seen["n_threads"] == 3 and seen["n_gpu_layers"] == 0
    assert llm.generate("q") == "answer"
    assert list(llm.stream("q")) == ["a", "b"]


def test_llamacpp_without_package(tmp_path, monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "llama_cpp", None)
    model = tmp_path / "m.gguf"
    model.write_bytes(b"x")
    with pytest.raises(LLMError, match="llama-cpp-python"):
        LlamaCppLLM(model, RuntimeParams(512, 1, 0))


def test_fake_llm_fixture(fake_llm):
    assert fake_llm.generate("x") == "fake answer"
