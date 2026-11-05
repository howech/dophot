# dophot-rubin

Python wrapper for DoPHOT PSF-based photometry with optional Rubin Observatory pipeline integration.

## Installation

Commands in this document are run from the project root, `Sahas_CDoPhot/`.

Install from the prebuilt Linux wheel (includes the DoPHOT executable):

```bash
pip install dist/dophot_rubin-0.1.0-py3-none-manylinux_2_28_x86_64.whl
```

Or install from source, which builds the DoPHOT executable first (requires gcc and CFITSIO):

```bash
pip install -e .
```

For Rubin Stack integration (optional), set up a separate conda environment:

```bash
conda create -n rubin -c conda-forge -c https://conda.lsst.codes rubin-env
conda activate rubin
pip install -e .
```

## Prerequisites

The prebuilt Linux wheel needs no compiler. When installing from source, the DoPHOT C
executable is built from `dophot_rubin/dophot_c/` during `pip install`. To build it by hand:

```bash
cd dophot_rubin/dophot_c
make dophot
```

Requirements for building from source:
- C compiler (gcc)
- CFITSIO library (http://heasarc.gsfc.nasa.gov/fitsio/)

The compiled binary is at `dophot_rubin/dophot_c/working_data/dophot`.

## Running DoPHOT on an image

```bash
python scripts/run_dophot.py input.fits -o catalog.ecsv
```

Options: `--workdir DIR` for intermediate files, `--dophot PATH` to use a different executable.
The catalog is written as ECSV (or FITS if the output name ends in `.fits`).
The script is in the source tree under `scripts/`; it is not installed with the wheel.

## Quick Start

```python
from dophot_rubin import DoPHOTConfig
from dophot_rubin.image_scaling import detect_units, scale_image_to_int32
from dophot_rubin.psf_measurement import measure_psf_simple, generate_parameter_file
from astropy.io import fits

# Load image
with fits.open('image.fits') as hdul:
    image = hdul[0].data.astype('float32')
    header = dict(hdul[0].header)

# Detect units and scale to int32
units = detect_units(header)
image_int32, conversion_factor, scale_metadata = scale_image_to_int32(
    image, units, header=header
)

# Measure PSF
sigma, beta4, beta6, beta8 = measure_psf_simple(image_int32)

# Generate DoPHOT parameter file
params = generate_parameter_file(
    'dophot.param',
    sigma=sigma, beta4=beta4, beta6=beta6, beta8=beta8,
    skyval=scale_metadata.skyval,
    epdn=scale_metadata.epdn,
    fpdn=1.0/scale_metadata.gain,
    gain=scale_metadata.gain,
    saturation=header.get('SATURATE', 65535),
    mprec=scale_metadata.mprec,
    image_shape=image_int32.shape
)
```

See `examples/` directory for complete end-to-end examples.

## License

MIT License. See LICENSE file for details.

Note: The DoPHOT C code in `dophot_rubin/dophot_c/` is separately licensed under MIT
(with one file under Common Public License v1.0). See `dophot_rubin/dophot_c/LICENSE`
for details.
