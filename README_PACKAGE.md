# dophot-rubin

Python wrapper for DoPHOT PSF-based photometry with optional Rubin Observatory pipeline integration.

## Installation

Install the Python package via pip:

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

The DoPHOT C executable must be built separately from the C source code in `DoPHOT_C-master/`.

Requirements:
- C compiler (gcc)
- CFITSIO library (http://heasarc.gsfc.nasa.gov/fitsio/)

To build:

```bash
cd DoPHOT_C-master
make clean
make
```

The compiled binary will be at `DoPHOT_C-master/working_data/dophot`.

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

Note: The DoPHOT C code in `DoPHOT_C-master/` is separately licensed under MIT
(with one file under Common Public License v1.0). See `DoPHOT_C-master/LICENSE`
for details.
