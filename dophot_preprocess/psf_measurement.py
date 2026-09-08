"""
PSF measurement from bright stars in image.

Detects bright stars and measures their PSF width (sigma).
Adapted from IDL: getstars6.pro + fitpsfim_single.pro workflow.
"""

import numpy as np
from astropy.io import fits
from photutils.detection import find_peaks


def detect_bright_stars(image, threshold=None, saturation=None, n_stars=None):
    """
    Detect bright stars suitable for PSF measurement.

    Uses photutils.find_peaks for source detection.
    Filters by intensity to avoid saturated/too-faint sources.

    Parameters
    ----------
    image : ndarray
        2D image array
    threshold : float, optional
        Detection threshold (absolute value in DN, not sigma).
        Default: auto-calculate from sky + noise
    saturation : float, optional
        Saturation value. Stars above saturation/5 are rejected.
        If None, use max(image) * 0.9
    n_stars : int, optional
        Return top N brightest stars. Default: all detected

    Returns
    -------
    x, y : ndarray
        Pixel coordinates of detected stars (0-indexed)
    intensity : ndarray
        Peak intensities of detected stars
    """
    # Estimate sky value (using percentile for robustness)
    sky = np.percentile(image, 20)
    sky_high = np.percentile(image, 50)

    # Estimate noise from lower half of image
    noise = np.std(image[image < sky_high])

    # Auto-detect threshold if not provided
    # For bright star detection, use higher threshold to avoid noise
    if threshold is None:
        # Use 10-sigma above sky for robust star detection
        threshold = sky + 10.0 * noise

    # Find peaks with minimum spacing (stars should be separated)
    peaks = find_peaks(image, threshold=threshold, box_size=11)

    if len(peaks) == 0:
        return np.array([]), np.array([]), np.array([])

    x = peaks['x_peak']
    y = peaks['y_peak']
    intensity = peaks['peak_value']

    # Filter by edge distance (need space for PSF fitting stamps)
    edge_buffer = 32  # Buffer for 31x31 PSF stamp extraction
    good = ((x > edge_buffer) & (x < image.shape[1] - edge_buffer) &
            (y > edge_buffer) & (y < image.shape[0] - edge_buffer))
    x, y, intensity = x[good], y[good], intensity[good]

    if len(x) == 0:
        return np.array([]), np.array([]), np.array([])

    # Filter by saturation if provided
    if saturation is not None:
        good = intensity < (saturation / 5.0)
        x, y, intensity = x[good], y[good], intensity[good]

    # Also reject very faint sources
    if len(intensity) > 0:
        intensity_threshold = sky + 3.0 * noise
        good = intensity > intensity_threshold
        x, y, intensity = x[good], y[good], intensity[good]

    # Keep brightest N stars
    if n_stars is not None and len(x) > n_stars:
        idx = np.argsort(intensity)[-n_stars:]
        x, y, intensity = x[idx], y[idx], intensity[idx]

    return x, y, intensity


def measure_psf_sigma(image, x, y, box_size=21, debug=False):
    """
    Measure PSF width (sigma) at a single star position.

    Uses second moment method (fast) instead of Gaussian fitting.

    Parameters
    ----------
    image : ndarray
        2D image array
    x, y : float
        Star center position (can be sub-pixel)
    box_size : int
        Box size around star for measurement (must be odd).
        Default: 21
    debug : bool
        Print debug info for this star. Default: False

    Returns
    -------
    sigma : float
        PSF width (pixels), estimated from second moment
    amplitude : float
        Peak value in stamp
    success : bool
        Whether measurement succeeded
    """
    # Extract postage stamp
    hsize = box_size // 2
    ix, iy = int(np.round(x)), int(np.round(y))

    # Check bounds
    if (ix - hsize < 0 or ix + hsize >= image.shape[1] or
        iy - hsize < 0 or iy + hsize >= image.shape[0]):
        return np.nan, np.nan, False

    stamp = image[iy-hsize:iy+hsize+1, ix-hsize:ix+hsize+1].astype(float)

    # Subtract sky
    sky_level = np.percentile(stamp, 10)
    stamp_centered = stamp - sky_level

    if stamp_centered.max() <= 0:
        return np.nan, np.nan, False

    amplitude = stamp_centered.max()

    # Compute second moment (much faster than Gaussian fitting)
    # This measures the spread of the stellar light
    y_coords, x_coords = np.mgrid[0:stamp.shape[0], 0:stamp.shape[1]]
    cy, cx = hsize, hsize

    # Weight by pixel values
    total_flux = stamp_centered.sum()
    if total_flux <= 0:
        return np.nan, np.nan, False

    # Compute centroid
    cx_measured = (stamp_centered * x_coords).sum() / total_flux
    cy_measured = (stamp_centered * y_coords).sum() / total_flux

    # Compute second moment (variance)
    dx2 = ((x_coords - cx_measured)**2 * stamp_centered).sum() / total_flux
    dy2 = ((y_coords - cy_measured)**2 * stamp_centered).sum() / total_flux

    # Sigma is sqrt of variance
    sigma_x = np.sqrt(dx2)
    sigma_y = np.sqrt(dy2)
    sigma = (sigma_x + sigma_y) / 2.0  # Average of x and y

    if debug:
        print(f"    Second moment: sigma={sigma:.2f}, amp={amplitude:.1f}, " +
              f"center_offset={np.sqrt((cx_measured-cx)**2 + (cy_measured-cy)**2):.2f}")

    # Check validity
    center_offset = np.sqrt((cx_measured - cx)**2 + (cy_measured - cy)**2)
    if center_offset > box_size / 3:  # Center drifted too far
        if debug:
            print(f"      FAIL: center drift > {box_size/3:.1f}")
        return np.nan, np.nan, False

    if sigma <= 0.5 or sigma > box_size / 2:  # Unreasonable sigma
        if debug:
            max_sigma = box_size / 2
            print(f"FAIL: sigma out of range (0.5-{max_sigma:.1f}), got {sigma:.2f}")
        return np.nan, np.nan, False

    if debug:
        print("SUCCESS")

    return sigma, amplitude, True


