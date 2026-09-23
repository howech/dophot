"""
DoPHOT C library execution wrapper.

Handles calling the compiled DoPHOT C code with generated parameter files.
"""

import logging
import subprocess
from pathlib import Path

from astropy.table import Table

from .config import DoPHOTConfig
from .parse_dophot_output import convert_to_original_units, parse_obj_out

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
        output_dir: str | Path | None = None,
        conversion_factor: float = 1.0,
        original_units: str = "DN",
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
        conversion_factor : float
            Scale factor to convert flux back to original units
        original_units : str
            Original units (DN, nJy, etc.) for conversion

        Returns
        -------
        catalog : astropy.table.Table
            DoPHOT source catalog with fluxes converted to original units
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
            # Copy param_default_c to working directory (DoPHOT needs it)
            repo_root = Path(self.config.doPHOTExecPath).parent.parent.parent
            param_default = repo_root / "DoPHOT_C-master/working_data/param_default_c"
            if param_default.exists():
                import shutil
                shutil.copy(param_default, output_dir / "param_default_c")

            # Execute DoPHOT, providing both param file and default file via stdin
            # DoPHOT is interactive: asks for (1) modification params file, (2) input objects file
            param_filename = Path(param_file).name
            stdin_input = f"{param_filename}\nparam_default_c\n"
            result = subprocess.run(
                [str(self.config.doPHOTExecPath)],
                input=stdin_input,
                cwd=str(output_dir),
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minute timeout
                check=False,
            )

            if result.returncode != 0:
                msg = f"DoPHOT execution failed with return code {result.returncode}"
                self.log.error(msg)
                self.log.error(f"STDOUT: {result.stdout}")
                self.log.error(f"STDERR: {result.stderr}")
                raise RuntimeError(f"DoPHOT failed: {result.stderr}")

            self.log.debug(f"DoPHOT output:\n{result.stdout}")

            # Parse output catalog
            catalog = self._parse_output(
                output_dir, conversion_factor=conversion_factor, original_units=original_units
            )
            self.log.info(f"✓ DoPHOT complete: {len(catalog)} sources detected")

            return catalog

        except subprocess.TimeoutExpired:
            self.log.error("DoPHOT execution timed out (>300s)")
            raise RuntimeError("DoPHOT execution timed out")

        except Exception as e:
            self.log.error(f"DoPHOT execution failed: {e}")
            raise

    def _parse_output(
        self,
        output_dir: str | Path,
        conversion_factor: float = 1.0,
        original_units: str = "DN",
    ) -> Table:
        """
        Parse DoPHOT output catalog.

        DoPHOT writes output to files named obj_out_<basename> where <basename>
        comes from the IMAGE_IN parameter file setting.

        Parameters
        ----------
        output_dir : Path
            Output directory containing DoPHOT output files
        conversion_factor : float
            Scale factor to convert flux from int32 back to original units
        original_units : str
            Original units (DN, nJy, etc.)

        Returns
        -------
        catalog : astropy.table.Table
            Parsed source catalog with fluxes in original units
        """
        output_dir = Path(output_dir)

        # Look for DoPHOT output file (obj_out_*)
        matches = sorted(output_dir.glob("obj_out_*"))

        if not matches:
            self.log.warning(f"No DoPHOT obj_out_* file found in {output_dir}")
            return Table()

        obj_out_file = matches[0]
        self.log.debug(f"Found DoPHOT output: {obj_out_file.name}")

        try:
            # Parse the DoPHOT output file
            sources = parse_obj_out(str(obj_out_file))
            self.log.debug(f"Parsed {len(sources)} sources from {obj_out_file.name}")

            # Convert to original units
            catalog = convert_to_original_units(
                sources, conversion_factor, original_units
            )

            return catalog

        except Exception as e:
            self.log.error(f"Failed to parse DoPHOT output: {e}")
            raise


def execute_dophot(
    image_path: str | Path,
    param_file: str | Path,
    config: DoPHOTConfig,
    output_dir: str | Path | None = None,
    conversion_factor: float = 1.0,
    original_units: str = "DN",
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
    conversion_factor : float
        Scale factor for unit conversion
    original_units : str
        Original flux units

    Returns
    -------
    catalog : astropy.table.Table
        DoPHOT source catalog with fluxes in original units
    """
    executor = DoPHOTExecutor(config)
    return executor.run(
        image_path,
        param_file,
        output_dir,
        conversion_factor=conversion_factor,
        original_units=original_units,
    )
