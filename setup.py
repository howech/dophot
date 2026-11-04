"""Build script: compiles the DoPHOT executable and ships it inside the wheel.

CFITSIO selection (environment variable):
    CFITSIO_PREFIX  Prefix of a static CFITSIO install (lib/libcfitsio.a,
                    include/). If unset, the system CFITSIO is linked
                    dynamically, which only works for local development.
"""
import os
import subprocess
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

try:
    from wheel.bdist_wheel import bdist_wheel
except ImportError:  # pragma: no cover
    bdist_wheel = None

DOPHOT_DIR = Path(__file__).parent / "dophot_rubin" / "dophot_c"
DOPHOT_EXE = DOPHOT_DIR / "working_data" / "dophot"
PARAM_DEFAULT = DOPHOT_DIR / "working_data" / "param_default_c"


def _make_args():
    prefix = os.environ.get("CFITSIO_PREFIX")
    if not prefix:
        return []
    lib = Path(prefix) / "lib" / "libcfitsio.a"
    inc = Path(prefix) / "include"
    if not lib.exists():
        raise RuntimeError(f"Static CFITSIO not found: {lib}")
    return [f"LIBS={lib} -lz -lpthread", f"CFIOflags=-I{inc}"]


class BuildDoPHOT(build_py):
    """Compile the DoPHOT executable, then package it with the Python code."""

    def run(self):
        subprocess.run(["make", "clean"], cwd=DOPHOT_DIR, check=True)
        subprocess.run(["make", "dophot", *_make_args()], cwd=DOPHOT_DIR, check=True)
        if not DOPHOT_EXE.exists() or not PARAM_DEFAULT.exists():
            raise RuntimeError(f"DoPHOT build incomplete: {DOPHOT_EXE}")
        super().run()


cmdclass = {"build_py": BuildDoPHOT}
if bdist_wheel is not None:

    class PlatformWheel(bdist_wheel):
        """The wheel contains a native executable, so it is not pure Python."""

        def finalize_options(self):
            super().finalize_options()
            self.root_is_pure = False

        def get_tag(self):
            _, _, plat = super().get_tag()
            return "py3", "none", plat

    cmdclass["bdist_wheel"] = PlatformWheel

setup(cmdclass=cmdclass, has_ext_modules=lambda: True)
