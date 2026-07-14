"""Verify the PyTorch install selected by install_windows.bat."""

from __future__ import annotations

import argparse
import sys


def _python_version() -> str:
    return sys.version.replace("\r", " ").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify PyTorch CUDA availability.")
    parser.add_argument(
        "--expected",
        choices=("cuda", "cpu"),
        required=True,
        help="Expected install mode selected by install_windows.bat.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print labeled install summary after the required raw torch values.",
    )
    args = parser.parse_args()

    try:
        import torch
    except Exception as exc:  # pragma: no cover - this is an install-time guard.
        print(f"[ERROR] Failed to import torch: {exc}", file=sys.stderr)
        return 1

    torch_version = torch.__version__
    torch_cuda_runtime = torch.version.cuda
    cuda_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if cuda_available else "CUDA unavailable"

    # Keep these four lines equivalent to the install guide's required check.
    print(torch_version)
    print(torch_cuda_runtime)
    print(cuda_available)
    print(gpu_name)

    install_mode = "CUDA" if args.expected == "cuda" else "CPU"
    if args.summary:
        print(f"Python 버전: {_python_version()}")
        print(f"PyTorch 버전: {torch_version}")
        print(f"PyTorch CUDA 런타임 버전: {torch_cuda_runtime}")
        print(f"CUDA 사용 가능 여부: {cuda_available}")
        print(f"GPU 이름: {gpu_name}")
        print(f"설치 모드: {install_mode}")

    if args.expected == "cuda":
        if not torch_cuda_runtime:
            print(
                "[ERROR] NVIDIA GPU was detected, but this PyTorch build has no CUDA runtime.",
                file=sys.stderr,
            )
            return 1
        if not cuda_available:
            print(
                "[ERROR] NVIDIA GPU was detected, but torch.cuda.is_available() is False.",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
