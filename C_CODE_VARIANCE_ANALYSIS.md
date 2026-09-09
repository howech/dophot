# How DoPHOT C Code Actually Uses Variance Data

**Date**: 2026-09-09  
**Key Finding**: DoPHOT does NOT read variance from FITS files. It computes its own noise internally.

---

## Executive Summary

The C DoPHOT code:
1. ✅ Is **designed to read single-extension FITS only** (image data)
2. ✅ **Rejects multi-extension FITS files** with variance/mask extensions
3. ✅ **Computes its own noise map** from the image using `makenoise_()`
4. ✅ Uses this computed noise for weighting in all photometric fits

**Implication**: Our approach of writing only the image to FITS is **correct and expected by DoPHOT**.

However, **we still have a critical problem**: We're not using the variance data in Python for star detection and PSF measurement, even though we could.

---

## How DoPHOT Handles Noise

### Step 1: Read FITS File

**File**: `readfits.c`, lines 60-66

```c
if ((hdu_num != 1) || (hdu_type != 0) || (naxis != 2)){
     printf("NOT VALID FILE FOR DOPHOT ANALYSIS\n");
     printf("either too many extensions,\n");
     printf("          invalid HDU type,\n");
     return NULL;
}
```

**Requirement**: Exactly 1 HDU (no multi-extension FITS)
- `hdu_num != 1` → expects exactly 1 HDU
- `hdu_type != 0` → expects primary image HDU (not extension)

**This means**:
- ✅ Single-extension FITS with only image → **ACCEPTED**
- ❌ Multi-extension FITS with IMAGE+VARIANCE+MASK → **REJECTED**

---

### Step 2: Compute Noise Map

**File**: `build.c`, lines in build.c

```c
/* making noise array and starting the warmstart if flagged */
int** noise = malloc_int_2darr(nslow, nfast);
makenoise_(big, noise, &nfast, &nslow);
```

DoPHOT calls `makenoise_()` to create a noise map from the image data.

---

### Step 3: Noise Calculation Algorithm

**File**: `makenoise.c`, lines 36-58

```c
TEMP1 = (RNOISE/EPERDN)*(RNOISE/EPERDN);  /* readout noise squared */
TEMP2 = 1.0f/EPERDN;                      /* inverse gain */

for (I = 0; I < NSLOW; I++){
     for (J = 0; J < NFAST; J++){
          if (BIG[I][J] > 0){
               NOISE[I][J] = BIG[I][J]*TEMP2 + TEMP1;
               /*         ↑ photon noise      ↑ readout noise */
          }
          else{
               NOISE[I][J] = TEMP1;
          }
     }
}
```

**The Formula**:
```
NOISE[i,j] = image[i,j] / EPERDN + (RNOISE/EPERDN)²
           = image[i,j] * (1/gain) + (readout_noise/gain)²
           = image_value/gain + (readout_noise/gain)²
```

**In floating point (variance)**:
```
variance[i,j] = image[i,j] * gain + readout_noise²
NOISE[i,j] = variance[i,j] / gain²  (noise in DN)
```

---

## Comparison: C Code vs. DP2 Variance

### What C DoPHOT Does

```c
/* In makenoise.c */
NOISE[I][J] = BIG[I][J] * (1.0/EPERDN) + (RNOISE/EPERDN)²
```

Where:
- `BIG[I][J]` = image pixel value (DN)
- `EPERDN` = gain (electrons per DN)
- `RNOISE` = readout noise (electrons)

### What DP2 FITS Provides

```
VARIANCE extension contains:
var[i,j] = image[i,j] * gain + readout_noise²
         (in electrons²)
```

### Why They're Different

- **C code**: Computes noise in DN units, pixel-by-pixel from image intensity
- **DP2 variance**: Pre-computed in electrons², includes ALL error sources from processing

