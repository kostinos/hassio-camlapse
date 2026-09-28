"""Standalone service verification entry point (camera and FFmpeg are mocked)."""

from pathlib import Path
import subprocess
import sys

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    raise SystemExit(
        subprocess.call([sys.executable, "-m", "pytest", str(root / "tests/test_services.py"), "-q"], cwd=root)
    )
