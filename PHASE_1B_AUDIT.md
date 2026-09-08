# Phase 1b: C Code Audit for Parameter Generation

**Status**: Exploration - Identify reusable functions and design Python parameter generation API

**Date**: 2026-09-04

---

## Key Finding: Parameter Generation Workflow

The IDL preprocessing code (`params_dp1_pim.pro`) auto-generates all DoPHOT tuning parameters from image characteristics:

### Input Data Required
- **Image data** (2D pixel array)
- **Gain** (electrons per DN) — from header
- **Readout noise** (electrons) — from header or default
- **Sky value** (DN) — computed from image statistics
- **PSF sigma** (pixels) — MUST be provided or measured from bright stars
- **Saturation value** — from header

### Computed Parameters (from params_dp1_pim.pro)

```
sigma (PSF width, input)
    ↓
FWHM = 2.35 * sigma

Noise estimation:
    nse_dn = sqrt(skyval*epdn + rdne²) / epdn

Box sizes (depends on beta4 PSF parameter):
    nfitbox = 2*nint(1.0 to 1.5 * FWHM) + 1  (clamped 9-31)
    maskbox = 1.5 * FWHM + 1
    apbox = 31
    empbox = 3*nfitbox (empirical model box, clamped 15-35)

Pixel thresholds:
    pxth = min(1.0, 1/(π*sigma²))  (pixel threshold for detection)
    thmin = 0.5 * nse_dn
    thmax = empstarz/2 (stellar magnitude limit)
    bottom = min(skyval - 4*nse_dn, skyval - 1.5*skyrms)

Readout noise handling:
    rdne = max(rdne, epdn + 1)  (ensure readout > gain)
```

---

## Available C Functions

### Image Processing
| Function | Header | Purpose | Inputs |
|----------|--------|---------|--------|
| `makenoise_()` | makenoise.h | Compute noise map from image | image, dimensions |
| `varipar_()` | varipar.h | Measure sky model variations | NSTOT, dimensions, model type |
| `guess1_()`, `guess2_()`, `guess3_()` | guess.h | PSF fitting (not generation) | A[], STARPAR[], position |

### Parameter Loading
| Function | Header | Purpose |
|----------|--------|---------|
| `tuneup_()` | tuneup.h | Load parameters from file |
| `paramfile_()` | paramfile.h | Parse parameter file |
| `readfits_()` | readfits.h | Read FITS image |

### Utility Math
| Header | Functions | Purpose |
|--------|-----------|---------|
| mini_mathlib.h | sqrt, min, max, etc. | Basic math |
| cast_arr.h | malloc_float_1darr, etc. | Memory allocation |

---

## What's **NOT** Currently in C Code

❌ **PSF measurement from bright stars** (CRITICAL FINDING)
- IDL workflow: getstars6() → detect bright stars → fitaper3() → fit PSF to each → median(sigma)
- C code has NO star detection or PSF-specific fitting functions
- These would need to be implemented or wrapped from external library
- **Decision**: PSF measurement should remain in Python (using scipy/photutils)

❌ **Automatic parameter generation**
- C code only reads pre-made parameter files
- No function to auto-generate parameters from image

❌ **Header parsing**
- Must read GAIN, RDNOISE, SATURATION from FITS headers
- Currently done by IDL; C code doesn't have this

---

## Proposed Parameter Generation API

For Python wrapper, we need to create a simple C interface:

```c
/* dophot_param_gen.h */

typedef struct {
    float sigma;        /* PSF FWHM in pixels (REQUIRED - must measure separately) */
    float gain;         /* Electrons per DN */
    float rdnoise;      /* Readout noise in electrons */
    float sky_value;    /* Sky value in DN */
    float sat_value;    /* Saturation value in DN */
    int beta4;          /* PSF shape parameter */
} dophot_image_stats_t;

typedef struct {
    float fwhm;
    float nse_dn;
    int nfitbox, maskbox, apbox, empbox;
    float pxth, thmin, thmax;
    float bottom;
} dophot_computed_params_t;

/* Compute all parameters from image statistics */
void dophot_compute_parameters(
    dophot_image_stats_t* stats,
    dophot_computed_params_t* params
);
```

---

## Phase 1b Tasks

### Track 1: ✓ COMPLETE
**Rubin parallelism assumption**: Sequential processing OK

### Track 2: C Code Audit

**Subtask 2a: Function Review** (1 hour)
- ✅ Identified available functions
- ✅ Found makenoise_() for noise measurement
- ✅ Located varipar_() for sky variation

**Subtask 2b: PSF Measurement** (2 hours)
- Search for bright star detection in C code
- Look for PSF fitting routines
- Determine if PSF measurement can be done in C or must stay in Python

**Subtask 2c: Create Parameter Generation Wrapper** (2-3 hours)
- Design dophot_param_gen.c (parameter calculation)
- Wrap math from params_dp1_pim.pro
- Test on Testsuite data

**Subtask 2d: Decision Point** (1 hour)
- Where should PSF measurement live? (Python or C)
- Can we call C parameter generation from Python easily?
- What's the cleanest architecture?

---

## Architecture Decision Needed

### Option A: Python-only Parameters
- Python measures PSF from bright stars (or uses external tool)
- Python calculates parameters using simple math
- Pros: No C dependencies, easy to test
- Cons: Duplicates parameter calculation logic

### Option B: C Parameters + Python Helper
- Python measures PSF, passes sigma to C
- C function computes all derived parameters
- Pros: Single source of truth, reusable
- Cons: Need ctypes binding for parameter struct

### **DECISION: Option A (Python Parameters)** ✓

**Audit Finding**: No PSF measurement or star detection in C code.

**Rationale**:
- PSF measurement (star detection + fitting) is not in C code, must be Python
- Parameter calculation is simple math from params_dp1_pim.pro
- Cleaner to keep all measurement in Python (single language, easier to test)
- Can always optimize to C later if performance critical

**Implementation Plan**:
1. **Phase 2a**: Python functions to measure PSF from bright stars
   - Star detection (photutils or scipy)
   - PSF fitting per star (Gaussian to each)
   - Median sigma from multiple stars
   
2. **Phase 2b**: Python function to compute parameters from measurements
   - Convert params_dp1_pim.pro math to Python
   - Takes (sigma, gain, rdnoise, sky, saturation) → returns all tuning parameters
   
3. **Phase 2c**: Parameter file generation
   - Write computed parameters to DoPHOT parameter file format
   - Ready to pass to C DoPHOT executable

---

## Completed Subtasks

✅ **Subtask 2a**: Function Review — Available C functions identified  
✅ **Subtask 2b**: PSF Measurement Search — NOT in C code, Python required  
✅ **Subtask 2d**: Architecture Decision — Option A (Python parameters)

## Next Phase

**Recommend**: Proceed to Phase 2 (Python Preprocessing Wrapper)
- Implement parameter generation in Python
- Test on Testsuite data (47 Tucanae images)
- Validate outputs match IDL reference