**The DP2 variance is MORE COMPLETE** because it includes:
- Photon noise (what C code computes)
- Readout noise (what C code computes)
- **Flat-field uncertainties** (what C code does NOT compute)
- **Gain variations** (what C code does NOT compute)
- **Cosmic ray masking errors** (what C code does NOT compute)
- **All other processing propagated errors** (what C code does NOT compute)

---

## The Real Problem

DoPHOT's `makenoise_()` is a **simplified noise model** that:
- ✅ Works for basic photometry
- ❌ Ignores spatial gain variations
- ❌ Ignores flat-field uncertainties
- ❌ Uses constant gain/readout noise (not per-pixel)

Meanwhile, **Rubin's DP2 variance**:
- ✅ Has full error propagation
- ✅ Accounts for all processing steps
- ✅ Has per-pixel uncertainties

---

## The Architecture Mismatch

```
Ideal Flow (Using DP2 data):
  DP2 FITS (IMAGE + VARIANCE + MASK)
    ↓
  Python preprocessing:
    - Use variance for weighted PSF fit
    - Use mask to reject bad pixels
    - Use mask to flag contaminated sources
    ↓
  C DoPHOT:
    - Uses pre-weighted star positions
    - Ignores bad pixels (already filtered)
    - Gets high-quality input

Current Flow (Our Implementation):
  DP2 FITS (IMAGE + VARIANCE + MASK)
    ↓
  Extract IMAGE only, discard VARIANCE + MASK
    ↓
  Python preprocessing:
    - Unweighted PSF fit (uses all pixels equally)
    - No mask checking (cosmic rays included)
    - No error tracking
    ↓
  C DoPHOT:
    - Gets degraded input
    - Computes its own simple noise from image
    - No benefit from DP2 error propagation
```

---

## Key Findings

### 1. DoPHOT Does NOT Read Variance from FITS ✅
- Only reads single-extension FITS files
- Rejects multi-extension FITS
- This is BY DESIGN

### 2. DoPHOT Computes Its Own Noise ✅
- Creates noise map from image using `makenoise_()`
- Formula: `noise[i,j] = image[i,j]/gain + readout_noise²`
- Same formula we use in Python parameter generation

### 3. We're Stripping Data Unnecessarily ❌
- We extract DP2 variance and mask from Python
- We don't use them in Python
- We strip them before C code
- C code never knows they existed

### 4. DP2 Variance is Better Than C Computation ✅
- DP2 has full error propagation
- C code has simplified model
- We should use DP2 variance in Python preprocessing

---

## What We SHOULD Be Doing

```python
# Instead of this:
sigma, n_stars, success = self._measure_psf(image, image_stats)

# We should do this:
sigma, n_stars, success = self._measure_psf(
    image, 
    variance=calexp.variance.array,  # Use for weighting
    mask=calexp.mask.array,          # Reject bad pixels
    image_stats=image_stats
)

# And write only image to FITS for C code
# (C code doesn't expect variance anyway)

# But use variance in Python for:
# 1. Weighted PSF fitting
# 2. Error bar calculation
# 3. Quality flagging
```

---

## Bottom Line

| Question | Answer | Implication |
|----------|--------|-------------|
| Does C code read variance from FITS? | ❌ NO | Our approach is correct |
| Does C code compute its own noise? | ✅ YES | C code is self-contained |
| Should we pass variance to C code? | ❌ NO | Not designed for it |
| Should we use variance in Python? | ✅ YES | We should! |
| Is DP2 variance better than C noise? | ✅ YES | Use it for weighting |

**Verdict**: Our approach of writing only image to FITS is **correct** for DoPHOT. But we should **use the DP2 variance and mask in our Python code** for better star detection, PSF measurement weighting, and error propagation.

---

## Conclusion

The user was right to question "doesn't C use variance?" The answer is:
- **C DoPHOT doesn't read variance from FITS** (by design)
- **C DoPHOT computes its own simple noise map** (which is adequate for photometry)
- **But we should use the DP2 variance in Python** (for preprocessing, not for passing to C)

This isn't a problem with passing data to C. It's a missed opportunity to use better uncertainty data in our Python preprocessing.
