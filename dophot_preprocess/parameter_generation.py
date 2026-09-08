"""
DoPHOT parameter generation from image measurements.

Implements the algorithm from IDL: params_dp1_pim.pro
Converts image characteristics (PSF, noise, gain) to DoPHOT tuning parameters.
"""

import numpy as np


def compute_dophot_parameters(sigma, gain, rdnoise, sky_value, saturation=None,
                              beta4=None, verbose=True):
    """
    Compute all DoPHOT tuning parameters from image measurements.

    Implements the parameter generation algorithm from params_dp1_pim.pro.

    Parameters
    ----------
    sigma : float
        PSF width (sigma in pixels). REQUIRED.
        Must be measured from bright stars (see psf_measurement.py)
    gain : float
        Electrons per DN (detector gain). REQUIRED.
    rdnoise : float
        Readout noise in electrons. REQUIRED.
    sky_value : float
        Sky background value in DN. REQUIRED.
    saturation : float, optional
        Saturation value in DN. Default: 60000 (LSST typical)
    beta4 : float, optional
        PSF shape parameter (controls box size scaling).
        Default: 1.0 (Gaussian-like)
    verbose : bool
        Print computed values. Default: True

    Returns
    -------
    dict
        Dictionary with computed parameters:
        - 'fwhm': Full-width half-maximum
        - 'nse_dn': Noise in DN
        - 'nfitbox': Fitting box half-width
        - 'maskbox': Mask box half-width
        - 'apbox': Aperture box half-width
        - 'empbox': Empirical model box half-width
        - 'pxth': Pixel threshold
        - 'thmin', 'thmax': Threshold range
        - 'bottom': Lower threshold
        - 'rdne': Readout noise (adjusted)
    """
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    if gain <= 0:
        raise ValueError("gain must be positive")
    if rdnoise < 0:
        raise ValueError("rdnoise must be non-negative")
    if sky_value <= 0:
        raise ValueError("sky_value must be positive")

    if saturation is None:
        saturation = 60000  # LSST typical

    if beta4 is None:
        beta4 = 1.0  # Gaussian-like PSF

    # === PSF width calculations ===
    fwhm = 2.35 * sigma  # FWHM from sigma

    # === Noise calculations ===
    # Noise in DN = sqrt(sky_value * gain + readout_noise^2) / gain
    # This accounts for both photon noise and readout noise
    nse_dn = np.sqrt(sky_value * gain + rdnoise**2) / gain

    # Ensure readout noise is at least slightly above gain
    rdne = max(rdnoise, gain + 1.0)

    # === Box size calculations ===
    # These depend on PSF width and beta4 parameter
    # Larger box for extended PSFs, smaller for point sources

    if beta4 >= 1.0:
        nfitbox = 2 * int(np.round(fwhm)) + 1
    elif beta4 > 0.5:
        nfitbox = 2 * int(np.round(1.25 * fwhm)) + 1
    else:
        nfitbox = 2 * int(1.5 * fwhm) + 1

    # Clamp to reasonable range
    nfitbox = max(9, min(31, nfitbox))
    if nfitbox % 2 == 0:  # Ensure odd
        nfitbox += 1

    maskbox = int(1.5 * fwhm) + 1
    if maskbox % 2 == 0:
        maskbox += 1

    apbox = 31  # Fixed aperture box size

    # Empirical model box (should be 3x nfitbox for good PSF sampling)
    empbox = 3 * nfitbox
    empbox = max(15, min(35, empbox))  # Clamp and ensure odd
    if empbox % 2 == 0:
        empbox += 1

    # === Threshold calculations ===
    # Pixel threshold - sensitivity for peak detection
    # Lower threshold for bright stars, higher for faint
    # Approximately: 1 / (pi * sigma^2) = fraction of pixels containing star light
    pxth = 1.0 / (np.pi * sigma**2)
    pxth = min(1.0, pxth)
    pxth = max(0.1, pxth)

    # Minimum detection threshold (sigma above noise)
    thmin = 0.5 * nse_dn

    # Maximum threshold (for stars brighter than 2.5 magnitudes)
    # Estimate from saturation: stars that are ~saturation/2 in brightness
    thmax = saturation / 2.0

    # Bottom threshold (lower limit for pixel acceptance)
    noise_est = image_noise_estimate(sky_value, nse_dn)
    bottom = min(
        sky_value - 4.0 * nse_dn,
        sky_value - 1.5 * np.std(noise_est)
    )
    bottom = max(-1000.0, bottom)  # Don't go too negative

    params = {
        'fwhm': fwhm,
        'nse_dn': nse_dn,
        'nfitbox': nfitbox,
        'maskbox': maskbox,
        'apbox': apbox,
        'empbox': empbox,
        'pxth': pxth,
        'thmin': thmin,
        'thmax': thmax,
        'bottom': bottom,
        'rdne': rdne,
        'sigma': sigma,
        'beta4': beta4,
        'saturation': saturation,
    }

    if verbose:
        print("Computed DoPHOT Parameters:")
        print(f"  FWHM:         {fwhm:.2f} pixels")
        print(f"  Noise (nse_dn): {nse_dn:.2f} DN")
        print(f"  Fitting box:  {nfitbox} x {nfitbox}")
        print(f"  Mask box:     {maskbox} x {maskbox}")
        print(f"  Aperture box: {apbox} x {apbox}")
        print(f"  Empirical box: {empbox} x {empbox}")
        print(f"  Pixel threshold: {pxth:.3f}")
        print(f"  Detection range: {thmin:.2f} - {thmax:.2f} DN")
        print(f"  Lower limit:  {bottom:.2f} DN")
        print(f"  Readout noise: {rdne:.2f} e-")

    return params


