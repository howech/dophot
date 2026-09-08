# DP2 FITS Data Usage Audit

**Date**: 2026-09-08  
**Status**: We extract data but don't fully use it

---

## Summary: What We Do vs. Don't Do

| Data | Extracted | Used | Status |
|------|-----------|------|--------|
| **Variance** | ✅ Yes | ❌ NO | Loaded but ignored |
| **Mask** | ✅ Yes | ❌ NO | Loaded but ignored |
| **WCS** | ✅ Yes | ⚠️ Partial | Only for coordinates, not for pixel scale |
| **Image** | ✅ Yes | ✅ YES | Used for PSF measurement |
| **Header** | ✅ Yes | ✅ Partial | Only GAIN/RDNOISE/SATURATE used |

---

## Detailed Breakdown

### 1. VARIANCE DATA ❌ (Completely Unused)

**What DP2 FITS provides:**
```
FITS structure:
  PRIMARY: Empty
  IMAGE:   2D image array (nJy units)
  MASK:    2D mask array
  VARIANCE: 2D variance array (propagated from all processing steps)
```

**What we extract:**
```python
# task.py:200
variance = calexp.variance.array if calexp.variance else None
```

**What we actually do with it:**
```python
# preprocess_wrapper.py:31
def run(self, image, variance=None, mask=None, header=None, work_dir=None):
    # ... 
    # NEVER USED - variance parameter ignored
```

**Where it should be used:**
1. **PSF measurement weighting** — Fit PSF with variance weighting
2. **Flux estimation errors** — Calculate error bars from variance
3. **Noise thresholds** — Use local variance for adaptive thresholds
4. **Quality flags** — Mark high-variance regions

**Current Impact:**
- ❌ PSF measurement ignores noise weighting
- ❌ No error bars on flux/magnitude measurements
- ❌ Using simple global noise estimate instead of local values
- ❌ Missing critical information about measurement precision

**Code Location**: Not used anywhere
```python
# Variance extracted but:
variance = calexp.variance.array  # Loaded
# Never passed to any processing function
```

---

### 2. MASK DATA ❌ (Completely Unused)

**What DP2 FITS provides:**
```
MASK extension has standardized bit flags:
  Bit 0: DETECTOR (bad pixel from detector)
  Bit 1: SENSOR (bad pixel from electronics)
  Bit 2: INTERPOLATED (pixel value interpolated)
  Bit 3: SATURATED (pixel saturated)
  Bit 4: CR (cosmic ray)
  Bit 5: EDGE (edge pixel)
  Bit 6: NO_DATA (no valid data)
  Bit 7: SUSPECT (suspicious value)
  Bits 8-15: Reserved
```

**What we extract:**
```python
# task.py:201
mask = calexp.mask.array if calexp.mask else None
```

**What we actually do with it:**
```python
# preprocess_wrapper.py:31
def run(self, image, variance=None, mask=None, ...):
    # NEVER USED - mask parameter ignored entirely
```

**Where it should be used:**
1. **Star detection** — Don't detect stars on masked pixels
2. **PSF measurement** — Don't fit PSF on bad/saturated pixels
3. **Photometry** — Don't use masked pixels in apertures
4. **Quality flags** — Mark sources near masks

**Current Impact:**
- ❌ Detecting "stars" on cosmic rays and bad pixels
- ❌ Fitting PSF on saturated/interpolated data
- ❌ Including bad pixels in photometry (biased fluxes)
- ❌ No quality flags about pixel contamination

**Code Location**: Not used anywhere
```python
# Mask extracted but never checked
# PSF measurement detects on all pixels regardless of mask
# DoPHOT runs on masked pixels
```

---

### 3. WCS COORDINATES ⚠️ (Partially Used)

**What DP2 FITS provides:**
```
WCS header in calexp metadata:
- CRPIX1, CRPIX2: Reference pixel
- CRVAL1, CRVAL2: Reference RA/Dec
- CD11, CD12, CD21, CD22: Rotation/scale matrix
- CTYPE1, CTYPE2: Coordinate system
- Also encodes pixel scale, rotation, distortions
```

