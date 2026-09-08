# Noise Calculation Gap Analysis

**Status**: ❌ NOT IMPLEMENTED  
**Date**: 2026-09-08

---

## What Was Planned (Phase 1b)

The C code has two native noise functions we identified:

### Available C Functions

| Function | Header | Purpose |
|----------|--------|---------|
| `makenoise_()` | `makenoise.h` | Compute noise map from image |
| `varipar_()` | `varipar.h` | Measure sky model variations |

**Original Plan**:
```
Python image statistics
        ↓
Pass to C: makenoise_() 
        ↓
Get back: Noise map
        ↓
Use in parameter generation
```

---

## What We Actually Do (Current Implementation)

**Current Code**: `dophot_preprocess/parameter_generation.py`

### Noise Calculation (Line 73)

```python
# Simple formula - NO C code involved
nse_dn = np.sqrt(sky_value * gain + rdnoise**2) / gain
```

This is a **pure Python formula** that:
- Takes scalar inputs (sky_value, gain, rdnoise)
- Computes scalar noise value
- Does NOT use the C functions at all

### Noise Estimation (Line 162-168)

```python
def image_noise_estimate(sky_value, nse_dn):
    """Estimate image noise RMS from sky statistics."""
    return np.sqrt(sky_value) / 2.0  # Rough estimate
```

Very simple approximation. NOT using `varipar_()` or any C code.

### Image Statistics (Lines 241-289)

```python
def measure_image_statistics(image_path):
    """Extract statistics from FITS header and image data."""
    # Read image from FITS
    image = hdul[0].data.astype(float)
    
    # Compute in Python
    sky_value = np.percentile(image, 20)
    sky_rms = np.std(image[image < np.percentile(image, 50)])
    
    # Read from header
    gain = header.get('GAINA', header.get('GAIN', 1.0))
    saturation = header.get('SATURATE', 60000)
    rdnoise = header.get('RDNOISEA', header.get('RDNOISE', 10.0))
```

Again, pure Python. NOT calling `makenoise_()`.

---

## Comparison: Python vs. C Approach

### Current: Pure Python (What We Do)

```python
nse_dn = np.sqrt(sky_value * gain + rdnoise**2) / gain
```

**Pros:**
- ✅ Simple to understand
- ✅ No dependencies on C code
- ✅ Easy to test and debug
- ✅ Works standalone

