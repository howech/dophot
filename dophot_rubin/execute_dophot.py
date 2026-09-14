"""
DoPHOT C library execution wrapper.

Handles calling the compiled DoPHOT C code with generated parameter files.
"""

import logging
import subprocess
from pathlib import Path

from astropy.io import ascii
from astropy.table import Table

from .config import DoPHOTConfig

logger = logging.getLogger(__name__)


class DoPHOTExecutor:
    """Wrapper for executing DoPHOT C code."""

    config: DoPHOTConfig
    log: logging.Logger

    def __init__(self, config: DoPHOTConfig) -> None:
        """
        Initialize executor.

        Parameters
        ----------
        config : DoPHOTConfig
            Task configuration
        """
        self.config = config
        self.log = logging.getLogger(__name__)

        # Verify executable exists
        self._verify_executable()

    def _verify_executable(self) -> None:
        """Verify DoPHOT executable is available."""
        exec_path = Path(self.config.doPHOTExecPath)

        if exec_path.is_absolute():
            if not exec_path.exists():
                self.log.warning(f"DoPHOT executable not found: {exec_path}")
        else:
            # Try to find in PATH
            import shutil
            if shutil.which(self.config.doPHOTExecPath) is None:
                exec_name = self.config.doPHOTExecPath
                self.log.warning(f"DoPHOT executable not in PATH: {exec_name}")

    def run(
        self,
        image_path: str | Path,
        param_file: str | Path,
        output_dir: str | Path | None = None
    ) -> Table:
        """
        Execute DoPHOT on an image.

        Parameters
        ----------
        image_path : str or Path
            Path to input FITS image
        param_file : str or Path
            Path to DoPHOT parameter file
        output_dir : str or Path, optional
            Directory for output files

        Returns
        -------
        catalog : astropy.table.Table
            DoPHOT source catalog (loaded from output file)
        """
        image_path = Path(image_path)
        param_file = Path(param_file)

        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        if not param_file.exists():
            raise FileNotFoundError(f"Parameter file not found: {param_file}")

        if output_dir is None:
            output_dir = Path(self.config.doPHOTWorkDir)
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        self.log.info(f"Executing DoPHOT on {image_path.name}")
        self.log.debug(f"  Image: {image_path}")
        self.log.debug(f"  Parameters: {param_file}")
        self.log.debug(f"  Output dir: {output_dir}")

        try:
            # DoPHOT is interactive - provide parameter file via stdin
            # The executable expects the parameter file name as input
            param_file_input = (
                param_file.name if not param_file.is_absolute() else str(param_file)
            )

            # Execute DoPHOT
            result = subprocess.run(
                [str(self.config.doPHOTExecPath)],
                input=f"{param_file_input}\n",
                cwd=str(output_dir),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=False
            )

            if result.returncode != 0:
                msg = f"DoPHOT execution failed with return code {result.returncode}"
                self.log.error(msg)
                self.log.error(f"STDOUT: {result.stdout}")
                self.log.error(f"STDERR: {result.stderr}")
                raise RuntimeError(f"DoPHOT failed: {result.stderr}")

            self.log.debug(f"DoPHOT output:\n{result.stdout}")

            # Parse output catalog
            catalog = self._parse_output(output_dir)
            self.log.info(f"✓ DoPHOT complete: {len(catalog)} sources detected")

            return catalog

        except subprocess.TimeoutExpired:
            self.log.error("DoPHOT execution timed out (>300s)")
            raise RuntimeError("DoPHOT execution timed out")

        except Exception as e:
            self.log.error(f"DoPHOT execution failed: {e}")
            raise

    def _parse_output(self, output_dir: str | Path) -> Table:
        """
        Parse DoPHOT output catalog.

        Parameters
        ----------
        output_dir : Path
            Output directory

        Returns
        -------
        catalog : astropy.table.Table
            Parsed source catalog
        """
        # Look for DoPHOT output files
        # Typical DoPHOT output: objects_out, errors_out, etc.

        output_file = Path(output_dir) / "objects_out"
        errors_file = Path(output_dir) / "errors_out"

        if not output_file.exists():
            self.log.warning(f"DoPHOT output file not found: {output_file}")
            # Return empty table
            return Table()

        try:
            # Read source catalog
            catalog = ascii.read(str(output_file))

            # Read error catalog if available
            if errors_file.exists():
                errors = ascii.read(str(errors_file))
                # Merge errors into main catalog
                if len(errors) == len(catalog):
                    for col in errors.colnames:
                        if col not in catalog.colnames:
                            catalog[f'err_{col}'] = errors[col]

            self.log.debug(f"Loaded {len(catalog)} sources from DoPHOT output")
            return catalog

        except Exception as e:
            self.log.error(f"Failed to parse DoPHOT output: {e}")
            raise


def execute_dophot(
    image_path: str | Path,
    param_file: str | Path,
    config: DoPHOTConfig,
    output_dir: str | Path | None = None
) -> Table:
    """
    Convenience function to execute DoPHOT.

    Parameters
    ----------
    image_path : str or Path
        Path to input FITS image
    param_file : str or Path
        Path to DoPHOT parameter file
    config : DoPHOTConfig
        Task configuration
    output_dir : str or Path, optional
        Output directory

    Returns
    -------
    catalog : astropy.table.Table
        DoPHOT source catalog
    """
    executor = DoPHOTExecutor(config)
    return executor.run(image_path, param_file, output_dir)
