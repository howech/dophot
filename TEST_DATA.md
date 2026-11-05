# DoPHOT Test Data

**Location**: `../Testsuite/` relative to the project root (`Sahas_CDoPhot/`), i.e. a sibling directory of the project. Not part of the repository.

**Size**: ~374 MB (2× 187 MB FITS files + verification outputs)

## Contents

### Input Test Images
- `47Tuc_wsky_i_2024120600054_4.fits` (187 MB) — 47 Tucanae field image 1
- `47Tuc_wsky_i_2024120600056_7.fits` (187 MB) — 47 Tucanae field image 2

These are calibrated visit images in nJy flux units with WCS headers.

### Reference Outputs (Verify/ directory)

Expected pipeline outputs for validation:
- `.ap` — Aperture photometry results
- `.bap` — Background aperture photometry
- `.doq` — DoPHOT quality/measurements
- `.doqcap` — DoPHOT with aperture corrections
- `.rdcap` — **Final catalog** (positions, magnitudes, errors, WCS)
- `.fits` — Intermediate processed FITS
- `.meta` — Metadata

### Documentation

`runexamples.txt` — Instructions for running the IDL preprocessing pipeline:
```
@Expidl/setpath
prep_dp1_pim, '47Tuc_wsky_i_2024120600054_4', '47Tuc_emp_i_2024120600054_4', 1
```

This runs the complete workflow:
1. IDL preprocessing (parameter generation from image)
2. DoPHOT C code (PSF photometry)
3. Aperture corrections
4. WCS transformations
5. Output catalog

## Usage

### Phase 1b (Exploration)
- Test DoPHOT C code on real data
- Verify dophot_globals refactoring works end-to-end
- Extract reusable functions for parameter generation

### Phase 2 (Python Preprocessing)
- Convert prep_dp1_pim.pro to Python
- Validate intermediate outputs match Verify/ directory
- Ensure parameter generation produces correct tuning files

### Phase 3 (Rubin Integration)
- Full pipeline validation with test data
- Compare final catalogs against Verify/.rdcap files
- Performance benchmarking

## Data Origin

Provided by Abi Saha (DoPHOT domain expert) — 47 Tucanae globular cluster observations from Rubin/LSST pipeline (`reprocessVisitImage` output).

**Not added to git** — Test data is large and external to source code repository.