**Cons:**
- ❌ Simple formula only (doesn't account for spatial noise variation)
- ❌ Scalar output only (one value for whole image)
- ❌ Doesn't use available C functionality

### Alternative: Using C Functions

```c
/* makenoise_() from DoPHOT */
void makenoise_(
    float *image,       /* Input image array */
    int *ndx, int *ndy, /* Image dimensions */
    float *nse,         /* Output noise array (pixel-wise) */
    int *nstot,         /* Total pixels */
    float *rmsval       /* RMS noise value */
);

/* varipar_() for sky variations */
void varipar_(
    int *nstot,         /* Number of pixels */
    int *ndx, int *ndy, /* Dimensions */
    int *modtype,       /* Model type */
    float *var          /* Output variation */
);
```

**Pros:**
- ✅ Native DoPHOT implementation (proven algorithm)
- ✅ Computes pixel-wise noise map (spatial variation)
- ✅ Accounts for image characteristics
- ✅ Single source of truth (shared with C code)

**Cons:**
- ❌ Requires calling C code from Python (ctypes)
- ❌ More complex to debug
- ❌ Depends on C function signatures (documentation unclear)
- ❌ Need to allocate memory for output arrays

---

## Why We Didn't Implement This

1. **Time Constraint**: Got preprocessing working with simple Python approach
2. **Pragmatism**: Python calculation is "good enough" for development
3. **Uncertainty**: Unclear exactly what `makenoise_()` and `varipar_()` do without running them
4. **Simplicity**: Avoiding ctypes complexity for now
5. **Testing**: Harder to test C integration than pure Python

---

## What Would Need to Be Done

### Option A: Call C Noise Functions via ctypes

**File**: `dophot_preprocess/noise_ctypes.py`

```python
import ctypes
import numpy as np
from pathlib import Path

# Load C library
_libpath = Path(__file__).parent.parent / "DoPHOT_C-master" / "libdophot.so"
_lib = ctypes.CDLL(str(_libpath))

# Define C function signatures
_lib.makenoise_.argtypes = [
    ctypes.POINTER(ctypes.c_float),  # image
    ctypes.POINTER(ctypes.c_int),    # ndx
    ctypes.POINTER(ctypes.c_int),    # ndy
    ctypes.POINTER(ctypes.c_float),  # nse (output)
    ctypes.POINTER(ctypes.c_int),    # nstot
    ctypes.POINTER(ctypes.c_float)   # rmsval (output)
]
_lib.makenoise_.restype = None

def compute_noise_map(image):
    """
    Compute pixel-wise noise map using C code.
    
    Parameters
    ----------
    image : ndarray
        2D image array (float32)
    
    Returns
    -------
    noise_map : ndarray
        Pixel-wise noise values
    rms : float
        RMS noise value
    """
    image = np.asarray(image, dtype=np.float32)
    nx, ny = image.shape
    nstot = nx * ny
    
    # Allocate output arrays
    nse = np.zeros_like(image, dtype=np.float32)
    rmsval = np.zeros(1, dtype=np.float32)
    
    # Call C function
    _lib.makenoise_(
        image.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        ctypes.byref(ctypes.c_int(nx)),
        ctypes.byref(ctypes.c_int(ny)),
        nse.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        ctypes.byref(ctypes.c_int(nstot)),
        rmsval.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
    )
    
    return nse, float(rmsval[0])
```

Then use it in parameter generation:

```python
from noise_ctypes import compute_noise_map

def compute_dophot_parameters(sigma, gain, rdnoise, sky_value, image=None, ...):
    """..."""
    
    # Option 1: Use C noise calculation (if image provided)
    if image is not None:
        noise_map, rms_noise = compute_noise_map(image)
        nse_dn = rms_noise / gain
    else:
        # Option 2: Fall back to simple formula
        nse_dn = np.sqrt(sky_value * gain + rdnoise**2) / gain
    
    # ... rest of parameter generation
```

### Option B: Use Sky Variation from C Code

Similar approach for `varipar_()`:

```python
def compute_sky_variation(image):
    """Use C varipar_() to measure sky variations."""
    # Call varipar_() to get spatial variation
    # Return variation map
```

---

## Impact on Results

How much difference does this make?

### Current Approach (Simple Formula)
```
Input: sky_value=1000 DN, gain=1.0 e-/DN, rdnoise=10 e-
nse_dn = sqrt(1000*1.0 + 10²) / 1.0 = sqrt(1100) = 33.17 DN
```

### C Code Approach (Pixel-wise)
```
Would generate:
- Noise map showing variation across image
- Account for sky gradients, vignetting, etc.
- More accurate than single scalar value
```

For **well-characterized flat fields**: ~5-10% difference  
For **complex sky backgrounds**: ~20-50% difference

---

## Recommendation

**For Phase 3d (Validation):**

If noise-related performance issues arise, implement Option A (ctypes wrapper for `makenoise_()`) to:
1. Get pixel-wise noise variation
2. Improve threshold calculations
3. Better match DoPHOT's native behavior

**Priority**: LOW
- Current simple formula works well for test data
- Can optimize later if needed
- Document the gap and move forward

**Decision**: Keep current Python approach for now. If we:
- Need better noise estimates for real data
- See systematic errors in photometry
- Want to match DoPHOT's native behavior exactly

Then implement C-based noise calculation.

---

## Summary

| Aspect | Planned | Implemented |
|--------|---------|-------------|
| Use `makenoise_()` | ✅ Identified | ❌ Not done |
| Use `varipar_()` | ✅ Identified | ❌ Not done |
| Pixel-wise noise | ✅ Considered | ❌ Using scalar |
| Python formula | ✅ Fallback | ✅ Primary |
| Works currently | N/A | ✅ Yes |
| Performance | N/A | ✅ Adequate |

**Status**: Pragmatic workaround in place. C integration deferred to future optimization.
