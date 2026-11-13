"""Hardware detection and profile selection (``tiny|small|medium|large``)."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import psutil

Profile = Literal["tiny", "small", "medium", "large"]

GIB = 1024**3


@dataclass(frozen=True)
class GPUInfo:
    """A detected GPU."""

    name: str
    vram_gb: float


@dataclass(frozen=True)
class HardwareReport:
    """Snapshot of the machine's capabilities."""

    ram_gb: float
    cpu_cores: int
    os_name: str
    gpu: GPUInfo | None
    disk_free_gb: float
    profile: Profile

    @property
    def lora_possible(self) -> bool:
        """LoRA fine-tuning needs a GPU and a medium/large profile."""
        return self.gpu is not None and self.profile in ("medium", "large")


def detect_gpu() -> GPUInfo | None:
    """Detect an NVIDIA GPU through ``nvidia-smi``; return None if unavailable."""
    exe = shutil.which("nvidia-smi")
    if exe is None:
        return None
    try:
        out = subprocess.run(
            [exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
        first = out.strip().splitlines()[0]
        name, mem_mib = (part.strip() for part in first.rsplit(",", 1))
        return GPUInfo(name=name, vram_gb=round(float(mem_mib) / 1024, 1))
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


def choose_profile(ram_gb: float, gpu: GPUInfo | None) -> Profile:
    """Pick a profile following the table in CLAUDE.md section 3."""
    vram = gpu.vram_gb if gpu else 0.0
    if vram >= 12:
        return "large"
    if ram_gb > 12 or vram >= 6:
        return "medium"
    if ram_gb >= 6:
        return "small"
    return "tiny"


def profile_hardware(path: str | Path | None = None) -> HardwareReport:
    """Inspect the machine and choose a profile."""
    ram_gb = psutil.virtual_memory().total / GIB
    gpu = detect_gpu()
    disk = shutil.disk_usage(str(path or Path.home()))
    return HardwareReport(
        ram_gb=round(ram_gb, 1),
        cpu_cores=psutil.cpu_count(logical=True) or os.cpu_count() or 1,
        os_name=f"{platform.system()} {platform.release()}",
        gpu=gpu,
        disk_free_gb=round(disk.free / GIB, 1),
        profile=choose_profile(ram_gb, gpu),
    )
