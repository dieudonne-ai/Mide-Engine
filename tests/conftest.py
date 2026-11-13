"""Shared fixtures. Tests must never download real models: use fakes here."""


def _load_demo_module():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "scripts" / "make_demo_data.py"
    spec = importlib.util.spec_from_file_location("make_demo_data", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import pytest


@pytest.fixture(scope="session")
def demo_data(tmp_path_factory):
    """Deterministic demo dataset (seed 42) shared by tests."""
    module = _load_demo_module()
    return module.generate_demo_data(tmp_path_factory.mktemp("demo"), seed=42)


@pytest.fixture
def fake_llm():
    """A FakeLLM instance; never loads a real model."""
    from mide.llm.runtime import FakeLLM

    return FakeLLM()
