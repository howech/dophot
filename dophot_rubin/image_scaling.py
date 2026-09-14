"""
Image scaling for DoPHOT.

Converts input images (DN or nJy) to int32 intermediate representation with
conversion factor tracking, following the IDL DoPHOT workflow.
"""

import logging
from typing import Any, NamedTuple

import numpy as np

logger = logging.getLogger(__name__)


class ScaleMetadata(NamedTuple):
    """Metadata from image scaling operation."""
    epdn: float
    mprec: int
    readnoise: float
    skyval: float
    noisethresh: float
    gain: float | None = None
    gain_scaled: float | None = None


def calculate_sky_gain(
    image: np.ndarray,
    variance: np.ndarray,
    mask: np.ndarray | None = None
) -> tuple[float, float, float, bool]:
    """
    Calculate sky level and gain from image and variance arrays.

    Following Abi's IDL sky_gain() approach: uses the variance-to-signal
    relationship to estimate gain, and image statistics to estimate sky.

    Parameters
    ----------
    image : ndarray
        Image array (DN or nJy units)
    variance : ndarray
        Variance array (same units squared)
    mask : ndarray, optional
        Mask array (bitflags from FITS MASK extension)

    Returns
    -------
    sky : float
        Sky level (same units as image)
    gain : float
        Electrons per DN (or similar unit)
    fpdn : float
        Flux per DN (1/gain), the inverse
    sky_subtracted : bool
        True if sky appears to already be subtracted from image
    """
    # Identify good pixels (unmasked and with valid data)
    good_pixels = np.ones(image.shape, dtype=bool)
    if mask is not None:
        flagged = (
            ((mask & 1) != 0) |  # Bad
            ((mask & 2) != 0) |  # Saturated
            ((mask & 4) != 0) |  # Interpolated
            ((mask & 8) != 0) |  # Cosmic ray
            ((mask & 16) != 0)   # Edge
        )
        good_pixels &= ~flagged

    # Calculate gain from variance-to-signal relationship
    # For Poisson statistics: variance = gain * signal
    # So: gain = variance / signal
    signal_mask = good_pixels & (image > 100) & (variance > 0)
    if np.any(signal_mask):
        gain_estimates = variance[signal_mask] / image[signal_mask]
        # Use median to reject outliers
        gain = np.median(gain_estimates)
    else:
        logger.warning("Could not calculate gain from variance, using default 1.0")
        gain = 1.0

    # Calculate sky level from image statistics
    # Sky is typically the mode/median of the image
    sky_pixels = good_pixels & (image > 0)
    if np.any(sky_pixels):
        # Use percentile to find sky (typically around 50th)
        sky = np.percentile(image[sky_pixels], 50)
    else:
        sky = 0.0

    # Check if sky is already subtracted
    # If most pixels are positive and median is small, sky likely subtracted
    sky_subtracted = False
    if sky < 100:
        sky_subtracted = True

    fpdn = 1.0 / gain if gain > 0 else 1.0

    logger.info(f"sky_gain calculation: sky={sky:.1f}, gain={gain:.4f} e/unit, "
               f"fpdn={fpdn:.4f}, sky_subtracted={sky_subtracted}")

    return sky, gain, fpdn, sky_subtracted


def detect_units(header: dict[str, Any]) -> str:
    """
    Detect image units from FITS header.

    Parameters
    ----------
    header : dict or astropy.io.fits.Header
        FITS header

    Returns
    -------
    units : str
        'DN' or 'nJy'
    """
    bunit = str(header.get('BUNIT', '')).strip().upper()

    if 'NJY' in bunit:
        return 'nJy'
    elif 'DN' in bunit or 'ADU' in bunit or bunit == '':
        return 'DN'
    else:
        logger.warning(f"Unknown BUNIT: {bunit}, assuming DN")
        return 'DN'


def _find_scaling_factor(
    skyval: float,
    readnoise: float,
    max_signal: float
) -> tuple[float, int]:
    """
    Find optimal scaling factor so noise is sampled at 2+ integer counts.

    Uses Abi's algorithm: iteratively halve maxsky until noise threshold
    (in integer units) reaches 2+ counts. Unit-agnostic—works for DN, nJy,
    or any calibrated flux units.

    Parameters
    ----------
    skyval : float
        Sky value (in same units as image will be scaled)
    readnoise : float
        Read noise (in same units as image)
    max_signal : float
        Maximum signal value (in same units as image)

    Returns
    -------
    epdn : float
        Scale factor (units per int32)
    mprec : int
        Median precision (integer counts for noise)
    """
    noisethresh = np.sqrt(skyval + readnoise**2)

    lpcnt = 0
    maxsky = max_signal
    while True:
        if lpcnt > 0:
            maxsky = maxsky / 2.0

        r2 = max(maxsky / 32760.0, 1.0)
        nt2 = noisethresh / r2

        if nt2 >= 2.0:
            epdn = r2
            mprec = int(np.round(nt2))
            logger.info(f"Found scaling: epdn={epdn:.4f}, mprec={mprec} "
                       f"(noise={nt2:.2f} counts)")
            return epdn, mprec

        lpcnt += 1
        if lpcnt > 20:
            logger.warning("Scaling loop exceeded 20 iterations, using current epdn")
            epdn = r2
            mprec = max(2, int(np.round(nt2)))
            return epdn, mprec


