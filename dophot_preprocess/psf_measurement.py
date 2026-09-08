"""
PSF measurement from bright stars in image.

Detects bright stars and measures their PSF width (sigma).
Adapted from IDL: getstars6.pro + fitpsfim_single.pro workflow.
"""

import numpy as np
from scipy.ndimage import gaussian_filter, label
from scipy.optimize import curve_fit
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
        Detection threshold above background (sigma).
        Default: 5.0
    saturation : float, optional
        Saturation value. Stars above saturation/5 are rejected.
        If None, use max(image) * 0.8
    n_stars : int, optional
        Return top N brightest stars. Default: all detected

    Returns
    -------
    x, y : ndarray
        Pixel coordinates of detected stars (0-indexed)
    intensity : ndarray
        Peak intensities of detected stars
    """
    if threshold is None:
        threshold = 5.0

    # Estimate sky value (using percentile instead of median for robustness)
    sky = np.percentile(image, 20)

    # Estimate noise
    noise = np.std(image[image < np.percentile(image, 50)])

    # Find peaks
    peaks = find_peaks(image, threshold=sky + threshold * noise, box_size=5)

    if len(peaks) == 0:
        return np.array([]), np.array([]), np.array([])

    x = peaks['x_peak']
    y = peaks['y_peak']
    intensity = peaks['peak_value']

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


def measure_psf_sigma(image, x, y, box_size=21):
    """
    Measure PSF width (sigma) at a single star position.

    Fits a 2D Gaussian to the stellar image.

    Parameters
    ----------
    image : ndarray
        2D image array
    x, y : float
        Star center position (can be sub-pixel)
    box_size : int
        Box size around star for fitting (must be odd).
        Default: 21

    Returns
    -------
    sigma : float
        Gaussian sigma (in pixels)
    amplitude : float
        Gaussian amplitude
    success : bool
        Whether fit converged
    """
    # Extract postage stamp
    hsize = box_size // 2
    ix, iy = int(np.round(x)), int(np.round(y))

    # Check bounds
    if (ix - hsize < 0 or ix + hsize >= image.shape[1] or
        iy - hsize < 0 or iy + hsize >= image.shape[0]):
        return np.nan, np.nan, False

    stamp = image[iy-hsize:iy+hsize+1, ix-hsize:ix+hsize+1].astype(float)

    # Create coordinate grids
    yy, xx = np.ogrid[0:stamp.shape[0], 0:stamp.shape[1]]
    cy, cx = hsize, hsize  # Center in the stamp

    # Estimate parameters
    sky_level = np.percentile(stamp, 10)
    stamp_centered = stamp - sky_level
    if stamp_centered.max() <= 0:
        return np.nan, np.nan, False

    amplitude_guess = stamp_centered.max()

    # Initial sigma guess
    sigma_guess = 2.0

    # Define 2D Gaussian function
    def gaussian_2d(coords, amp, sigma, cx, cy):
        x, y = coords
        return amp * np.exp(-((x-cx)**2 + (y-cy)**2) / (2*sigma**2))

    # Prepare data for fitting
    coords = (xx.ravel(), yy.ravel())
    data = stamp_centered.ravel()

    try:
        # Fit Gaussian
        popt, _ = curve_fit(
            gaussian_2d, coords, data,
            p0=[amplitude_guess, sigma_guess, cx, cy],
            maxfev=500
        )

        amplitude, sigma, fit_cx, fit_cy = popt

        # Check convergence - fitted center should be near expected center
        center_offset = np.sqrt((fit_cx - cx)**2 + (fit_cy - cy)**2)
        if center_offset > box_size / 3:  # Center drifted too far
            return np.nan, np.nan, False

        if sigma <= 0 or sigma > box_size / 2:  # Unreasonable sigma
            return np.nan, np.nan, False

        return sigma, amplitude, True

    except (RuntimeError, ValueError):
        return np.nan, np.nan, False


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
            image = hdul[0].data.astype(float)
            header = hdul[0].header
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

    for xi, yi in zip(x, y):
        sigma, amp, success = measure_psf_sigma(image, xi, yi, box_size=31)
        if success:
            sigmas.append(sigma)
            amplitudes.append(amp)

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
