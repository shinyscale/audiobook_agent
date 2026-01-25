"""
System hardware specification detection.

Detects GPU, RAM, CPU, and platform information for optimal configuration.
"""

import logging
import os
import platform
import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    """Information about a single GPU."""

    name: str
    vram_gb: float
    gpu_type: str  # "nvidia", "amd", "apple_silicon", "integrated", "none"
    driver_version: Optional[str] = None
    compute_capability: Optional[str] = None


@dataclass
class SystemSpecs:
    """Complete system hardware specifications."""

    platform: str  # "linux", "darwin", "windows"
    architecture: str  # "x86_64", "aarch64", "arm64"
    cpu_cores: int
    ram_gb: float
    gpu_type: str  # Primary GPU type: "nvidia", "amd", "apple_silicon", "none"
    gpu_name: str  # Primary GPU name
    gpu_vram_gb: float  # Primary GPU VRAM (or unified memory for Apple)
    is_apple_silicon: bool
    gpus: list[GPUInfo] = field(default_factory=list)  # All detected GPUs

    @property
    def total_gpu_vram_gb(self) -> float:
        """Total VRAM across all GPUs."""
        return sum(gpu.vram_gb for gpu in self.gpus)

    @property
    def gpu_count(self) -> int:
        """Number of discrete GPUs detected."""
        return len([g for g in self.gpus if g.gpu_type not in ("integrated", "none")])


def detect_system_specs() -> SystemSpecs:
    """
    Detect current system hardware specifications.

    Returns:
        SystemSpecs with detected hardware information
    """
    plat = platform.system().lower()
    arch = platform.machine()
    cpu_cores = os.cpu_count() or 1
    ram_gb = _detect_ram()
    is_apple_silicon = _is_apple_silicon()

    # Detect GPUs
    gpus = []

    if plat == "darwin" and is_apple_silicon:
        # Apple Silicon - unified memory
        apple_gpu = _detect_apple_silicon_gpu(ram_gb)
        if apple_gpu:
            gpus.append(apple_gpu)
    else:
        # Try NVIDIA first
        nvidia_gpus = _detect_nvidia_gpus()
        gpus.extend(nvidia_gpus)

        # Try AMD/ROCm
        amd_gpus = _detect_amd_gpus()
        gpus.extend(amd_gpus)

    # Determine primary GPU
    if gpus:
        primary_gpu = gpus[0]
        gpu_type = primary_gpu.gpu_type
        gpu_name = primary_gpu.name
        gpu_vram_gb = primary_gpu.vram_gb
    else:
        gpu_type = "none"
        gpu_name = "No GPU detected"
        gpu_vram_gb = 0.0

    return SystemSpecs(
        platform=plat,
        architecture=arch,
        cpu_cores=cpu_cores,
        ram_gb=ram_gb,
        gpu_type=gpu_type,
        gpu_name=gpu_name,
        gpu_vram_gb=gpu_vram_gb,
        is_apple_silicon=is_apple_silicon,
        gpus=gpus,
    )


def _detect_ram() -> float:
    """Detect total system RAM in GB."""
    try:
        mem = psutil.virtual_memory()
        return round(mem.total / (1024**3), 1)
    except Exception as e:
        logger.warning(f"Failed to detect RAM via psutil: {e}")
        return _detect_ram_fallback()


