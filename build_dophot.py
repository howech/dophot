"""Build script for DoPHOT C extension."""
import subprocess
import sys
from pathlib import Path

def build_dophot():
    """Compile DoPHOT C code using existing Makefile."""
    dophot_dir = Path(__file__).parent / "dophot_rubin" / "dophot_c"

    if not dophot_dir.exists():
        raise RuntimeError(f"DoPHOT source not found at {dophot_dir}")

    print(f"Building DoPHOT in {dophot_dir}...")

    # Run make
    result = subprocess.run(
        ["make", "-C", str(dophot_dir)],
        capture_output=False,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError("Failed to build DoPHOT C code")

    # Verify output exists
    dophot_exe = dophot_dir / "working_data" / "dophot"
    if not dophot_exe.exists():
        raise RuntimeError(f"DoPHOT executable not found at {dophot_exe}")

    print(f"✓ DoPHOT built successfully: {dophot_exe}")

if __name__ == "__main__":
    build_dophot()
