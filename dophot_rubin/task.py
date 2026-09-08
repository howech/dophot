"""
DoPHOT PipelineTask for Rubin Observatory.

Orchestrates PSF-based photometry using DoPHOT on calibrated visit images.
"""

import logging
import os
import tempfile
from pathlib import Path

try:
    from lsst.pipe.base import PipelineTask, PipelineTaskConnections
    from lsst.pex.config import Config
    HAS_RUBIN_STACK = True
except ImportError:
    HAS_RUBIN_STACK = False
    # Fallback for development
    class PipelineTask:
        def __init__(self, config, name=None):
            self.config = config
            self.name = name or self.__class__.__name__

    class PipelineTaskConnections:
        pass

    class Config:
        pass

from .config import DoPHOTConfig
from .preprocess_wrapper import DoPHOTPreprocessor, PreprocessingContext
from .postprocess import DoPHOTPostprocessor
from .execute_dophot import DoPHOTExecutor


logger = logging.getLogger(__name__)


class DoPHOTTask(PipelineTask):
    """
    Perform PSF-based photometry using DoPHOT.

    This task orchestrates the complete DoPHOT workflow:
    1. Measure PSF from bright stars in the image
    2. Generate DoPHOT tuning parameters automatically
    3. Execute DoPHOT C photometry code
    4. Postprocess results (aperture corrections, WCS, magnitudes)

    Inputs:
        calexp: Calibrated exposure from reprocessVisitImage
                (DP2 format: IMAGE, MASK, VARIANCE extensions)
        photoCalib: Photometric calibration for magnitude conversion
        psf: PSF model from previous processing

    Outputs:
        src: SourceCatalog with DoPHOT photometry
        srcMetadata: Metadata about processing
    """

    ConfigClass = DoPHOTConfig
    _DefaultName = "dophot"

    def __init__(self, config, name=None, **kwargs):
        """Initialize DoPHOT task."""
        super().__init__(config, name=name, **kwargs)

        # Set up logging
        self.log = logging.getLogger(self.name)
        self.log.setLevel(getattr(logging, self.config.logLevel))

        # Create working directory
        self.work_dir = Path(self.config.doPHOTWorkDir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

        self.log.info(f"DoPHOT task initialized. Working directory: {self.work_dir}")

    def runQuantum(self, butlerQC, inputRefs, outputRefs):
        """
        Execute DoPHOT photometry for a single visit/detector.

        This is the main entry point called by the Rubin pipeline for each
        dataId (typically per-detector per-visit).

        Parameters
        ----------
        butlerQC : ButlerQuantumContext
            Data access object for this quantum
        inputRefs : InputQuantumContext
            References to input datasets
        outputRefs : OutputQuantumContext
            References to output datasets
        """
        self.log.info(f"Running DoPHOT for {inputRefs.calexp.dataId}")

        try:
            # Load inputs
            calexp = butlerQC.get(inputRefs.calexp)
            photoCalib = butlerQC.get(inputRefs.photoCalib)

            # Run preprocessing
            sigma, params = self._preprocessing(calexp)

            # Run DoPHOT
            catalog = self._run_dophot(calexp, params)

            # Run postprocessing
            src = self._postprocessing(calexp, catalog, photoCalib)

            # Write outputs
            butlerQC.put(src, outputRefs.src)

            self.log.info(f"DoPHOT completed: {len(src)} sources detected")

        except Exception as e:
            self.log.error(f"DoPHOT failed: {e}")
            raise

    def _preprocessing(self, calexp):
        """
        Measure PSF and generate DoPHOT parameters.

        Parameters
        ----------
        calexp : lsst.afw.image.ExposureF
            Calibrated exposure

        Returns
        -------
        sigma : float
            Measured PSF width (pixels)
        params : dict
            DoPHOT tuning parameters
        """
        with PreprocessingContext(self.work_dir) as work_dir:
            preprocessor = DoPHOTPreprocessor(self.config)

            # Extract image data
            image = calexp.image.array
            variance = calexp.variance.array if calexp.variance else None
            mask = calexp.mask.array if calexp.mask else None
            header = calexp.getMetadata()

            # Run preprocessing
            sigma, params, metadata = preprocessor.run(
                image=image,
                variance=variance,
                mask=mask,
                header=header,
                work_dir=work_dir
            )

            self.log.info(f"✓ Preprocessing complete: sigma={sigma:.3f} pixels")
            return sigma, params

    def _run_dophot(self, calexp, params):
        """
        Execute DoPHOT photometry.

        Parameters
        ----------
        calexp : lsst.afw.image.ExposureF
            Calibrated exposure
        params : dict
            DoPHOT tuning parameters

        Returns
        -------
        catalog : astropy.table.Table
            DoPHOT source catalog
        """
        from ..dophot_preprocess import param_file_writer
        from astropy.table import Table

        self.log.info("Running DoPHOT photometry")

        # Write temporary parameter file
        with tempfile.TemporaryDirectory(dir=self.work_dir) as tmpdir:
            tmpdir = Path(tmpdir)
            param_file = tmpdir / "dophot.param"

            param_file_writer.write_param_file(str(param_file), params, verbose=False)
            self.log.debug(f"Parameter file: {param_file}")

            # Check if DoPHOT executable exists
            import shutil
            if shutil.which(self.config.doPHOTExecPath) is None:
                self.log.warning(f"DoPHOT executable not found: {self.config.doPHOTExecPath}")
                self.log.warning("Returning empty catalog (DoPHOT not available)")
                return Table()

            # Execute DoPHOT
            try:
                executor = DoPHOTExecutor(self.config)

                # Need to write FITS image to temp file for DoPHOT
                fits_file = tmpdir / "input.fits"
                import fits  # Will use astropy.io.fits
                fits.writeto(str(fits_file), calexp.image.array, overwrite=True)

                catalog = executor.run(
                    image_path=fits_file,
                    param_file=param_file,
                    output_dir=tmpdir
                )

                self.log.info(f"✓ DoPHOT complete: {len(catalog)} sources")
                return catalog

            except Exception as e:
                self.log.error(f"DoPHOT execution failed: {e}")
                # Return empty catalog on error
                return Table()

    def _postprocessing(self, calexp, catalog, photoCalib):
        """
        Postprocess DoPHOT output.

        Apply aperture corrections, WCS transformation, magnitude conversion.

        Parameters
        ----------
        calexp : lsst.afw.image.ExposureF
            Calibrated exposure
        catalog : astropy.table.Table
            DoPHOT source catalog
        photoCalib : lsst.afw.image.PhotoCalib
            Photometric calibration

        Returns
        -------
        src : lsst.afw.table.SourceCatalog
            Rubin SourceCatalog with photometry
        """
        from .postprocess import create_source_catalog

        postprocessor = DoPHOTPostprocessor(self.config)

        # Run postprocessing
        catalog_out = postprocessor.run(
            catalog,
            calexp=calexp,
            psf=calexp.getPsf() if calexp else None,
            photoCalib=photoCalib
        )

        # Convert to SourceCatalog
        if HAS_RUBIN_STACK:
            src = create_source_catalog(catalog_out, self.config)
        else:
            # Fallback for development
            src = catalog_out

        self.log.info("✓ Postprocessing complete")
        return src


class DoPHOTTaskWithConnections(PipelineTask):
    """
    DoPHOT task with full Rubin connections (requires lsst.pipe.base).

    This is the version used when the full Rubin Stack is available.
    It includes proper input/output connections following Rubin conventions.
    """

    if HAS_RUBIN_STACK:
        # This would be properly decorated when Rubin Stack is available
        pass

    ConfigClass = DoPHOTConfig
    _DefaultName = "dophotWithConnections"

    # TODO: Define InputConnections and OutputConnections when Rubin Stack available


def create_dophot_task():
    """Factory function to create appropriate DoPHOT task."""
    if HAS_RUBIN_STACK:
        return DoPHOTTaskWithConnections
    else:
        return DoPHOTTask
