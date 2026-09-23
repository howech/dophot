"""Setup script to build DoPHOT C extension."""
from setuptools import setup
from setuptools.command.build_py import build_py
import subprocess
from pathlib import Path


class BuildDoPHOT(build_py):
    """Custom build command that compiles DoPHOT C code."""

    def run(self):
        """Build DoPHOT before building Python packages."""
        dophot_dir = Path(self.build_lib).parent.parent / "dophot_rubin" / "dophot_c"

        # If not in build_lib, use source directory
        if not dophot_dir.exists():
            dophot_dir = Path(__file__).parent / "dophot_rubin" / "dophot_c"

        if not dophot_dir.exists():
            raise RuntimeError(f"DoPHOT source not found at {dophot_dir}")

        print(f"Building DoPHOT C code in {dophot_dir}...")

        # Check for required dependencies
        result = subprocess.run(
            ["which", "gcc"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(
                "gcc not found. Please install a C compiler.\n"
                "  Ubuntu/Debian: sudo apt-get install build-essential libcfitsio-dev\n"
                "  macOS: brew install gcc cfitsio\n"
                "  Or use conda: conda install -c conda-forge gcc cfitsio"
            )

        # Run make
        result = subprocess.run(
            ["make"],
            cwd=str(dophot_dir),
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

        # Run parent class build
        super().run()


if __name__ == "__main__":
    setup(cmdclass={"build_py": BuildDoPHOT})
