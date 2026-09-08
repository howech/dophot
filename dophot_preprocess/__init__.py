"""
DoPHOT Preprocessing: Python wrapper for automated parameter generation.

Provides tools to:
1. Measure PSF width from bright stars
2. Compute DoPHOT tuning parameters from image measurements
3. Write DoPHOT parameter files

Example usage:
    from dophot_preprocess import psf_measurement, parameter_generation

    # Measure PSF
    sigma, n_stars, success = psf_measurement.measure_psf_from_image('image.fits')

    # Compute parameters
    params = parameter_generation.compute_dophot_parameters(
        sigma=sigma,
        gain=1.0,
        rdnoise=10.0,
        sky_value=1000.0
    )

    # Write parameter file
    from dophot_preprocess import param_file_writer
    param_file_writer.write_param_file('param.mod', params)
"""

from . import psf_measurement
from . import parameter_generation
from . import param_file_writer

__version__ = '0.1.0'
__all__ = ['psf_measurement', 'parameter_generation', 'param_file_writer']