**What we extract:**
```python
# task.py:202
header = calexp.getMetadata()
# Later in postprocess:
wcs = calexp.getWcs()
```

**What we actually do with it:**

```python
# postprocess.py:148-150
coords = wcs.pixelToSky(x_pix, y_pix)
catalog['RA'] = np.array([c.getRa().asDegrees() for c in coords])
catalog['Dec'] = np.array([c.getDec().asDegrees() for c in coords])
```

**What we DON'T use:**
1. ❌ **Pixel scale** — Not extracting plate scale (arcsec/pixel)
2. ❌ **Rotation** — Not accounting for field rotation
3. ❌ **Distortion** — Not applying optical distortion corrections
4. ❌ **Uncertainties** — Not propagating astrometric errors

**Impact:**
- ✅ Basic coordinate transformation works
- ⚠️ But we're missing pixel scale for aperture size calculations
- ⚠️ Not propagating astrometric uncertainties to catalog

**Missing code:**
```python
# Should extract and use:
pixel_scale = wcs.getPixelScale().asArcseconds()  # arcsec/pixel
# Then use for aperture definitions:
aperture_pixels = aperture_arcsec / pixel_scale

# Should propagate errors:
coord_err = wcs.getPixelOrigin().distanceFrom(...)  # or similar
```

---

## What SHOULD Be Happening

### DP2 Data Flow (Ideal)

```
DP2 FITS File
├── IMAGE extension
│   └─> Photometry input
├── VARIANCE extension
│   ├─> Weighting for PSF fit
│   ├─> Error bar calculation
│   └─> Noise-based thresholds
├── MASK extension
│   ├─> Pixel rejection in PSF fit
│   ├─> Bad pixel flagging
│   └─> Aperture contamination check
└── WCS in header
    ├─> Coordinate transformation
    ├─> Pixel scale calculation
    └─> Distortion corrections

All → DoPHOT → Weighted photometry
           → Proper error estimates
           → Quality flags
```

### Current Data Flow (Actual)

```
DP2 FITS File
├── IMAGE extension
│   └─> Used for PSF measurement ✅
├── VARIANCE extension
│   └─> Extracted but IGNORED ❌
├── MASK extension
│   └─> Extracted but IGNORED ❌
└── WCS in header
    └─> Used for coord transform only ⚠️

→ Basic photometry
→ No error estimates
→ No quality flags
```

---

## Code Gaps

### Gap 1: Variance Weighting in PSF Fit

**Should be:**
```python
# dophot_preprocess/psf_measurement.py:measure_psf_sigma()
def measure_psf_sigma(image, x, y, variance=None, box_size=21, debug=False):
    """
    Measure PSF width using variance-weighted fitting.
    """
    # Extract stamp
    stamp = extract_stamp(image, x, y, box_size)
    variance_stamp = extract_stamp(variance, x, y, box_size) if variance is not None else None
    
    # Fit with weights
    if variance_stamp is not None:
        weights = 1.0 / variance_stamp  # Inverse variance weighting
        sigma, amp = fit_gaussian(stamp, weights=weights)
    else:
        sigma, amp = fit_gaussian(stamp)
    
    return sigma, amp
```

**Currently:**
```python
# variance parameter accepted but never used
def measure_psf_sigma(image, x, y, box_size=21, debug=False):
    # No variance parameter at all
    stamp = ...
    sigma, amp = fit_gaussian(stamp)  # Unweighted
    return sigma, amp
```

---

### Gap 2: Mask Checking in PSF Measurement

**Should be:**
```python
# dophot_preprocess/psf_measurement.py:detect_bright_stars()
def detect_bright_stars(image, threshold, mask=None, ...):
    """
    Detect bright stars, excluding masked pixels.
    """
    peaks = find_peaks(image, threshold=threshold, box_size=11)
    
    if mask is not None:
        # Remove detections on masked pixels
        good = mask[peaks['y_peak'], peaks['x_peak']] == 0
        peaks = peaks[good]
    
    return peaks
```

