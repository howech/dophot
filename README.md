# Sahas_CDoPhot

Project root for the DoPHOT PSF photometry integration. This directory (`Sahas_CDoPhot/`)
is the root of the project: every relative path in the project documentation is relative to it.
Run all commands below from this directory.

- **Package documentation:** [README_PACKAGE.md](README_PACKAGE.md) (installed with the Python package)
- **Project status and history:** [PROJECT_STATUS.md](PROJECT_STATUS.md)
- **Test data:** [TEST_DATA.md](TEST_DATA.md)

## Layout

```
Sahas_CDoPhot/
├── README.md, README_PACKAGE.md, PROJECT_STATUS.md, TEST_DATA.md
├── pyproject.toml, setup.py, MANIFEST.in   # packaging (setup.py builds the DoPHOT executable)
├── requirements.txt                        # development dependencies
├── LICENSE
├── dophot_rubin/                           # Python package
│   ├── config.py, execute_dophot.py, preprocess_wrapper.py, psf_measurement.py, ...
│   ├── tests/                              # pytest suite
│   └── dophot_c/                           # DoPHOT C source, Makefile, verification data
│       └── working_data/                   # build output: dophot executable, param_default_c
├── scripts/
│   ├── run_dophot.py                       # command-line pipeline: FITS image -> catalog
│   └── build_linux_wheel.sh                # builds the manylinux wheel (see below)
├── examples/                               # end-to-end and verification scripts
├── Expidl/, IDLAstro/                      # original IDL reference code
└── .github/workflows/build-wheels.yml      # CI: Linux wheel and sdist
```

## Building the DoPHOT executable

The Python code runs the DoPHOT executable, which is built from the C source in
`dophot_rubin/dophot_c/`. Building requires gcc and CFITSIO.

```bash
cd dophot_rubin/dophot_c
make dophot
```

The executable is written to `dophot_rubin/dophot_c/working_data/dophot`. Installing the
package with `pip install -e .` from this directory builds it automatically (`setup.py` runs `make`).

## Installing

From this directory, in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .            # development install (builds the executable)
```

To install the prebuilt Linux wheel instead, pass its path to pip:

```bash
pip install dist/dophot_rubin-0.1.0-py3-none-manylinux_2_28_x86_64.whl
```

## Running DoPHOT on an image

```bash
python scripts/run_dophot.py path/to/image.fits -o catalog.ecsv --workdir work/
```

## Running the tests

```bash
pytest dophot_rubin/tests
python examples/test_e2e.py     # end-to-end run on the verification image
```

Known issue: `test_full_pipeline` fails. The pipeline detects 316 objects on the verification image, while the reference catalog in `dophot_c/verif_data/compare_out/` lists 1124 (379 of them type 1, against 81 detected). The cause is not yet investigated; the test is the check for this gap and is left failing on purpose.

`test_e2e.py` and the reference-comparison tests use the verification image in
`dophot_rubin/dophot_c/verif_data/`. The 47 Tucanae test data lives outside the project
root; see [TEST_DATA.md](TEST_DATA.md).

## Building the Linux wheel

```bash
docker run --rm -v "$PWD:/src" -w /src quay.io/pypa/manylinux_2_28_x86_64 scripts/build_linux_wheel.sh
```

The wheel is written to `dist/`. macOS and Windows wheels are not yet supported.
