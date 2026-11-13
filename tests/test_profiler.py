"""Tests for the hardware profiler (psutil and GPU mocked)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from mide.cli import app
from mide.hardware import profiler
from mide.hardware.profiler import GIB, GPUInfo, choose_profile, profile_hardware


@pytest.mark.parametrize(
    ("ram", "gpu", "expected"),
    [
        (4, None, "tiny"),
        (5.9, None, "tiny"),
        (6, None, "small"),
        (12, None, "small"),
        (16, None, "medium"),
        (8, GPUInfo("RTX 3060", 6), "medium"),
        (8, GPUInfo("RTX 3050", 4), "small"),
        (32, GPUInfo("RTX 4090", 24), "large"),
        (16, GPUInfo("A2000", 12), "large"),
    ],
)
def test_choose_profile(ram, gpu, expected):
    assert choose_profile(ram, gpu) == expected


def _mock(monkeypatch, ram_gb, gpu=None):
    monkeypatch.setattr(
        profiler.psutil, "virtual_memory", lambda: SimpleNamespace(total=int(ram_gb * GIB))
    )
    monkeypatch.setattr(profiler.psutil, "cpu_count", lambda logical=True: 4)
    monkeypatch.setattr(profiler, "detect_gpu", lambda: gpu)


@pytest.mark.parametrize(
    ("ram", "gpu", "profile"),
    [(4, None, "tiny"), (8, None, "small"), (16, None, "medium"), (32, GPUInfo("X", 24), "large")],
)
def test_profile_hardware(monkeypatch, ram, gpu, profile):
    _mock(monkeypatch, ram, gpu)
    report = profile_hardware()
    assert report.profile == profile
    assert report.ram_gb == ram
    assert report.cpu_cores == 4
    assert report.disk_free_gb > 0
    assert report.lora_possible == (gpu is not None and profile in ("medium", "large"))


def test_detect_gpu_without_nvidia_smi(monkeypatch):
    monkeypatch.setattr(profiler.shutil, "which", lambda _: None)
    assert profiler.detect_gpu() is None


def test_detect_gpu_parses_output(monkeypatch):
    monkeypatch.setattr(profiler.shutil, "which", lambda _: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(
        profiler.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(stdout="NVIDIA GeForce RTX 3060, 12288\n"),
    )
    assert profiler.detect_gpu() == GPUInfo("NVIDIA GeForce RTX 3060", 12.0)


def test_detect_gpu_handles_failure(monkeypatch):
    monkeypatch.setattr(profiler.shutil, "which", lambda _: "/usr/bin/nvidia-smi")

    def boom(*a, **k):
        raise OSError("nope")

    monkeypatch.setattr(profiler.subprocess, "run", boom)
    assert profiler.detect_gpu() is None


def test_doctor_shows_report(monkeypatch):
    _mock(monkeypatch, 8)
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "OK" in result.output
    assert "Profile: small" in result.output
