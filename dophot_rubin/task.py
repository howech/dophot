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
        from ..dophot_preprocess import psf_measurement, parameter_generation

        self.log.info("Starting preprocessing: PSF measurement")

        # Extract image data
        image = calexp.image.array
        variance = calexp.variance.array
        mask = calexp.mask.array

        # Measure PSF
        sigma, n_stars, success = psf_measurement.measure_psf_from_image(
            image_path=None,  # Will pass image array directly
            saturation=self.config.doPHOTWorkDir,
            min_stars=self.config.psfMinStars,
            verbose=self.config.doDebug
        )

        if not success or sigma is None:
            raise RuntimeError(f"PSF measurement failed (n_stars={n_stars})")

        self.log.info(f"PSF measured: sigma={sigma:.2f} pixels ({n_stars} stars)")

        # Generate parameters
        image_stats = {
            'sky_value': float(image.mean()),  # Rough estimate
            'gain': 1.0,  # Get from header
            'rdnoise': 10.0,  # Get from header
            'saturation': 60000,  # Get from header
        }

        params = parameter_generation.compute_dophot_parameters(
            sigma=sigma,
            gain=image_stats['gain'],
            rdnoise=image_stats['rdnoise'],
            sky_value=image_stats['sky_value'],
            saturation=image_stats['saturation'],
            verbose=self.config.doDebug
        )

        self.log.info("Parameter generation complete")
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

        self.log.info("Running DoPHOT photometry")

        # Write temporary parameter file
        with tempfile.TemporaryDirectory(dir=self.work_dir) as tmpdir:
            param_file = Path(tmpdir) / "dophot.param"
            param_file_writer.write_param_file(str(param_file), params, verbose=False)

            # Execute DoPHOT
            # TODO: Implement C library call
            self.log.info(f"DoPHOT parameter file: {param_file}")

            # For now, return empty catalog (placeholder)
            # In production, this will execute C DoPHOT and read output
            from astropy.table import Table
            catalog = Table()

        return catalog

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
        self.log.info("Starting postprocessing")

        # TODO: Implement postprocessing
        # 1. WCS transformation
        # 2. Aperture corrections
        # 3. Magnitude conversion
        # 4. Convert to SourceCatalog

        self.log.info("Postprocessing complete")

        # Placeholder: return empty SourceCatalog
        if HAS_RUBIN_STACK:
            from lsst.afw.table import SourceCatalog
            src = SourceCatalog()
        else:
            # Fallback for development
            src = catalog

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
