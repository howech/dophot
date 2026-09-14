"""
PSF measurement and parameter file generation for DoPHOT.

Follows Abi's IDL prep_dp1_pim.pro approach:
1. Measure PSF from image (sigma, beta parameters)
2. Generate DoPHOT parameter file with derived parameters
3. Append PSF to image for DoPHOT input
"""

import logging
from typing import NamedTuple

import numpy as np

logger = logging.getLogger(__name__)


class PSFParameters(NamedTuple):
    """PSF parameters for DoPHOT."""
    sigma: float
    beta4: float
    beta6: float
    beta8: float
    fwhm: float
    pxth: float
    nfitbox: int
    maskbox: int
    apbox: int
    empbox: int
    rdne: float
    nse_dn: float
    skyval: float
    epdn: float
    fpdn: float
    gain: float
    saturation: float
    mprec: int
    nx: int
    ny: int


def measure_psf_simple(
    image: np.ndarray,
    mask: np.ndarray | None = None,
    verbose: bool = False
) -> tuple[float, float, float, float]:
    """
    Measure PSF from image using bright stars.

    Simplified version: fits a 2D gaussian to bright star cores.
    Returns sigma (standard deviation), which is the key parameter.
    Other parameters (beta4, beta6, beta8) are set to typical values.

    Parameters
    ----------
    image : ndarray (int32)
        Scaled int32 image
    mask : ndarray, optional
        Mask array (to avoid bad pixels)
    verbose : bool
        Print diagnostic info

    Returns
    -------
    sigma : float
        PSF width (pixels)
    beta4 : float
        Moffat beta4 parameter (core flatness, ~0-2)
    beta6 : float
        Moffat beta6 parameter (wings, ~0-1)
    beta8 : float
        Moffat beta8 parameter (far wings, ~0)
    """
    # Find bright stars (peaks in the image)
    if mask is not None:
        # Only use good pixels
        good_pixels = (mask & 31) == 0
        image_clean = image.copy()
        image_clean[~good_pixels] = -30000
    else:
        image_clean = image

    # Find peaks (bright pixels away from edges and masked regions)
    threshold = np.percentile(image_clean[image_clean > 0], 90)
    bright_pixels = (image_clean > threshold) & (image_clean > 0)

    if not np.any(bright_pixels):
        logger.warning("No bright pixels found for PSF measurement, using defaults")
        return 2.5, 1.0, 0.5, 0.0

    # Find candidate star positions (local maxima)
    from scipy import ndimage
    labeled, num_features = ndimage.label(bright_pixels)

    if num_features < 3:
        logger.warning(f"Found only {num_features} bright regions, using defaults")
        return 2.5, 1.0, 0.5, 0.0

    # Get properties of bright regions
    props = ndimage.find_objects(labeled)
    sigmas = []

    for prop in props[:min(10, num_features)]:  # Use up to 10 bright stars
        if prop is None:
            continue

        # Extract star cutout
        star_data = image_clean[prop]
        if star_data.size < 9:  # Need at least 3x3
            continue

        # Find peak
        peak_val = np.max(star_data)
        if peak_val <= 0:
            continue

        # Estimate sigma from FWHM
        # For a gaussian, FWHM ≈ 2.35 * sigma
        # Estimate FWHM as width at half max
        try:
            # Simple estimate: radius to half-max
            half_max = peak_val / 2.0
            half_max_pixels = np.sum(star_data > half_max)
            # Approximate radius from area
            radius = np.sqrt(half_max_pixels / np.pi)
            sigma = radius / 1.177  # Convert FWHM to sigma
            if 0.5 < sigma < 10:  # Reasonable range
                sigmas.append(sigma)
        except ValueError:
            continue

    if len(sigmas) == 0:
        logger.warning("Could not measure PSF from stars, using defaults")
        return 2.5, 1.0, 0.5, 0.0

    sigma = np.median(sigmas)
    logger.info(f"Measured PSF: sigma={sigma:.2f} pixels from {len(sigmas)} stars")

    # Beta parameters: typical values for moffat-like profiles
    # beta4: core shape (1.0 = gaussian, higher = flatter)
    # beta6, beta8: wing parameters
    beta4 = 1.0
    beta6 = 0.5
    beta8 = 0.0

    return sigma, beta4, beta6, beta8