def scale_dn_to_int32(
    image: np.ndarray,
    gain: float,
    readnoise: float,
    saturation: float,
    header: dict[str, Any] | None = None,
    mask: np.ndarray | None = None,
    sky: float | None = None,
    sky_subtracted: bool = False
) -> tuple[np.ndarray, float, ScaleMetadata]:
    """
    Scale DN image to I*4 (int32) with proper noise digitization.

    Uses Abi's algorithm from IDL DoPHOT:
    1. Calculate noise threshold in electrons
    2. Find scaling factor so noise is sampled at 2+ integer counts
    3. Ensure scaled sky fits in ~16-bit range (maxsky/32760)

    Parameters
    ----------
    image : ndarray
        Input DN image
    gain : float
        Electrons per DN
    readnoise : float
        Read noise in electrons
    saturation : float
        Saturation level in DN
    header : dict, optional
        FITS header for metadata

    Returns
    -------
    scaled_image : ndarray (int32)
        Scaled image in intermediate representation
    conversion_factor : float
        Factor to convert int32 back to DN: DN = int32 * conversion_factor
    metadata : dict
        Scaling metadata (mprec, epdn, etc.)
    """
    # Step 1: Conditionally add sky back to image if not pre-subtracted
    # (Following IDL prep_dp1_pim.pro logic)
    if sky is not None and not sky_subtracted:
        image_working = image + sky
        msg = f"Added sky back to image: {sky:.1f} DN (sky was not pre-subtracted)"
        logger.info(msg)
    else:
        image_working = image.copy()
        if sky_subtracted:
            logger.info("Sky already subtracted from image, using as-is")

    # Step 2: Convert image to electrons using gain
    # This must happen BEFORE scaling calculation
    image_e = image_working * gain

    # Step 3: Create quality mask: exclude bad/masked pixels
    good_pixels = np.ones(image_working.shape, dtype=bool)
    if mask is not None:
        # Any flagged bit makes pixel bad (bits 0-4: bad/sat/interp/cosmic/edge)
        flagged = (mask & 31) != 0
        good_pixels &= ~flagged
        logger.info(f"Excluding {np.sum(~good_pixels)} masked pixels from scaling")

    # Step 4: Calculate sky in electrons
    # Use median of good unmasked pixels
    valid_mask = good_pixels & (image_working > 0) & (image_working < saturation * 0.9)
    if np.any(valid_mask):
        skyval_dn = np.median(image_working[valid_mask])
    else:
        # Fallback: use median of any positive unmasked pixels
        pos_unmasked = good_pixels & (image_working > 0)
        if np.any(pos_unmasked):
            skyval_dn = np.median(image_working[pos_unmasked])
        else:
            skyval_dn = np.median(image_working[image_working > 0])

    # Convert sky to electrons for noise calculation
    skyval = skyval_dn * gain

    # Step 5: Calculate noise threshold IN ELECTRONS
    # This combines Poisson noise from sky photons and readnoise
    # Both must be in electrons for proper combination
    noisethresh = np.sqrt(skyval + readnoise**2)

    logger.info(f"DN→int32: skyval={skyval:.1f} e, readnoise={readnoise:.1f} e, "
                f"noisethresh={noisethresh:.1f} e")

    # Find scaling factor using Abi's algorithm
    if np.any(good_pixels):
        maxsky = np.max(image_e[good_pixels])
    else:
        maxsky = np.max(image_e)

    epdn, mprec = _find_scaling_factor(skyval, readnoise, maxsky)

    # Calculate gain with scaling: fpdn = fpdn1 * epdn
    fpdn = (1.0 / gain) * epdn  # DN per electron (scaled)
    gain_scaled = 1.0 / fpdn     # electrons per DN (scaled)

    # Apply scaling
    image_scaled = image_e / epdn

    # Clamp to I*4 range
    image_scaled = np.clip(image_scaled, -2147483648, 2147483647)
    image_int32 = image_scaled.astype(np.int32)

    # Conversion factor: int32 -> DN
    # int32_value * epdn / gain = DN
    conversion_factor = epdn / gain

    logger.info(f"DN→int32 result: scale_factor={epdn:.4f}, "
                f"conversion_factor={conversion_factor:.6f} DN/int32, mprec={mprec}")

    metadata = ScaleMetadata(
        epdn=epdn,
        mprec=mprec,
        readnoise=readnoise,
        skyval=skyval,
        noisethresh=noisethresh,
        gain=gain,
        gain_scaled=gain_scaled,
    )

    return image_int32, conversion_factor, metadata


