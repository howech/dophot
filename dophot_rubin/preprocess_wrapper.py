"""
Preprocessing wrapper for DoPHOT task.

Integrates PSF measurement and parameter generation from dophot_preprocess
into the Rubin PipelineTask context.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

from .config import DoPHOTConfig
from .psf_measurement import PSFParameters


class ImageStats(NamedTuple):
    """Image statistics extracted from header or image data."""
    sky_value: float
    sky_rms: float
    gain: float
    rdnoise: float
    saturation: float


class PreprocessingMetadata(NamedTuple):
    """Metadata from preprocessing operation."""
    n_stars_measured: int
    param_file: str
    image_stats: ImageStats
    psfSigma: float


class PreprocessingResult(NamedTuple):
    """Complete result from preprocessing."""
    sigma: float
    params: PSFParameters
    metadata: PreprocessingMetadata

logger = logging.getLogger(__name__)


class DoPHOTPreprocessor:
    """Wrapper for PSF measurement and parameter generation."""

    config: DoPHOTConfig
    log: logging.Logger

    def __init__(self, config: DoPHOTConfig) -> None:
        """
        Initialize preprocessor.

        Parameters
        ----------
        config : DoPHOTConfig
            Task configuration
        """
        self.config = config
        self.log = logging.getLogger(__name__)

    def run(
        self,
        image: np.ndarray,
        variance: np.ndarray | None = None,
        mask: np.ndarray | None = None,
        header: dict[str, Any] | None = None,
        work_dir: str | Path | None = None
    ) -> PreprocessingResult:
        """
        Run complete preprocessing pipeline.

        Parameters
        ----------
        image : ndarray
            2D image array (DN or flux units)
        variance : ndarray, optional
            2D variance array (same units as image^2)
        mask : ndarray, optional
            2D mask array (0=good, nonzero=bad)
        header : dict or astropy.io.fits.Header, optional
            FITS header with gain, saturation, readout noise
        work_dir : str or Path, optional
            Working directory for temporary files

        Returns
        -------
        sigma : float
            Measured PSF sigma (pixels)
        params : dict
            DoPHOT tuning parameters
        metadata : dict
            Processing metadata (n_stars, quality flags, etc.)
        """
        from dophot_preprocess import parameter_generation

        msg = "Starting preprocessing: PSF measurement + parameter generation"
        self.log.info(msg)

        # Extract image statistics from header
        image_stats = self._extract_image_stats(header, image)

        self.log.debug(f"Image stats: sky={image_stats['sky_value']:.1f}, "
                      f"gain={image_stats['gain']:.2f}, "
                      f"rdnoise={image_stats['rdnoise']:.1f}")

        # Measure PSF
        sigma, n_stars, success = self._measure_psf(image, image_stats)

        if not success or sigma is None:
            msg = f"PSF measurement failed (n_stars={n_stars}, success={success})"
            raise RuntimeError(msg)

        msg = f"✓ PSF measured: sigma={sigma:.3f} pixels ({n_stars} stars used)"
        self.log.info(msg)

        # Generate parameters
        params = parameter_generation.compute_dophot_parameters(
            sigma=sigma,
            gain=image_stats['gain'],
            rdnoise=image_stats['rdnoise'],
            sky_value=image_stats['sky_value'],
            saturation=image_stats['saturation'],
            beta4=1.0,
            verbose=self.config.doDebug
        )

        self.log.info("✓ Parameters generated successfully")

        # Write parameter file
        param_file = self._write_param_file(params, work_dir)

        metadata = PreprocessingMetadata(
            n_stars_measured=n_stars,
            param_file=str(param_file),
            image_stats=image_stats,
            psfSigma=sigma,
        )

        return PreprocessingResult(
            sigma=sigma,
            params=params,
            metadata=metadata,
        )

    def _extract_image_stats(
        self,
        header: dict[str, Any] | None,
        image: np.ndarray,
    ) -> ImageStats:
        """
        Extract image statistics from FITS header or image data.

        Parameters
        ----------
        header : dict or fits.Header or None
            FITS header
        image : ndarray
            Image data

        Returns
        -------
        ImageStats
            Statistics: sky_value, sky_rms, gain, rdnoise, saturation
        """
        # Sky value (robust percentile-based estimate)
        sky_value: float = float(np.percentile(image, 20))
        sky_rms: float = float(np.std(image[image < np.percentile(image, 50)]))

        # Extract or use defaults for gain, saturation, readnoise
        gain: float = 1.0
        saturation: float = 60000.0
        rdnoise: float = 10.0

        if header is not None:
            # Extract gain (try GAINA first, then GAIN)
            try:
                gain_val = header.get('GAINA', header.get('GAIN', 1.0))
                gain = float(gain_val)
            except TypeError:
                self.log.debug(f"Could not extract gain, using default {gain}")

            # Extract saturation
            try:
                saturation = float(header.get('SATURATE', 60000))
            except TypeError:
                self.log.debug(f"Could not extract saturation, using default {saturation}")

            # Extract readnoise (try RDNOISEA first, then RDNOISE)
            try:
                rdnoise_val = header.get('RDNOISEA', header.get('RDNOISE', 10.0))
                rdnoise = float(rdnoise_val)
            except TypeError:
                self.log.debug(f"Could not extract readnoise, using default {rdnoise}")

        result = ImageStats(
            sky_value=sky_value,
            sky_rms=sky_rms,
            gain=gain,
            rdnoise=rdnoise,
            saturation=saturation,
        )

        self.log.debug(f"Image stats: sky={result.sky_value:.1f}, "
                      f"gain={result.gain:.2f}, "
                      f"rdnoise={result.rdnoise:.1f}, "
                      f"saturation={int(result.saturation)}")

        return result

    def _measure_psf(
        self,
        image: np.ndarray,
        image_stats: ImageStats,
    ) -> tuple[float, int, bool]:
        """
        Measure PSF sigma from bright stars.

        Parameters
        ----------
        image : ndarray
            2D image array
        image_stats : dict
            Image statistics

        Returns
        -------
        sigma : float
            PSF sigma (pixels)
        n_stars : int
            Number of stars successfully measured
        success : bool
            Whether measurement succeeded
        """
        from dophot_preprocess.psf_measurement import (
            detect_bright_stars,
            measure_psf_sigma,
        )

        # Detect bright stars
        threshold = (
            image_stats['sky_value']
            + self.config.psfDetectionThreshold * image_stats['sky_rms']
        )

        # Create temp FITS file for detection (workaround for array-based detection)
        import tempfile

        from astropy.io import fits as fits_io

        with tempfile.NamedTemporaryFile(suffix='.fits', delete=False) as tmp:
            fits_io.writeto(tmp.name, image, overwrite=True)
            try:
                x, y, _ = detect_bright_stars(
                    image,
                    threshold=threshold,
                    saturation=image_stats['saturation'],
                    n_stars=None
                )
            except (TypeError, ValueError):
                # No stars detected, return failure
                msg = f"No bright stars detected (threshold={threshold:.1f} DN)"
                self.log.debug(msg)
                return np.nan, 0, False

        if x is None or len(x) == 0:
            self.log.debug(f"No bright stars detected (threshold={threshold:.1f} DN)")
            return np.nan, 0, False

        self.log.debug(f"Detected {len(x)} bright stars (threshold={threshold:.1f} DN)")

        if len(x) == 0:
            return np.nan, 0, False

        # Measure PSF on each star
        sigmas = []
        for i, (xi, yi) in enumerate(zip(x, y)):
            sigma, _, success = measure_psf_sigma(
                image, xi, yi,
                box_size=self.config.psfBoxSize,
                debug=(i < 3 and self.config.doDebug)
            )
            if success:
                sigmas.append(sigma)

        n_stars = len(sigmas)
        self.log.debug(f"Successfully measured {n_stars} stars")

        if n_stars < self.config.psfMinStars:
            min_stars = self.config.psfMinStars
            self.log.warning(
                f"Only {n_stars} stars measured (need {min_stars})"
            )
            return np.nan, n_stars, False

        sigma = float(np.median(sigmas))
        return sigma, n_stars, True

    def _write_param_file(
        self,
        params: dict[str, Any],
        work_dir: str | Path | None = None,
    ) -> Path:
        """
        Write DoPHOT parameter file.

        Parameters
        ----------
        params : dict
            DoPHOT parameters
        work_dir : str or Path, optional
            Working directory

        Returns
        -------
        Path
            Path to written parameter file
        """
        from dophot_preprocess import param_file_writer

        if work_dir is None:
            work_dir = Path(self.config.doPHOTWorkDir)
        else:
            work_dir = Path(work_dir)

        work_dir.mkdir(parents=True, exist_ok=True)
        param_file = work_dir / "dophot_auto.param"

        success = param_file_writer.write_param_file(
            str(param_file),
            params,
            verbose=self.config.doDebug
        )

        if not success:
            raise RuntimeError(f"Failed to write parameter file: {param_file}")

        self.log.debug(f"Parameter file written: {param_file}")
        return param_file


class PreprocessingContext:
    """Context manager for temporary preprocessing files."""

    def __init__(self, work_dir: str | Path | None = None) -> None:
        """Initialize context."""
        if work_dir is None:
            self.temp_dir = tempfile.TemporaryDirectory()
            self.work_dir = Path(self.temp_dir.name)
        else:
            self.work_dir = Path(work_dir)
            self.work_dir.mkdir(parents=True, exist_ok=True)
            self.temp_dir = None

    def __enter__(self) -> Path:
        """Enter context."""
        return self.work_dir

    def __exit__(self, *args: object) -> None:
        """Exit context and clean up."""
        if self.temp_dir is not None:
            self.temp_dir.cleanup()


def preprocess_calexp(
    calexp: Any,
    config: DoPHOTConfig,
    work_dir: str | Path | None = None
) -> PreprocessingResult:
    """
    Convenience function to preprocess a Rubin calexp.

    Parameters
    ----------
    calexp : lsst.afw.image.ExposureF
        Calibrated exposure
    config : DoPHOTConfig
        Task configuration
    work_dir : str or Path, optional
        Working directory

    Returns
    -------
    sigma : float
        PSF sigma (pixels)
    params : dict
        DoPHOT parameters
    metadata : dict
        Processing metadata
    """
    preprocessor = DoPHOTPreprocessor(config)

    # Extract data from calexp
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

    return sigma, params, metadata