def _detect_ram_fallback() -> float:
    """Fallback RAM detection using /proc/meminfo on Linux."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    # Format: "MemTotal:       32456789 kB"
                    kb = int(line.split()[1])
                    return round(kb / (1024**2), 1)
    except Exception:
        pass

    # Last resort: assume 8GB
    logger.warning("Could not detect RAM, assuming 8GB")
    return 8.0


def _is_apple_silicon() -> bool:
    """Check if running on Apple Silicon."""
    if platform.system() != "Darwin":
        return False

    arch = platform.machine()
    return arch in ("arm64", "aarch64")


def _detect_apple_silicon_gpu(ram_gb: float) -> Optional[GPUInfo]:
    """Detect Apple Silicon GPU info."""
    try:
        # Get chip info via system_profiler
        result = subprocess.run(
            ["system_profiler", "SPHardwareDataType"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        chip_name = "Apple Silicon"
        for line in result.stdout.split("\n"):
            if "Chip:" in line or "Processor Name:" in line:
                chip_name = line.split(":")[-1].strip()
                break

        # Apple Silicon uses unified memory
        # GPU can use most of system RAM, but typically ~75% is available
        unified_vram = ram_gb * 0.75

        return GPUInfo(
            name=chip_name,
            vram_gb=round(unified_vram, 1),
            gpu_type="apple_silicon",
        )
    except Exception as e:
        logger.debug(f"Failed to detect Apple Silicon GPU: {e}")
        return None


def _detect_nvidia_gpus() -> list[GPUInfo]:
    """Detect NVIDIA GPUs via nvidia-smi."""
    gpus = []

    # Known GPU VRAM sizes (for when nvidia-smi reports [N/A])
    KNOWN_GPU_VRAM = {
        "nvidia gb10": 128,  # DGX Spark
        "nvidia a100": 80,
        "nvidia h100": 80,
        "nvidia h200": 141,
        "nvidia a6000": 48,
        "nvidia rtx 4090": 24,
        "nvidia rtx 3090": 24,
    }

    try:
        # Query GPU info
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue

            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                name = parts[0]
                memory_str = parts[1]
                driver = parts[2] if len(parts) > 2 else None

                # Try to parse memory, handle [N/A] case
                vram_gb = 0.0
                try:
                    if memory_str and memory_str != "[N/A]":
                        vram_mb = float(memory_str)
                        vram_gb = round(vram_mb / 1024, 1)
                except (ValueError, TypeError):
                    pass

                # If VRAM not available, check known GPU list
                if vram_gb == 0:
                    name_lower = name.lower()
                    for gpu_pattern, known_vram in KNOWN_GPU_VRAM.items():
                        if gpu_pattern in name_lower:
                            vram_gb = known_vram
                            logger.debug(f"Using known VRAM {known_vram}GB for {name}")
                            break

                # Still no VRAM? Log warning but still add GPU
                if vram_gb == 0:
                    logger.warning(
                        f"Could not determine VRAM for {name}, assuming high-end GPU (96GB)"
                    )
                    vram_gb = 96.0  # Assume high-end for unrecognized NVIDIA GPUs

                gpus.append(
                    GPUInfo(
                        name=name,
                        vram_gb=vram_gb,
                        gpu_type="nvidia",
                        driver_version=driver,
                    )
                )

    except FileNotFoundError:
        logger.debug("nvidia-smi not found")
    except subprocess.TimeoutExpired:
        logger.warning("nvidia-smi timed out")
    except Exception as e:
        logger.debug(f"Failed to detect NVIDIA GPUs: {e}")

    return gpus


def _detect_amd_gpus() -> list[GPUInfo]:
    """Detect AMD GPUs via rocm-smi."""
    gpus = []

    try:
        # Try rocm-smi for AMD GPUs
        result = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram", "--csv"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        # Parse CSV output
        lines = result.stdout.strip().split("\n")
        if len(lines) < 2:
            return []

        # Get GPU names separately
        name_result = subprocess.run(
            ["rocm-smi", "--showproductname", "--csv"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        gpu_names = {}
        if name_result.returncode == 0:
            for line in name_result.stdout.strip().split("\n")[1:]:
                parts = line.split(",")
                if len(parts) >= 2:
                    gpu_id = parts[0].strip()
                    name = parts[1].strip()
                    gpu_names[gpu_id] = name

        # Parse memory info
        for line in lines[1:]:  # Skip header
            parts = line.split(",")
            if len(parts) >= 2:
                gpu_id = parts[0].strip()
                # Total VRAM in bytes
                try:
                    vram_bytes = int(parts[1].strip())
                    vram_gb = round(vram_bytes / (1024**3), 1)
                except (ValueError, IndexError):
                    vram_gb = 0.0

                name = gpu_names.get(gpu_id, f"AMD GPU {gpu_id}")

                gpus.append(
                    GPUInfo(
                        name=name,
                        vram_gb=vram_gb,
                        gpu_type="amd",
                    )
                )

    except FileNotFoundError:
        logger.debug("rocm-smi not found")
    except subprocess.TimeoutExpired:
        logger.warning("rocm-smi timed out")
    except Exception as e:
        logger.debug(f"Failed to detect AMD GPUs: {e}")

    # Fallback: try lspci for basic AMD GPU detection
    if not gpus:
        gpus = _detect_amd_via_lspci()

    return gpus


def _detect_amd_via_lspci() -> list[GPUInfo]:
    """Detect AMD GPUs via lspci (less detailed, fallback)."""
    gpus = []

    try:
        result = subprocess.run(
            ["lspci"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        for line in result.stdout.split("\n"):
            # Look for AMD/ATI VGA or 3D controllers
            if ("VGA" in line or "3D controller" in line) and ("AMD" in line or "ATI" in line):
                # Extract GPU name
                match = re.search(r"\[([^\]]+)\]", line)
                name = match.group(1) if match else "AMD GPU"

                gpus.append(
                    GPUInfo(
                        name=name,
                        vram_gb=0.0,  # Cannot determine VRAM from lspci
                        gpu_type="amd",
                    )
                )

    except FileNotFoundError:
        logger.debug("lspci not found")
    except Exception as e:
        logger.debug(f"Failed to detect AMD GPUs via lspci: {e}")

    return gpus