def scale_njy_to_int32(
    image: np.ndarray,
    readnoise_nJy: float | None = None,
    mask: np.ndarray | None = None
) -> tuple[np.ndarray, float, ScaleMetadata]:
    """
    Scale nJy image to I*4 (int32) with proper noise digitization.

    For nJy images (already in flux units), we scale to keep noise at ~1 count level.
    Since nJy values are typically 2-5x larger than DN values, both fit easily within
    I*4 range (-2,147,483,648 to 2,147,483,647). Same assumptions apply:
    values <1 → 0, values >2^31 → too bright.

    Parameters
    ----------
    image : ndarray
        Input nJy image
    readnoise_nJy : float, optional
        Read noise in nJy (estimated if not provided)

    Returns
    -------
    scaled_image : ndarray (int32)
        Scaled image in intermediate representation
    conversion_factor : float
        Factor to convert int32 back to nJy: nJy = int32 * conversion_factor
    """
    # Create quality mask: exclude bad/masked pixels
    good_pixels = np.ones(image.shape, dtype=bool)
    if mask is not None:
        # Any flagged bit makes pixel bad (bits 0-4: bad/sat/interp/cosmic/edge)
        flagged = (mask & 31) != 0
        good_pixels &= ~flagged
        logger.info(f"Excluding {np.sum(~good_pixels)} masked pixels from scaling")

    # Get sky value (median of valid unmasked pixels)
    valid_mask = good_pixels & (image > 0)
    if np.any(valid_mask):
        skyval = np.median(image[valid_mask])
    else:
        skyval = np.median(image[image > 0]) if np.any(image > 0) else 1.0

    # Estimate readnoise if not provided
    if readnoise_nJy is None:
        # For nJy data, estimate from image statistics
        # Use standard deviation of low-value unmasked pixels
        if np.any(valid_mask):
            sorted_vals = np.sort(image[valid_mask])
            # Noise is typically in lower percentiles
            readnoise_nJy = np.percentile(sorted_vals, 10)
            readnoise_nJy = max(readnoise_nJy, 0.1)  # At least 0.1 nJy
        else:
            readnoise_nJy = 1.0

    # Calculate noise threshold (needed for metadata and scaling)
    noisethresh = np.sqrt(skyval + readnoise_nJy**2)

    msg = (
        f"nJy→int32: skyval={skyval:.2f} nJy, readnoise={readnoise_nJy:.2f} nJy, "
        f"noisethresh={noisethresh:.2f} nJy"
    )
    logger.info(msg)

    # Find scaling factor using same algorithm as DN
    if np.any(good_pixels):
        maxsky = np.max(image[good_pixels])
    else:
        maxsky = np.max(image)

    epdn, mprec = _find_scaling_factor(skyval, readnoise_nJy, maxsky, units='nJy')

    # Apply scaling
    image_scaled = image / epdn

    # Clamp to I*4 range
    image_scaled = np.clip(image_scaled, -2147483648, 2147483647)
    image_int32 = image_scaled.astype(np.int32)

    # Conversion factor: int32 -> nJy
    conversion_factor = epdn

    logger.info(f"nJy→int32 result: scale_factor={epdn:.4f}, "
                f"conversion_factor={conversion_factor:.6f} nJy/int32, mprec={mprec}")

    metadata = ScaleMetadata(
        epdn=epdn,
        mprec=mprec,
        readnoise=readnoise_nJy,
        skyval=skyval,
        noisethresh=noisethresh,
    )

    return image_int32, conversion_factor, metadata