**Currently:**
```python
# mask parameter not even in function signature
def detect_bright_stars(image, threshold=None, saturation=None, n_stars=None):
    peaks = find_peaks(image, threshold=threshold, box_size=11)
    # Detects on all pixels including cosmic rays, saturated, etc.
    return peaks
```

---

### Gap 3: Pixel Scale Usage for Apertures

**Should be:**
```python
# dophot_rubin/config.py
class DoPHOTConfig:
    apertureRadius = pexConfig.Field(
        dtype=float, default=2.0,
        doc="Aperture radius in arcseconds"  # Not pixels!
    )

# dophot_rubin/postprocess.py
def _apply_aperture_corrections(self, catalog, calexp, ...):
    # Get pixel scale from WCS
    pixel_scale = calexp.getWcs().getPixelScale().asArcseconds()
    
    # Convert aperture radius to pixels
    aperture_pixels = self.config.apertureRadius / pixel_scale
    
    # Now use for photometry
```

**Currently:**
```python
# No access to pixel scale
apertureRadius = 2.0  # Unclear units
# Aperture corrections don't actually use aperture radius
```

---

### Gap 4: Error Propagation

**Should be:**
```python
# After photometry with variance weighting:
flux_err = np.sqrt(  # Propagated from variance
    aperture_variance * (1 + aperture_area_variance)
)
mag_err = 2.5 / np.log(10) * flux_err / flux
ra_err, dec_err = transform_errors(x_err, y_err, wcs)
catalog['flux_err'] = flux_err
catalog['mag_err'] = mag_err
catalog['ra_err'] = ra_err
catalog['dec_err'] = dec_err
```

**Currently:**
```python
# No error propagation at all
catalog['flux'] = flux  # No uncertainties
catalog['mag_AB'] = mag  # No uncertainties
catalog['RA'] = ra  # No uncertainties
catalog['Dec'] = dec  # No uncertainties
```

---

## Impact Summary

| Missing Feature | Affects | Severity |
|-----------------|---------|----------|
| Variance weighting | PSF measurement accuracy | HIGH |
| Mask checking | Star detection quality | HIGH |
| Error propagation | Photometric uncertainty estimates | HIGH |
| Pixel scale usage | Aperture size accuracy | MEDIUM |
| WCS distortion | Astrometric accuracy | MEDIUM |

---

## Files That Need Changes

1. **dophot_preprocess/psf_measurement.py**
   - Add variance parameter to `measure_psf_sigma()`
   - Add mask parameter to `detect_bright_stars()`
   - Implement variance weighting
   - Implement mask rejection

2. **dophot_preprocess/parameter_generation.py**
   - Extract pixel scale from WCS
   - Use for box size calculations

3. **dophot_rubin/postprocess.py**
   - Extract pixel scale from WCS
   - Calculate aperture radius in pixels
   - Add error propagation
   - Use variance for error estimation

4. **dophot_rubin/config.py**
   - Change aperture radius units to arcseconds
   - Add precision/uncertainty config options

5. **dophot_rubin/execute_dophot.py**
   - Pass variance and mask to C code if available

---

## Honest Assessment

We're treating the DP2 FITS file like a **simple 2D image**, not like the **rich data product** it actually is.

The problem: **We load the data, we never use it.**

```python
variance = calexp.variance.array if calexp.variance else None  # ❌ Loaded, never used
mask = calexp.mask.array if calexp.mask else None              # ❌ Loaded, never used
wcs = calexp.getWcs()                                           # ⚠️ Used only for coords
```

This is a **critical oversight** for production photometry. Without using variance and mask, we're:
- Throwing away measurement precision information
- Including bad pixels in photometry
- Missing error bars on results
- Not leveraging Rubin's careful data processing

**Impact on results**: Could bias fluxes, underestimate errors, include contaminated sources.

**For Phase 3d validation**: This is something that should be fixed before running on real LSST data.