def generate_parameter_file(
    output_path: str,
    sigma: float,
    beta4: float,
    beta6: float,
    beta8: float,
    skyval: float,
    epdn: float,
    fpdn: float,
    gain: float,
    saturation: float,
    mprec: int,
    image_shape: tuple[int, int],
    mask: np.ndarray | None = None,
    image_file: str | None = None,
    verbose: bool = False
) -> PSFParameters:
    """
    Generate DoPHOT parameter file (DoPHOT-compatible format).

    Parameters
    ----------
    output_path : str
        Path to write parameter file
    sigma : float
        PSF width (pixels)
    beta4, beta6, beta8 : float
        Moffat profile parameters
    skyval : float
        Sky level (DN)
    epdn : float
        Scale factor (DN/int32)
    fpdn : float
        Flux per DN (1/gain)
    gain : float
        Electrons per DN
    saturation : float
        Saturation level (DN)
    mprec : int
        Median precision (integer counts for noise)
    image_shape : tuple
        (ny, nx) of image
    mask : ndarray, optional
        Mask array
    image_file : str, optional
        Name of input FITS file (for DoPHOT)
    verbose : bool
        Print diagnostic info

    Returns
    -------
    params : dict
        Dictionary of calculated parameters
    """
    ny, nx = image_shape

    # Calculate derived parameters (from IDL code)
    fwhm = 2.35 * sigma

    # Pixel threshold (fraction of peak within sigma radius)
    pxth = 1.0 / (0.5 * np.pi * sigma * sigma)
    pxth = min(1.0, max(0.1, pxth))

    # Fitting box size (depends on PSF profile)
    if beta4 >= 1.0:
        nfitbox = 2 * int(np.round(fwhm)) + 1
    elif beta4 > 0.5:
        nfitbox = 2 * int(np.round(1.25 * fwhm)) + 1
    else:
        nfitbox = 2 * int(1.5 * fwhm) + 1

    nfitbox = min(31, max(9, nfitbox))
    # Make it odd
    if nfitbox % 2 == 0:
        nfitbox += 1

    # Other box sizes
    maskbox = int(1.5 * fwhm) + 1
    apbox = 31
    empbox = min(35, 3 * int(np.ceil(nfitbox / 2)))
    empbox = max(15, empbox)
    if empbox % 2 == 0:
        empbox += 1

    # Readnoise (placeholder)
    rdne = 15
    if rdne <= 1.0:
        rdne = 8.0
    rdne = max(rdne, gain + 1.0)

    # Noise in DN
    nse_dn = np.sqrt(skyval * epdn + rdne * rdne) / epdn

    params = PSFParameters(
        sigma=sigma,
        beta4=beta4,
        beta6=beta6,
        beta8=beta8,
        fwhm=fwhm,
        pxth=pxth,
        nfitbox=nfitbox,
        maskbox=maskbox,
        apbox=apbox,
        empbox=empbox,
        rdne=rdne,
        nse_dn=nse_dn,
        skyval=skyval,
        epdn=epdn,
        fpdn=fpdn,
        gain=gain,
        saturation=saturation,
        mprec=mprec,
        nx=nx,
        ny=ny,
    )

    # Generate output file names
    if image_file:
        from pathlib import Path
        img_base = Path(image_file).stem
    else:
        img_base = "image"

    # Write parameter file in exact DoPHOT format
    from pathlib import Path as PathLib
    if image_file:
        image_name = PathLib(image_file).name
    else:
        image_name = "intermediate_i4.fits"

    with open(output_path, 'w') as f:
        f.write("=\n")
        f.write("PSFTYPE = 'PGAUSS'        PSF type: (PGAUSS, GAUSS, EXTPGAUSS)\n")
        f.write("=\n")
        fwhm_comment = "FWHM of objects (pixels) along major axis."
        f.write(f"FWHM = {fwhm:.2e}       {fwhm_comment}\n")
        sky_comment = "Approximate mean sky value in data numbers."
        f.write(f"SKY = {skyval:.1f}             {sky_comment}\n")
        f.write("=\n")
        f.write(f"EPERDN = {1.0/fpdn:.1f}         Electrons per data number\n")
        f.write(f"RDNOISE = {rdne:.1f}       Readout noise in electrons\n")
        f.write("=\n")
        f.write("PARAMS_DEFAULT = 'param_default'\n")
        f.write("PARAMS_OUT = 'param_out'\n")
        f.write(f"IMAGE_IN = '{image_name}'\n")
        f.write(f"IMAGE_OUT = 'image_out_{img_base}.fits'\n")
        f.write(f"OBJECTS_IN = 'obj_in_{img_base}'\n")
        f.write("OBJTYPE_IN = 'INTERNAL'\n")
        f.write(f"OBJECTS_OUT = 'obj_out_{img_base}'\n")
        f.write("OBJTYPE_OUT = 'INTERNAL'\n")
        f.write(f"ERRORS_OUT = 'errors_out_{img_base}'\n")
        f.write(f"SHADOWFILE_OUT = 'shad_out_{img_base}'\n")
        f.write(f"EMP_SUBRAS_OUT = 'psf_out_{img_base}.fits'\n")
        f.write("LOGFILE = 'log.txt'\n")
        f.write("LOGVERBOSITY = 100\n")
        f.write(f"COVARS_OUT = 'covar_out_{img_base}'\n")
        f.write("=\n")
        f.write("PSDIR = './'\n")
        f.write("=\n")
        f.write("MAX_PERF = 2000\n")
        f.write("THRESHMIN = 20.0\n")
        f.write("DOFINALFIT = 'NO'\n")
        f.write("=\n")
        f.write("AUTOSCALE = 'YES'\n")
        f.write("SCALEFITBOX = 5.0\n")
        f.write("FITBOXMIN = 5.0\n")
        f.write("=\n")
        f.write("END\n")

    logger.info(f"Parameter file written to {output_path}")
    return params