def scale_image_to_int32(
    image: np.ndarray,
    units: str,
    header: dict[str, Any] | None = None,
    gain: float | None = None,
    readnoise: float | None = None,
    saturation: float | None = None,
    mask: np.ndarray | None = None,
    variance: np.ndarray | None = None
) -> tuple[np.ndarray, float, ScaleMetadata]:
    """
    Scale image to int32 intermediate representation.

    Uses Abi's algorithm to find optimal scaling so noise is sampled at 2+
    integer counts. Excludes masked pixels from scaling calculations to avoid
    biasing towards bad pixels.

    Parameters
    ----------
    image : ndarray
        Input image
    units : str
        'DN' or 'nJy'
    header : dict, optional
        FITS header (used to extract gain, readnoise, saturation for DN images)
    gain : float, optional
        Electrons per DN (for DN images)
    readnoise : float, optional
        Read noise in electrons (for DN images)
    saturation : float, optional
        Saturation level in DN (for DN images)
    mask : ndarray, optional
        Mask array (bitflags from FITS MASK extension)
    variance : ndarray, optional
        Variance array (for calculating gain via sky_gain)

    Returns
    -------
    scaled_image : ndarray (int32)
        Scaled image
    conversion_factor : float
        Factor to convert int32 back to original units
    metadata : dict
        Scaling metadata (mprec, epdn, etc.)
    """
    # If variance provided, calculate sky_gain to get better gain/sky estimates
    sky_val = None
    sky_sub = False
    if variance is not None and units == 'DN':
        sky_val, gain_from_var, _, sky_sub = calculate_sky_gain(
            image, variance, mask=mask
        )
        if gain is None:
            gain = gain_from_var
        if readnoise is None:
            # Estimate readnoise from sky-level variance
            readnoise = np.sqrt(np.median(variance[variance > 0]))

    if units == 'DN':
        # Extract parameters from header if not provided
        if gain is None:
            gain = _get_header_value(header, 'GAIN', 1.0)
        if readnoise is None:
            readnoise = _get_header_value(header, 'READNOISE', 10.0)
        if saturation is None:
            saturation = _get_header_value(header, 'SATURATE', 65535.0)

        return scale_dn_to_int32(image, gain, readnoise, saturation, header,
                                mask=mask, sky=sky_val, sky_subtracted=sky_sub)

    elif units == 'nJy':
        # For nJy, readnoise is estimated from image
        readnoise_njy = None
        if header is not None:
            readnoise_njy = _get_header_value(header, 'READNOIS', None)

        return scale_njy_to_int32(image, readnoise_njy, mask=mask)

    else:
        raise ValueError(f"Unknown units: {units}")


def apply_mask_to_scaled_image(
    image_int32: np.ndarray,
    mask: np.ndarray,
    sentinel_value: int = -30000
) -> np.ndarray:
    """
    Apply mask to scaled int32 image.

    Sets flagged pixels to sentinel value, following IDL DoPHOT convention.

    Parameters
    ----------
    image_int32 : ndarray (int32)
        Scaled int32 image
    mask : ndarray (int32)
        Mask array (bitflags from FITS MASK extension)
    sentinel_value : int
        Value to use for bad pixels (default: -30000, matches IDL)

    Returns
    -------
    image_masked : ndarray (int32)
        Image with masked pixels set to sentinel value
    """
    if mask is None:
        return image_int32

    image_masked = image_int32.copy()

    # Apply mask flags (following IDL prep_dp1_pim.pro)
    # Bit flags: 1=bad, 2=saturated, 4=interpolated, 8=cosmic ray, 16=edge
    flagged = (mask & 31) != 0

    image_masked[flagged] = sentinel_value

    # Count individual flag types for logging
    bad_pixels = (mask & 1) != 0
    saturated = (mask & 2) != 0
    interpolated = (mask & 4) != 0
    cosmic_ray = (mask & 8) != 0
    edge = (mask & 16) != 0

    num_flagged = np.sum(flagged)
    logger.info(f"Applied mask: {num_flagged} pixels flagged "
               f"(bad={np.sum(bad_pixels)}, sat={np.sum(saturated)}, "
               f"interp={np.sum(interpolated)}, cr={np.sum(cosmic_ray)}, "
               f"edge={np.sum(edge)})")

    return image_masked


def unscale_int32_to_units(
    image_int32: np.ndarray,
    conversion_factor: float,
    units: str
) -> np.ndarray:
    """
    Convert int32 image back to original units using conversion factor.

    Parameters
    ----------
    image_int32 : ndarray (int32)
        Scaled int32 image from DoPHOT
    conversion_factor : float
        Conversion factor from scale_image_to_int32
    units : str
        'DN' or 'nJy'

    Returns
    -------
    image_original : ndarray (float32)
        Image in original units
    """
    image_float = image_int32.astype(np.float32) * conversion_factor
    msg = (
        f"Converted int32 image back to {units} "
        f"using factor {conversion_factor:.6f}"
    )
    logger.info(msg)
    return image_float


def _get_header_value(
    header: dict[str, Any] | None,
    keyword: str,
    default: float | None
) -> float | None:
    """Extract value from FITS header with fallback."""
    if header is None:
        return default

    try:
        return float(header.get(keyword, default))
    except (TypeError, ValueError):
        return default