def image_noise_estimate(sky_value, nse_dn):
    """
    Estimate image noise RMS from sky statistics.

    Simple model: noise scales with sqrt(sky_value).
    """
    return np.sqrt(sky_value) / 2.0  # Rough estimate


def params_to_tune_values(params):
    """
    Convert computed parameters to DoPHOT tune* struct values.

    Maps computed parameters to the specific tune* structs that DoPHOT expects.

    Parameters
    ----------
    params : dict
        Output from compute_dophot_parameters()

    Returns
    -------
    dict
        tune values organized by struct name:
        tune1_, tune2_, tune3_, etc.
    """
    sigma = params['sigma']
    fwhm = params['fwhm']
    nse_dn = params['nse_dn']
    nfitbox = params['nfitbox']
    maskbox = params['maskbox']
    apbox = params['apbox']

    # tune1_ - PSF width parameters
    tune1 = {
        'gxwid': sigma**2 * 100,  # Scaled PSF width
        'gywid': sigma**2 * 100,
        'skyguess': 1000.0  # Initial sky guess (not used)
    }

    # tune2_ - Box sizes
    tune2 = {
        'irect': [nfitbox // 2, nfitbox // 2],  # Fix box half-widths
        'krect': [nfitbox // 2, nfitbox // 2],  # Fit box half-widths
        'arect': [apbox // 2, apbox // 2]       # Aperture box half-widths
    }

    # tune3_ - Thresholds
    tune3 = {
        'tmin': params['thmin'],
        'tmax': params['thmax'],
        'tfac': 1.0,  # Threshold spacing factor
        'ibot': int(params['bottom']),
        'itop': int(params['saturation']),
        'dofinalfit': 1  # Do final fitting pass
    }

    # tune12_ - Mask box
    tune12 = {
        'ixby2': maskbox // 2,
        'iyby2': maskbox // 2
    }

    # tune20_ - Median filter box
    tune20 = {
        'jhxwid': int(2.0 * fwhm) // 2,  # Half-width for median box
        'jhywid': int(2.0 * fwhm) // 2,
        'mprec': int(nse_dn)  # Median precision
    }

    return {
        'tune1_': tune1,
        'tune2_': tune2,
        'tune3_': tune3,
        'tune12_': tune12,
        'tune20_': tune20,
    }


def measure_image_statistics(image_path):
    """
    Measure image statistics needed for parameter generation.

    Parameters
    ----------
    image_path : str
        Path to FITS image file

    Returns
    -------
    dict
        Statistics: sky_value, sky_rms, gain (if in header), saturation
    """
    from astropy.io import fits

    with fits.open(image_path) as hdul:
        # Handle DP2 format (data in IMAGE extension) or standard FITS (PRIMARY)
        if hdul[0].data is not None:
            image = hdul[0].data.astype(float)
            header = hdul[0].header
        elif len(hdul) > 1 and hdul[1].data is not None:
            image = hdul[1].data.astype(float)
            header = hdul[1].header
        else:
            raise ValueError("No image data found in FITS file")

    # Estimate sky value (20th percentile, below noise)
    sky_value = np.percentile(image, 20)

    # Estimate sky RMS
    sky_rms = np.std(image[image < np.percentile(image, 50)])

    # Try to get gain from header (LSST format)
    gain = header.get('GAINA', header.get('GAIN', 1.0))

    # Try to get saturation from header
    saturation = header.get('SATURATE', 60000)

    # Try to get readout noise from header
    rdnoise = header.get('RDNOISEA', header.get('RDNOISE', 10.0))

    return {
        'sky_value': sky_value,
        'sky_rms': sky_rms,
        'gain': float(gain),
        'saturation': float(saturation),
        'rdnoise': float(rdnoise),
    }
