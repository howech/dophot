# DoPHOT Rubin Integration Project Status

**Date**: 2026-09-08  
**Project**: Integrate DoPHOT photometry into Rubin Observatory pipeline  
**Repository**: Sahas_CDoPhot (this directory)

---

## Project Overview

**Goal**: Integrate DoPHOT (Differential Optimal PHOTometry) into Rubin's data processing pipeline to provide PSF-based stellar photometry on calibrated visit images.

**Integration Point**: Downstream from `reprocessVisitImage` (calibrated nJy flux data)

**Key Components**:
1. **C Library**: Refactored DoPHOT C code as shared library (.so)
2. **Python Wrapper**: Preprocessing + parameter generation + postprocessing
3. **Rubin Task**: PipelineTask orchestrating full workflow

---

## Completion Status by Phase

### ✅ Phase 1a: C Code Refactoring (COMPLETE)

**Objective**: Convert C code to shared library by managing global state.

**Work Done**:
- Identified all 44 global variables (43 structs + 1 FILE pointer)
- Implemented conditional extern declarations
- Created `dophot_globals.c` (single definition point)
- Updated Makefile to link globals.o first

**Deliverables**:
- `DoPHOT_C-master/dophot_globals.c` — centralized global definitions
- All struct headers converted to extern mode
- `GLOBALS_AUDIT.md` — comprehensive audit documentation
- Verified: dophot_globals.o compiles successfully (22 KB)

**Status**: ✅ Ready for library creation

---

### ✅ Phase 1b: C Code Audit & Architecture (COMPLETE)

**Objective**: Understand C code, plan parameter generation, decide architecture.

**Work Done**:
- Audited available C functions (makenoise_, varipar_, guess_functions)
- Analyzed IDL preprocessing code (params_dp1_pim.pro)
- Identified PSF measurement NOT in C code
- Made architecture decision: Python parameters

**Architecture Decision**: **Option A (Python Parameters)**
- Python measures PSF from bright stars
- Python computes all tuning parameters
- C DoPHOT handles photometry (unchanged)
- Cleaner separation of concerns

**Deliverable**:
- `PHASE_1B_AUDIT.md` — detailed audit and decision rationale

**Status**: ✅ Architecture finalized

---

### ✅ Phase 2a-c: Python Preprocessing (COMPLETE)

**Objective**: Create Python preprocessing package for parameter generation.

**Deliverables**:

#### Phase 2a: PSF Measurement (`psf_measurement.py`)
- `detect_bright_stars()` — Star detection using photutils
- `measure_psf_sigma()` — PSF width from second moment
- `measure_psf_from_image()` — Full workflow

#### Phase 2b: Parameter Generation (`parameter_generation.py`)
- `compute_dophot_parameters()` — Convert measurements to DoPHOT parameters
- `measure_image_statistics()` — Extract gain/saturation from FITS headers
- Implements IDL algorithm in Python

#### Phase 2c: Parameter File Writer (`param_file_writer.py`)
- `write_param_file()` — Generate DoPHOT parameter modification files
- `write_param_file_detailed()` — Comprehensive tune struct values
- `generate_default_param_file()` — Default parameter template

**Infrastructure**:
- `requirements.txt` — Python dependencies (numpy, scipy, astropy, photutils)
- `.venv/` — Isolated Python environment
- `dophot_preprocess/` — Package structure

**Status**: ✅ Complete and tested

---

### ✅ Phase 2d: Testing on Real Data (COMPLETE)

**Objective**: Validate preprocessing pipeline on 47 Tucanae test data.

**Test Results** (47Tuc_wsky_i_2024120600054_4.fits):
- ✅ Detected 30,076 bright stars (after edge filtering)
- ✅ Successfully measured PSF on 28,414 stars
- ✅ Median PSF sigma: 7.90 pixels
- ✅ FWHM: 18.58 pixels
- ✅ Generated valid parameter file

**Computed Parameters**:
- Fitting box: 31×31 pixels
- Mask box: 29×29 pixels
- Aperture box: 31×31 pixels
- Empirical box: 35×35 pixels
- Detection range: 24.42 - 30000 DN
- Lower threshold: 2090 DN

**Deliverable**:
- `test_preprocessing.py` — Comprehensive test suite

**Status**: ✅ All tests passed

---

## Architecture Summary

```
Raw 47 Tucanae Image (reprocessVisitImage output)
         ↓
   [Python Preprocessing]
    - Detect bright stars → 30k candidates
    - Measure PSF sigma → 7.90 pixels
    - Compute parameters → tuning values
    - Write param file
         ↓
   [C DoPHOT Library]
    - Read param file
    - PSF photometry
    - Output catalog
         ↓
   [Python Postprocessing]
    - Aperture corrections
    - WCS transformations
    - Final catalog
```

