"""Optional LoRA fine-tuning (medium/large profiles with a GPU only).

Heavy dependencies (torch, transformers, peft) are imported lazily and only by the real
trainer. The adapter is activated only if it beats the base model on held-out questions.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from mide.connectors.files import DocumentConnector
from mide.hardware.profiler import HardwareReport
from mide.llm.runtime import LLM
from mide.rag.chunking import chunk_text

logger = logging.getLogger(__name__)

MIN_QA_PAIRS = 8
HOLDOUT_RATIO = 0.2

# Trainer signature: (train_pairs, output_dir) -> adapter path.
Trainer = Callable[[list["QAPair"], Path], Path]
# Scorer signature: (holdout_pairs, adapter_path or None) -> score in [0, 1].
Scorer = Callable[[list["QAPair"], "Path | None"], float]


class LoRAUnavailableError(Exception):
    """Raised when fine-tuning cannot run on this machine."""


@dataclass(frozen=True)
class QAPair:
    """A question/answer pair generated from a company document."""

    question: str
    answer: str
    source: str


@dataclass
class FinetuneReport:
    """Outcome of a fine-tuning attempt."""

    status: str  # "unavailable" | "skipped" | "rejected" | "activated"
    message: str
    n_pairs: int = 0
    score_before: float | None = None
    score_after: float | None = None
    adapter: Path | None = None
    details: dict = field(default_factory=dict)


def unavailable_reason(report: HardwareReport, profile_allows_lora: bool, language: str) -> str | None:
    """Return a user message if LoRA cannot run here, else ``None``."""
    fr = language == "fr"
    if not report.lora_possible or not profile_allows_lora:
        return (
            "Fine-tuning indisponible sur cette machine (GPU requis, profil medium/large), "
            "le RAG est utilisé."
            if fr
            else "Fine-tuning unavailable on this machine (GPU and medium/large profile "
            "required), RAG is used."
        )
    try:
        import peft  # noqa: F401
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        return (
            "Fine-tuning indisponible : installez `pip install mide-engine[finetune]`, "
            "le RAG est utilisé."
            if fr
            else "Fine-tuning unavailable: install `pip install mide-engine[finetune]`, "
            "RAG is used."
        )
    return None


_QA_RE = re.compile(r"Q:\s*(.+?)\s*\n+\s*A:\s*(.+?)(?=\n+\s*Q:|\Z)", re.DOTALL)


def parse_qa(text: str, source: str) -> list[QAPair]:
    """Parse ``Q: ... A: ...`` blocks produced by the LLM."""
    return [QAPair(q.strip(), a.strip(), source) for q, a in _QA_RE.findall(text)
            if q.strip() and a.strip()]


def generate_qa_dataset(
    documents: dict[str, str],
    llm: LLM,
    chunk_size: int = 800,
    max_pairs: int = 200,
    language: str = "fr",
) -> list[QAPair]:
    """Ask the local LLM for Q/A pairs about each document chunk (stays 100% local)."""
    lang = "français" if language == "fr" else "English"
    pairs: list[QAPair] = []
    for source, text in documents.items():
        for chunk in chunk_text(text, source, chunk_size, 0):
            prompt = (
                f"Write 2 factual question/answer pairs in {lang} that are answerable "
                f"ONLY from the text below. Format: 'Q: ...' then 'A: ...'.\n\n"
                f"TEXT:\n{chunk.text}\n"
            )
            pairs.extend(parse_qa(llm.generate(prompt, max_tokens=300, temperature=0.3), source))
            if len(pairs) >= max_pairs:
                return pairs[:max_pairs]
    return pairs


def split_dataset(pairs: list[QAPair]) -> tuple[list[QAPair], list[QAPair]]:
    """Deterministic train / held-out split (every 5th pair is held out)."""
    step = round(1 / HOLDOUT_RATIO)
    holdout = [p for i, p in enumerate(pairs) if i % step == step - 1]
    train = [p for i, p in enumerate(pairs) if i % step != step - 1]
    return train, holdout


def save_dataset(pairs: list[QAPair], path: Path) -> None:
    """Write the dataset as JSONL (kept under ``~/.mide``, never in the repo)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for p in pairs:
            fh.write(json.dumps(p.__dict__, ensure_ascii=False) + "\n")


def finetune(
    report: HardwareReport,
    profile_allows_lora: bool,
    documents: dict[str, str],
    llm: LLM,
    out_dir: Path,
    trainer: Trainer,
    scorer: Scorer,
    language: str = "fr",
    min_pairs: int = MIN_QA_PAIRS,
) -> FinetuneReport:
    """Full pipeline: availability check, dataset, training, before/after evaluation.

    The adapter is kept (``activated``) only if its held-out score beats the base model.
    """
    reason = unavailable_reason(report, profile_allows_lora, language)
    if reason:
        return FinetuneReport("unavailable", reason)
    pairs = generate_qa_dataset(documents, llm, language=language)
    if len(pairs) < min_pairs:
        msg = (f"Pas assez de données ({len(pairs)} paires < {min_pairs}), le RAG est utilisé."
               if language == "fr"
               else f"Not enough data ({len(pairs)} pairs < {min_pairs}), RAG is used.")
        return FinetuneReport("skipped", msg, n_pairs=len(pairs))
    train, holdout = split_dataset(pairs)
    save_dataset(pairs, out_dir / "qa_dataset.jsonl")
    adapter = trainer(train, out_dir / "adapter")
    before, after = scorer(holdout, None), scorer(holdout, adapter)
    if after > before:
        msg = (f"Adaptateur activé ({before:.2f} -> {after:.2f})." if language == "fr"
               else f"Adapter activated ({before:.2f} -> {after:.2f}).")
        (out_dir / "active_adapter.json").write_text(
            json.dumps({"adapter": str(adapter), "before": before, "after": after}),
            encoding="utf-8")
        return FinetuneReport("activated", msg, len(pairs), before, after, adapter)
    msg = (f"Adaptateur rejeté (pas d'amélioration : {before:.2f} -> {after:.2f}), "
           "le RAG est utilisé." if language == "fr"
           else f"Adapter rejected (no improvement: {before:.2f} -> {after:.2f}), RAG is used.")
    return FinetuneReport("rejected", msg, len(pairs), before, after)


def load_documents(sources: list[str], max_file_size_mb: float) -> dict[str, str]:
    """Read documents of authorized folders only (read-only)."""
    docs: dict[str, str] = {}
    for source in sources:
        if Path(source).expanduser().is_dir():
            docs.update(DocumentConnector(source, sources,
                                          max_file_size_mb=max_file_size_mb).read_all())
    return docs


def peft_trainer(base_model: str) -> Trainer:  # pragma: no cover - needs GPU + weights
    """Build the real PEFT trainer (HF base model name, e.g. Qwen/Qwen2.5-3B-Instruct)."""

    def train(pairs: list[QAPair], out: Path) -> Path:
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tok = AutoTokenizer.from_pretrained(base_model)
        model = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype=torch.float16,
                                                     device_map="auto")
        model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05,
                                                 task_type="CAUSAL_LM"))
        opt = torch.optim.AdamW(model.parameters(), lr=2e-4)
        model.train()
        for _ in range(2):
            for p in pairs:
                batch = tok(f"Q: {p.question}\nA: {p.answer}", return_tensors="pt",
                            truncation=True, max_length=512).to(model.device)
                loss = model(**batch, labels=batch["input_ids"]).loss
                loss.backward()
                opt.step()
                opt.zero_grad()
        model.save_pretrained(out)
        return out

    return train
