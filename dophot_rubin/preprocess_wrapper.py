"""
Preprocessing wrapper for DoPHOT task.

Orchestrates image scaling, PSF measurement, and parameter generation
using the proven-working recipe from the standalone pipeline.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

from .config import DoPHOTConfig
from .image_scaling import ScaleMetadata
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
    image_int32: np.ndarray
    image_with_psf: np.ndarray
    conversion_factor: float
    scale_metadata: ScaleMetadata
    units: str
    psfcenx: float
    psfceny: float
    psfcenz: int
    param_file: Path

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

        Executes the proven-working recipe:
        1. Detect image units (DN or nJy)
        2. Scale image to int32 with mask awareness
        3. Measure PSF from bright stars
        4. Generate DoPHOT parameter file
        5. Append PSF to image for DoPHOT input

        Parameters
        ----------
        image : ndarray
            2D image array (DN or flux units, float32)
        variance : ndarray, optional
            2D variance array (same units as image^2)
        mask : ndarray, optional
            2D mask array (0=good, nonzero=bad)
        header : dict or astropy.io.fits.Header, optional
            FITS header with GAIN, SATURATE, RDNOISE, etc.
        work_dir : str or Path, optional
            Working directory for parameter file (default: temp dir)

        Returns
        -------
        PreprocessingResult
            Complete preprocessing output including all intermediate arrays
        """
        from .image_scaling import (
            apply_mask_to_scaled_image,
            detect_units,
            scale_image_to_int32,
        )
        from .psf_measurement import (
            append_psf_to_image,
            generate_parameter_file,
            measure_psf_simple,
        )

        self.log.info("Starting preprocessing: PSF measurement + parameter generation")

        # Extract image statistics from header
        image_stats = self._extract_image_stats(header, image)

        self.log.debug(
            f"Image stats: sky={image_stats.sky_value:.1f}, "
            f"gain={image_stats.gain:.2f}, "
            f"rdnoise={image_stats.rdnoise:.1f}"
        )

        # Step 1: Detect units
        units = detect_units(header or {})
        self.log.info(f"Detected units: {units}")

        # Step 2: Scale image to int32
        image_int32, conversion_factor, scale_metadata = scale_image_to_int32(
            image,
            units,
            header=header,
            mask=mask,
            variance=variance,
        )
        self.log.info(
            f"Scaled to int32: epdn={scale_metadata.epdn:.4f}, mprec={scale_metadata.mprec}"
        )

        # Step 3: Apply mask to scaled image
        if mask is not None:
            image_int32 = apply_mask_to_scaled_image(image_int32, mask)
            self.log.debug("Applied mask to scaled image")

        # Step 4: Measure PSF
        sigma, beta4, beta6, beta8 = measure_psf_simple(image_int32, mask=mask)
        self.log.info(f"PSF measured: σ={sigma:.3f} pixels")

        # Step 5: Append PSF to image
        image_with_psf, psfcenx, psfceny, psfcenz = append_psf_to_image(
            image_int32, image_int32
        )

        # Step 6: Generate parameter file
        if work_dir is None:
            work_dir = Path(self.config.doPHOTWorkDir)
        else:
            work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        param_file = work_dir / "dophot_auto.param"

        params = generate_parameter_file(
            str(param_file),
            sigma=sigma,
            beta4=beta4,
            beta6=beta6,
            beta8=beta8,
            skyval=scale_metadata.skyval,
            epdn=scale_metadata.epdn,
            fpdn=1.0 / scale_metadata.gain,
            gain=scale_metadata.gain,
            saturation=image_stats.saturation,
            mprec=scale_metadata.mprec,
            image_shape=image_int32.shape,
            mask=mask,
            image_file="intermediate_i4.fits",
        )
        self.log.info(f"Parameter file written: {param_file}")

        metadata = PreprocessingMetadata(
            n_stars_measured=0,  # Not tracked in simple PSF measurement
            param_file=str(param_file),
            image_stats=image_stats,
            psfSigma=sigma,
        )

        return PreprocessingResult(
            sigma=sigma,
            params=params,
            metadata=metadata,
            image_int32=image_int32,
            image_with_psf=image_with_psf,
            conversion_factor=conversion_factor,
            scale_metadata=scale_metadata,
            units=units,
            psfcenx=psfcenx,
            psfceny=psfceny,
            psfcenz=psfcenz,
            param_file=param_file,
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
