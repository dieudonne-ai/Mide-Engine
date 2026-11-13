"""Local LLM runtime: llama.cpp wrapper, hardware-adapted parameters, and a fake for tests."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from mide.hardware.profiler import HardwareReport, Profile

# Context window (tokens) per hardware profile.
CONTEXT_BY_PROFILE: dict[Profile, int] = {
    "tiny": 2048,
    "small": 4096,
    "medium": 4096,
    "large": 8192,
}


class LLMError(Exception):
    """Raised when the LLM runtime cannot be loaded or used."""


@dataclass(frozen=True)
class RuntimeParams:
    """Parameters used to load a model with llama.cpp."""

    n_ctx: int
    n_threads: int
    n_gpu_layers: int


class LLM(Protocol):
    """Minimal interface the rest of the engine depends on."""

    def generate(
        self, prompt: str, max_tokens: int = 512, temperature: float = 0.2
    ) -> str: ...

    def stream(
        self, prompt: str, max_tokens: int = 512, temperature: float = 0.2
    ) -> Iterator[str]: ...


def params_for_hardware(report: HardwareReport) -> RuntimeParams:
    """Derive context size, threads and GPU offload from the hardware report.

    Leaves one core free for the OS/UI; offloads all layers (-1) only when a GPU exists.
    """
    threads = max(1, report.cpu_cores - 1) if report.cpu_cores > 2 else max(1, report.cpu_cores)
    return RuntimeParams(
        n_ctx=CONTEXT_BY_PROFILE[report.profile],
        n_threads=threads,
        n_gpu_layers=-1 if report.gpu is not None else 0,
    )


class LlamaCppLLM:
    """Wrapper around ``llama-cpp-python`` (imported lazily, optional dependency)."""

    def __init__(
        self,
        model_path: str | Path,
        params: RuntimeParams,
        loader: Callable[..., Any] | None = None,
    ) -> None:
        path = Path(model_path)
        if not path.is_file():
            raise LLMError(f"Model file not found: {path}. Run `mide models pull`.")
        if loader is None:
            try:
                from llama_cpp import Llama  # type: ignore[import-not-found]
            except ImportError as exc:
                raise LLMError(
                    "llama-cpp-python is not installed. Install it with "
                    "`pip install mide-engine[llm]`."
                ) from exc
            loader = Llama
        self.params = params
        self._model = loader(
            model_path=str(path),
            n_ctx=params.n_ctx,
            n_threads=params.n_threads,
            n_gpu_layers=params.n_gpu_layers,
            verbose=False,
        )

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
        out = self._model(prompt, max_tokens=max_tokens, temperature=temperature)
        return str(out["choices"][0]["text"])

    def stream(
        self, prompt: str, max_tokens: int = 512, temperature: float = 0.2
    ) -> Iterator[str]:
        for chunk in self._model(
            prompt, max_tokens=max_tokens, temperature=temperature, stream=True
        ):
            yield str(chunk["choices"][0]["text"])


class FakeLLM:
    """Deterministic LLM for tests: returns a canned reply and records prompts."""

    def __init__(self, reply: str | Callable[[str], str] = "fake answer") -> None:
        self._reply = reply
        self.prompts: list[str] = []

    def _answer(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._reply(prompt) if callable(self._reply) else self._reply

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
        return self._answer(prompt)

    def stream(
        self, prompt: str, max_tokens: int = 512, temperature: float = 0.2
    ) -> Iterator[str]:
        words = self._answer(prompt).split(" ")
        for i, word in enumerate(words):
            yield word if i == 0 else " " + word


def load_llm(model_path: str | Path, report: HardwareReport) -> LlamaCppLLM:
    """Load the model at ``model_path`` with parameters adapted to the hardware."""
    return LlamaCppLLM(model_path, params_for_hardware(report))