def append_psf_to_image(
    image: np.ndarray,
    psf_image: np.ndarray,
    max_iterations: int = 5
) -> tuple[np.ndarray, float, float, int]:
    """
    Append PSF strip to bottom of image, matching borders.

    Following IDL prep_dp1_pim.pro logic.

    Parameters
    ----------
    image : ndarray (int32)
        Scaled image
    psf_image : ndarray (int32)
        Measured/scaled PSF image
    max_iterations : int
        Max iterations for border matching

    Returns
    -------
    composite : ndarray (int32)
        Image with PSF appended at bottom
    psfcenx : int
        PSF center X coordinate
    psfceny : int
        PSF center Y coordinate
    psfcenz : int
        PSF center Z value (pixel value at center)
    """
    ny, nx = image.shape
    psy, psx = psf_image.shape

    logger.info(f"Appending PSF ({psy}x{psx}) to image ({ny}x{nx})")

    # Match PSF borders to image background
    sentinel = -30000
    psf_work = psf_image.copy()

    for iteration in range(max_iterations):
        # Get image strip near bottom (where PSF will attach)
        strip_y_start = ny - 21
        strip_y_end = ny
        image_strip = image[strip_y_start:strip_y_end, :psx]

        # Calculate median of good pixels in strip
        good_in_strip = image_strip > sentinel
        if np.sum(good_in_strip) > (psx * 21 / 4):
            median_image = np.median(image_strip[good_in_strip])
        else:
            median_image = np.median(image[image > sentinel])

        # Get PSF strip (top rows)
        psf_strip = psf_work[:5, :]
        median_psf = np.median(psf_strip[psf_strip > sentinel])

        # Adjust PSF to match image background
        psf_work = psf_work + (median_image - median_psf)

        # Check saturation
        max_image = np.max(image[image > sentinel])
        if np.max(psf_work) > 0.8 * max_image:
            # Rescale PSF
            psf_work = psf_work * (0.75 * max_image) / np.max(psf_work)
            logger.info(f"  Iteration {iteration+1}: Rescaled PSF to fit saturation")
        else:
            logger.info(f"  Iteration {iteration+1}: Border matched")
            break

    # Create composite image: original + PSF strip
    composite = np.full((ny + psy, nx), sentinel, dtype=np.int32)
    composite[:ny, :nx] = image

    # Add PSF strip at bottom (centered, with sentinel padding)
    psf_strip_region = np.full((psy, nx), sentinel, dtype=np.int32)
    psf_strip_region[:psy, :psx] = psf_work
    composite[ny:, :] = psf_strip_region

    # Calculate PSF center coordinates
    psfcenx = (psx - 1) / 2 + 1
    psfceny = (psy - 1) / 2 + 1 + ny
    psfcenz = int(psf_work[int(psy / 2), int(psx / 2)])

    msg = f"PSF appended. Center: ({psfcenx:.1f}, {psfceny:.1f}), Value: {psfcenz}"
    logger.info(msg)

    return composite, psfcenx, psfceny, psfcenz