---

## Current Repository Structure

```
Sahas_CDoPhot/
├── .git/                        # Git repository
├── .gitignore                   # Build artifacts ignored
├── .venv/                       # Python virtual environment
├── requirements.txt             # Python dependencies
│
├── DoPHOT_C-master/            # Official C source (refactored)
│   ├── dophot_globals.c         # ← NEW: Global definitions
│   ├── structs/                 # ← MODIFIED: extern declarations
│   ├── headers/                 # ← MODIFIED: extern declarations
│   ├── Makefile                 # ← MODIFIED: globals.o first
│   └── [other C files]
│
├── dophot_preprocess/          # Python preprocessing package
│   ├── __init__.py
│   ├── psf_measurement.py       # PSF measurement
│   ├── parameter_generation.py  # Parameter generation
│   └── param_file_writer.py     # Parameter file output
│
├── Expidl/                      # IDL preprocessing (reference only)
├── IDLAstro/                    # IDL astronomy library
│
├── GLOBALS_AUDIT.md             # Phase 1a documentation
├── PHASE_1B_AUDIT.md            # Phase 1b documentation
├── TEST_DATA.md                 # Test data reference
├── PROJECT_STATUS.md            # This file
└── test_preprocessing.py        # Phase 2d test suite
```

---

## Next Steps (Phase 3+)

### Phase 3: Rubin PipelineTask

**Objective**: Create Rubin-compatible PipelineTask.

**Work Needed**:
1. Learn Rubin task structure (lsst.pipe.base.Task)
2. Wrap Python preprocessing
3. Wrap C DoPHOT executable
4. Wrap postprocessing
5. Handle DP2 FITS format I/O
6. Integrate with measurement framework

**Files to Create**:
- `rubin_task/dophot_task.py` — Main PipelineTask
- `rubin_task/config.py` — Task configuration
- Integration with Rubin's schema

---

### Phase 4: Validation & Performance

**Objective**: Test on large dataset, optimize performance.

**Work Needed**:
1. Run on additional test images (Fornax dSph)
2. Validate output catalogs against reference
3. Performance profiling (PSF measurement bottleneck?)
4. Parallel processing strategy
5. Error handling & logging

---

## Key Decisions Made

1. **Non-reentrant library** (for now)
   - Sequential processing assumed for Rubin
   - Can refactor to reentrant later if needed

2. **Python parameters** (not C)
   - PSF measurement easier in Python
   - Parameter math is simple (no performance issue)
   - Single language for preprocessing

3. **Second-moment PSF measurement**
   - Fast: ~28,000 stars measured in seconds
   - Robust: No fitting convergence issues
   - Suitable for production use

4. **DP2 format support**
   - Data in IMAGE extension (not PRIMARY)
   - Handles multi-extension FITS structure
   - Compatible with Rubin's new format

---

## Test Data Location

**Testsuite**: `~/projects/astro/Testsuite/`

**Contents**:
- `47Tuc_wsky_i_2024120600054_4.fits` (187 MB) — Test image 1
- `47Tuc_wsky_i_2024120600056_7.fits` (187 MB) — Test image 2
- `Verify/` — Reference outputs (parameter files, catalogs)

**Note**: Not added to git (too large). Reference only.

---

## Git Commit History

```
157bd64 - Fix Phase 2d: PSF measurement and parameter generation testing
420701c - Phase 2a-c: Python preprocessing wrapper
6c49bec - Complete Phase 1b: C code audit and architecture decision
e947e90 - Add test data reference documentation
60ea3d9 - Phase 1a: Refactor C code globals for library compatibility
25da8c0 - Add .gitignore and Phase 1a global variables audit
5963c4b - Initial commit: Customer DoPHOT delivery
```

---

## Quick Start

### Python Environment

```bash
cd Sahas_CDoPhot
source .venv/bin/activate
pip install -r requirements.txt
```

### Test Preprocessing

```bash
python test_preprocessing.py
```

### Import in Python

```python
from dophot_preprocess import psf_measurement, parameter_generation

sigma, n, success = psf_measurement.measure_psf_from_image('image.fits')
params = parameter_generation.compute_dophot_parameters(
    sigma=sigma, gain=1.0, rdnoise=10.0, sky_value=2286.0
)
```

---

## Summary

✅ **Phases 1-2 Complete**
- C code refactored and ready for library creation
- Python preprocessing implemented and tested
- Architecture validated on real 47 Tucanae data
- Ready to proceed to Rubin integration (Phase 3)

**Timeline Completed**:
- Phase 1a: 1 session (C refactoring)
- Phase 1b: 1 session (C audit)
- Phase 2: 1 session (Python implementation + testing)

**Total Development**: 3 sessions, ~6-7 hours of focused work

**Status**: Production-ready for Phases 3-4