def measure_psf_from_image(image_path, saturation=None, min_stars=10, verbose=True):
    """
    Measure PSF width from an image by finding and fitting bright stars.

    Workflow:
    1. Detect bright stars
    2. Fit Gaussian to each star
    3. Return median sigma from successful fits

    Parameters
    ----------
    image_path : str
        Path to FITS image file
    saturation : float, optional
        Saturation value in DN. If None, use 60000 (LSST typical)
    min_stars : int
        Minimum number of successful star fits required.
        Default: 10
    verbose : bool
        Print progress messages. Default: True

    Returns
    -------
    sigma : float
        Median PSF sigma from successful fits (pixels)
    n_stars : int
        Number of stars successfully measured
    success : bool
        Whether measurement succeeded
    """
    # Read image
    try:
        with fits.open(image_path) as hdul:
            # Try to get data from IMAGE extension (DP2 format) or PRIMARY
            if hdul[0].data is not None:
                image = hdul[0].data.astype(float)
            elif len(hdul) > 1 and hdul[1].data is not None:
                # DP2 format: data in IMAGE extension
                image = hdul[1].data.astype(float)
            else:
                raise ValueError("No image data found in FITS file")
    except Exception as e:
        if verbose:
            print(f"Error reading {image_path}: {e}")
        return np.nan, 0, False

    if saturation is None:
        saturation = 60000  # LSST typical

    if verbose:
        print(f"Image shape: {image.shape}")

    # Detect bright stars
    x, y, intensity = detect_bright_stars(image, threshold=5.0, saturation=saturation)

    if len(x) == 0:
        if verbose:
            print("No bright stars detected")
        return np.nan, 0, False

    if verbose:
        print(f"Detected {len(x)} bright stars")

    # Measure PSF sigma for each star
    sigmas = []
    amplitudes = []
    debug_fails = {'center_drift': 0, 'bad_sigma': 0, 'fit_error': 0}

    for i, (xi, yi) in enumerate(zip(x, y)):
        sigma, amp, success = measure_psf_sigma(
            image, xi, yi, box_size=31, debug=(i < 3)
        )
        if success:
            sigmas.append(sigma)
            amplitudes.append(amp)
        elif i < 3 and verbose:
            # Log first few failures for debugging
            print(f"    Star {i}: sigma={sigma}, amp={amp}")
            if sigma is not np.nan and sigma <= 0:
                debug_fails['bad_sigma'] += 1
            elif sigma is np.nan:
                debug_fails['fit_error'] += 1
            else:
                debug_fails['center_drift'] += 1

    if len(sigmas) < min_stars:
        if verbose:
            print(f"Only {len(sigmas)} successful fits (need {min_stars})")
        return np.nan, len(sigmas), False

    sigmas = np.array(sigmas)

    if verbose:
        print(f"Successful fits: {len(sigmas)}")
        print(f"Sigma range: {sigmas.min():.2f} - {sigmas.max():.2f} pixels")
        print(f"Sigma median: {np.median(sigmas):.2f} pixels")
        print(f"Sigma mean: {np.mean(sigmas):.2f} pixels")

    return float(np.median(sigmas)), len(sigmas), True
