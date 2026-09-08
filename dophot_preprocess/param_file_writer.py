"""
Write DoPHOT parameter files from computed parameters.

Generates parameter modification files in DoPHOT format.
"""

import os
from datetime import datetime


def write_param_file(filename, params, base_param_file=None, verbose=True):
    """
    Write DoPHOT parameter modification file.

    Creates a file with computed parameters that can be passed to DoPHOT
    to override default values.

    Parameters
    ----------
    filename : str
        Output filename
    params : dict
        Output from compute_dophot_parameters()
    base_param_file : str, optional
        Path to base parameter file to copy from.
        If None, write minimal parameter file.
    verbose : bool
        Print progress. Default: True

    Returns
    -------
    bool
        True if successful
    """

    if verbose:
        print(f"Writing parameter file: {filename}")

    lines = []

    # Header
    lines.append("; DoPHOT Parameter File (Auto-Generated)")
    lines.append(f"; Generated: {datetime.now().isoformat()}")
    lines.append("; Auto-generated from image measurements")
    lines.append("")

    # Image measurements section
    lines.append("; === Image Measurements ===")
    lines.append(f"; PSF sigma: {params['sigma']:.2f} pixels")
    lines.append(f"; PSF FWHM: {params['fwhm']:.2f} pixels")
    lines.append(f"; Image noise: {params['nse_dn']:.2f} DN")
    lines.append(f"; Gain: {params.get('gain', 'N/A')} e-/DN")
    lines.append(f"; Readout noise: {params.get('rdne', 'N/A')} e-")
    lines.append(f"; Sky value: {params.get('sky_value', 'N/A')} DN")
    lines.append("")

    # Parameter overrides
    lines.append("; === DoPHOT Parameter Overrides ===")

    # FWHM (tune1_)
    gxwid = params['sigma']**2 * 100
    lines.append(f"; PSF width (FWHM)")
    lines.append(f"FWHM = {params['fwhm']:.2f}")
    lines.append("")

    # Box sizes (tune2_)
    lines.append("; Box sizes")
    lines.append(f"NFITBOX_X = {params['nfitbox'] // 2}")
    lines.append(f"NFITBOX_Y = {params['nfitbox'] // 2}")
    lines.append(f"MASKBOX_X = {params['maskbox'] // 2}")
    lines.append(f"MASKBOX_Y = {params['maskbox'] // 2}")
    lines.append(f"APBOX_X = {params['apbox'] // 2}")
    lines.append(f"APBOX_Y = {params['apbox'] // 2}")
    lines.append("")

    # Thresholds (tune3_)
    lines.append("; Detection thresholds")
    lines.append(f"THRESHMIN = {params['thmin']:.2f}")
    lines.append(f"THRESHMAX = {params['thmax']:.2f}")
    lines.append(f"THRESHDEC = 1.0")
    lines.append(f"IBOT = {int(params['bottom'])}")
    lines.append(f"ITOP = {int(params['saturation'])}")
    lines.append("")

    # Median filter (tune20_)
    lines.append("; Median filter settings")
    med_size = int(2.0 * params['fwhm']) // 2
    lines.append(f"HMEDWID_X = {med_size}")
    lines.append(f"HMEDWID_Y = {med_size}")
    lines.append(f"MPREC = {int(params['nse_dn'])}")
    lines.append("")

    # Pixel threshold
    lines.append("; Pixel detection threshold")
    lines.append(f"PIXTHRESH = {params['pxth']:.3f}")
    lines.append("")

    # Write file
    try:
        with open(filename, 'w') as f:
            f.write('\n'.join(lines))

        if verbose:
            print(f"✓ Parameter file written: {filename}")
        return True

    except Exception as e:
        print(f"Error writing parameter file: {e}")
        return False


def write_param_file_detailed(filename, params_dict, verbose=True):
    """
    Write detailed parameter file with all tune values.

    More comprehensive version that maps all computed parameters
    to DoPHOT tune struct values.

    Parameters
    ----------
    filename : str
        Output filename
    params_dict : dict
        Output from params_to_tune_values()
    verbose : bool
        Print progress. Default: True

    Returns
    -------
    bool
        True if successful
    """
    lines = []

    lines.append("; DoPHOT Parameter File (Detailed Auto-Generated)")
    lines.append(f"; Generated: {datetime.now().isoformat()}")
    lines.append("")

    # Iterate through each tune struct
    tune_names = [
        ('tune1_', 'PSF Width'),
        ('tune2_', 'Box Sizes'),
        ('tune3_', 'Thresholds'),
        ('tune12_', 'Mask Box'),
        ('tune20_', 'Median Filter'),
    ]

    for tune_name, description in tune_names:
        if tune_name not in params_dict:
            continue

        lines.append(f"; === {tune_name}: {description} ===")

        tune_values = params_dict[tune_name]
        for key, value in tune_values.items():
            if isinstance(value, (list, tuple)):
                lines.append(f"; {key}: {value}")
            else:
                lines.append(f"; {key}: {value:.3f}" if isinstance(value, float)
                            else f"; {key}: {value}")

        lines.append("")

    # Write file
    try:
        with open(filename, 'w') as f:
            f.write('\n'.join(lines))

        if verbose:
            print(f"✓ Detailed parameter file written: {filename}")
        return True

    except Exception as e:
        print(f"Error writing parameter file: {e}")
        return False


def generate_default_param_file(output_dir='.', filename='param_default'):
    """
    Generate a default DoPHOT parameter file.

    Creates a minimal parameter file with reasonable defaults.
    This can be used as a base for the parameter modification file.

    Parameters
    ----------
    output_dir : str
        Output directory. Default: current directory
    filename : str
        Output filename (without extension). Default: 'param_default'

    Returns
    -------
    str
        Path to generated file
    """
    param_content = """; Default DoPHOT Parameter File
; Auto-generated for Rubin DP2 images

; Image input/output
IMAGE_IN = input.fits
IMAGE_OUT = output.fits
OBJECTS_IN = objects_in.txt
OBJECTS_OUT = objects_out.txt
ERRORS_OUT = errors_out.txt
COVAR_OUT = covar_out.txt
BADDATA_OUT = baddata_out.txt
SHADOW_OUT = shadow_out.txt
LOG_FILE = dophot.log

; PSF model
PSF_MODEL = PGAUSS

; Detection
THRESHMIN = 5.0
THRESHMAX = 100.0
PIXTHRESH = 1.0

; Fitting boxes
NFITBOX_X = 5
NFITBOX_Y = 5

; Mask box
MASKBOX_X = 3
MASKBOX_Y = 3

; Sky model
SKY_MODEL = PLANE

; Output format
OUTPUT_FORMAT = RDCAP
"""

    filepath = os.path.join(output_dir, filename)
    try:
        with open(filepath, 'w') as f:
            f.write(param_content)
        print(f"✓ Default parameter file written: {filepath}")
        return filepath
    except Exception as e:
        print(f"Error writing default parameter file: {e}")
        return None
