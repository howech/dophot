# C Code Architecture Audit: Supporting DP2 Variance Data

**Date**: 2026-09-09  
**Goal**: Enable DoPHOT to read and use variance data from DP2 FITS files instead of computing noise internally

---

## Current Architecture

### FITS File Handling (readfits.c:60-66)

```c
if ((hdu_num != 1) || (hdu_type != 0) || (naxis != 2)){
     printf("NOT VALID FILE FOR DOPHOT ANALYSIS\n");
     printf("either too many extensions,\n");
     printf("          invalid HDU type,\n");
     return NULL;
}
```

**Current Behavior:**
- ✅ Accepts: Single-extension FITS (image only)
- ❌ Rejects: Multi-extension FITS (IMAGE + VARIANCE + MASK)
- ✅ Returns: 2D image array `int** big`

**Problem**: DP2 FITS files have 4 HDUs:
1. PRIMARY (empty or header)
2. IMAGE (the science data)
3. MASK (pixel quality flags)
4. VARIANCE (uncertainty estimates)

---

### Noise Calculation (build.c:313-314, makenoise.c:36-58)

```c
/* build.c */
int** noise = malloc_int_2darr(nslow, nfast);
makenoise_(big, noise, &nfast, &nslow);

/* makenoise.c formula */
NOISE[i,j] = image[i,j]/gain + (readout_noise/gain)²
```

**Current Behavior:**
- Computes pixel-wise noise map from image intensity
- Uses global gain and readout noise parameters
- Simplified model (photon noise + readout noise only)

**Problem**: Ignores pre-computed DP2 variance which includes:
- Photon noise ✅
- Readout noise ✅
- Flat-field uncertainties ✅ (NOT in C code)
- Gain variations ✅ (NOT in C code)
- Cosmic ray masking errors ✅ (NOT in C code)

---

### Pipeline Data Flow (build.c:313-450)

```
readfits_(image_file)  →  big[nslow][nfast]
                             ↓
                        makenoise_(big)  →  noise[nslow][nfast]
                             ↓
                        USED BY:
                        - isearch_() (line 415)
                        - shape_() (line 420)
                        - bestab_() (line 441)
                        - improve_() (line 450)
                        - warmstart_() (line 320)
```

**All these functions pass noise array:**
```c
isearch_(model2d, big, noise, &nfast, &nslow);
shape_(model2d, model4d, big, noise, &nfast, &nslow);
bestab_(model2d, big, noise, &nfast, &nslow);
improve_(model2d, big, noise, &nfast, &nslow);
warmstart_(model2d, big, noise, &nfast, &nslow, warmstartfile);
```

---

## Changes Required

### 1. Modify readfits.c: Accept Multi-Extension FITS

**Current Code (Lines 47-66):**
```c
fits_get_num_hdus(fptr, &hdu_num, &fio_err);
fits_get_hdu_type(fptr, &hdu_type, &fio_err);
fits_read_key(fptr, TSHORT, "NAXIS", &naxis, NAXIS_comment, &fio_err);
if (file_ver != 0){ ... }
if ((hdu_num != 1) || (hdu_type != 0) || (naxis != 2)){
     printf("NOT VALID FILE FOR DOPHOT ANALYSIS\n");
     return NULL;
}
```

**Required Changes:**

Option A: Accept both single- and multi-extension FITS
```c
// Allow either:
// - 1 HDU (traditional single-extension)
// - 4 HDUs (DP2 format: PRIMARY + IMAGE + MASK + VARIANCE)
if ((hdu_num != 1 && hdu_num != 4) || (hdu_type != 0) || (naxis != 2)){
     printf("NOT VALID FILE FOR DOPHOT ANALYSIS\n");
     return NULL;
}

// If DP2 format, navigate to IMAGE HDU
if (hdu_num == 4){
     fits_movabs_hdu(fptr, 2, NULL, &fio_err);  // Move to IMAGE extension
}
```

**Why this works:**
- ✅ Single-extension FITS: hdu_num=1, reads PRIMARY directly
- ✅ DP2 FITS: hdu_num=4, moves to IMAGE (HDU 2)
- ✅ Backward compatible with existing single-extension files

---

### 2. Modify readfits.c: Create New Function to Read Variance

**New Function: readfits_variance.c**

```c
float** readfits_variance_(char* r_file, int nx, int ny)
{
     fitsfile* fptr;
     int fio_err = 0;
     int hdu_num;
     float* var1d;
     float** var2d;
     long npixels = ny * nx;
     long fpixel[2] = {1, 1};
     float nullval = 0.0;
     int anynull;
     
     fits_open_file(&fptr, r_file, 0, &fio_err);
     if (fio_err != 0) return NULL;
     
     fits_get_num_hdus(fptr, &hdu_num, &fio_err);
     
     // Single-extension: no variance available
     if (hdu_num == 1){
          fits_close_file(fptr, &fio_err);
          return NULL;  // Signal: use makenoise_ instead
     }
     
     // DP2 format: read VARIANCE extension (HDU 4)
     if (hdu_num >= 4){
          fits_movabs_hdu(fptr, 4, NULL, &fio_err);  // Move to VARIANCE
          if (fio_err != 0){
               fits_close_file(fptr, &fio_err);
               return NULL;
          }
          
          var1d = malloc_float_1darr(npixels);
          var2d = malloc_float_2darr(ny, nx);
          
          fits_read_pix(fptr, TFLOAT, fpixel, npixels, &nullval,
               var1d, &anynull, &fio_err);
          
          if (fio_err != 0){
               fits_close_file(fptr, &fio_err);
               free(var1d);
               return NULL;
          }
          
          recast_float_1dto2darr(ny, nx, var1d, var2d);
          free(var1d);
          fits_close_file(fptr, &fio_err);
          return var2d;
     }
     
     fits_close_file(fptr, &fio_err);
     return NULL;
}
```

**Key Features:**
- ✅ Returns NULL if no variance available (backward compatible)
- ✅ Reads from HDU 4 (VARIANCE extension)
- ✅ Returns float array (variance in electrons²)

---

### 3. Modify makenoise.c: Accept Pre-Computed Variance

**Current Code (makenoise.c:36-58):**
```c
void makenoise_(float *image, int *ndx, int *ndy,
     float *nse, int *nstot, float *rmsval)
{
     float TEMP1 = (RNOISE/EPERDN)*(RNOISE/EPERDN);
     float TEMP2 = 1.0f/EPERDN;
     for (I = 0; I < NSLOW; I++){
          for (J = 0; J < NFAST; J++){
               if (BIG[I][J] > 0){
                    NOISE[I][J] = BIG[I][J]*TEMP2 + TEMP1;
               }
          }
     }
}
```

**Option 1: New variant function makenoise_from_variance_**

```c
void makenoise_from_variance_(
     float** variance,      // Input: DP2 variance array
     int** noise,          // Output: noise in DN
     int* ndx, int* ndy,
     float* gain,          // Gain factor for conversion
     float* rmsval)        // Output: RMS noise
{
     float TEMP = 1.0f / (*gain);
     float sum = 0.0f;
     int i, j, nstot = (*ndx) * (*ndy);
     
     for (i = 0; i < *ndy; i++){
          for (j = 0; j < *ndx; j++){
               // variance is in electrons²
               // Convert to DN: noise² = var/gain²
               // noise = sqrt(var) / gain
               noise[i][j] = (int)(sqrt(variance[i][j]) * TEMP);
               sum += noise[i][j];
          }
     }
     
     *rmsval = sum / nstot;
}
```

**Option 2: Modify makenoise_ to check if variance provided**

```c
void makenoise_(float** image, int** noise, int* ndx, int* ndy,
     float** variance)  // NEW parameter
{
     if (variance != NULL){
          // Use DP2 variance
          makenoise_from_variance_(variance, noise, ndx, ndy, 
               &tune_gain, &rmsval);
     } else {
          // Fall back to original algorithm
          // ... existing code ...
     }
}
```

---

### 4. Modify build.c: Read and Pass Variance

**Current Code (build.c:283-314):**
```c
int nx, ny;
int** big = readfits_(files[0], &nx, &ny);
int nfast = undergnd_.NFAST = nx;
int nslow = undergnd_.NSLOW = ny;

int** noise = malloc_int_2darr(nslow, nfast);
makenoise_(big, noise, &nfast, &nslow);
```

**Required Changes:**
```c
int nx, ny;
int** big = readfits_(files[0], &nx, &ny);
int nfast = undergnd_.NFAST = nx;
int nslow = undergnd_.NSLOW = ny;

// TRY to read variance from DP2 FITS
float** variance = readfits_variance_(files[0], nx, ny);

// Allocate noise array
int** noise = malloc_int_2darr(nslow, nfast);

// Use variance if available, otherwise compute
if (variance != NULL){
     // Convert DP2 variance to noise in DN
     makenoise_from_variance_(variance, noise, &nfast, &nslow, 
          &tune_gain);
     if (lverb > 10){
          fprintf(logfile, "Using DP2 FITS variance data\n");
     }
} else {
     // Fall back to original makenoise_
     makenoise_(big, noise, &nfast, &nslow);
     if (lverb > 10){
          fprintf(logfile, "Computing noise from image\n");
     }
}
```

---

## Implementation Roadmap

### Phase 1: Read Multi-Extension FITS (3-4 hours)
- [ ] Modify readfits.c to accept hdu_num=4 (DP2 format)
- [ ] Add logic to move to IMAGE extension when needed
- [ ] Test with DP2 FITS files
- [ ] Verify backward compatibility with single-extension FITS

### Phase 2: Read Variance Extension (2-3 hours)
- [ ] Create readfits_variance.c
- [ ] Read VARIANCE extension (HDU 4)
- [ ] Convert float32 variance to proper units
- [ ] Handle missing variance gracefully

### Phase 3: Integrate Variance into Noise Calculation (2-3 hours)
- [ ] Create makenoise_from_variance_()
- [ ] Convert electrons² to DN units
- [ ] Update makenoise_() to accept variance parameter
- [ ] Maintain backward compatibility

### Phase 4: Update build.c Pipeline (1-2 hours)
- [ ] Add variance reading to main()
- [ ] Call appropriate makenoise variant
- [ ] Add logging for which source used
- [ ] Test full pipeline

### Phase 5: Verification (2-3 hours)
- [ ] Test on single-extension FITS (backward compat)
- [ ] Test on DP2 multi-extension FITS
- [ ] Compare photometry results
- [ ] Verify noise levels are sensible

**Total Effort**: ~12-15 hours

---

## Data Format Conversion

### DP2 Variance → DN Noise

**DP2 FITS VARIANCE Extension:**
- Contains: variance in electrons²
- Type: 32-bit float
- Formula: `var[i,j] = image[i,j]*gain + readout_noise²`

**DoPHOT noise (DN units):**
- Contains: noise estimate in DN
- Type: 32-bit int (currently, could be float)
- Formula: `noise[i,j] = sqrt(var[i,j]) / gain`

**Conversion:**
```c
// DP2 variance in electrons²
float var_e2 = variance[i,j];

// Convert to DN
float noise_dn = sqrt(var_e2) / gain;

// Store in noise array
noise[i][j] = (int)(noise_dn);
```

---

## Backward Compatibility

### Single-Extension FITS Files
- readfits.c: hdu_num=1, reads PRIMARY ✅
- readfits_variance_(): returns NULL ✅
- build.c: calls makenoise_() (original algorithm) ✅
- **Result**: Unchanged behavior ✅

### DP2 Multi-Extension FITS Files  
- readfits.c: hdu_num=4, reads HDU 2 (IMAGE) ✅
- readfits_variance_(): reads HDU 4 (VARIANCE) ✅
- build.c: calls makenoise_from_variance_() ✅
- **Result**: Uses DP2 variance for noise ✅

---

## Risk Analysis

### Low Risk ✅
- Backward compatibility maintained
- Variance reading isolated in separate function
- Existing code paths unchanged if variance unavailable
- No changes to core algorithms

### Medium Risk ⚠️
- Data type conversions (float → int)
- Unit conversions (electrons² → DN)
- May need tuning of conversion factors

### High Risk ❌
- None identified

---

## Testing Strategy

### Unit Tests
1. **readfits_variance_()**
   - Read DP2 FITS, verify values in correct range
   - Handle missing VARIANCE extension
   - Handle corrupted files

2. **makenoise_from_variance_()**
   - Verify conversion formulas
   - Compare with makenoise_() on simple images
   - Check RMS value calculation

3. **Integration**
   - Run full pipeline on DP2 FITS
   - Run full pipeline on single-extension FITS
   - Compare photometric results

### Validation Tests
1. Compare noise maps (DP2 variance vs. computed)
2. Check photometry consistency
3. Verify astrometry unaffected
4. Profile runtime impact

---

## Migration Strategy for Python Code

Once C code supports DP2 variance:

### Current Python Code
```python
# dophot_rubin/execute_dophot.py:94-100
fits.writeto(str(fits_file), calexp.image.array, overwrite=True)
# Only writing image - variance is lost
```

### Future Python Code
```python
# dophot_rubin/execute_dophot.py
hdul = fits.HDUList([
    fits.PrimaryHDU(),
    fits.ImageHDU(calexp.image.array, name='IMAGE'),
    fits.ImageHDU(calexp.mask.array, name='MASK'),
    fits.ImageHDU(calexp.variance.array, name='VARIANCE'),
])
hdul.writeto(str(fits_file), overwrite=True)
# Write full DP2 structure for C code to use
```

---

---

## ADDITIONAL REQUIREMENT: Unit System Support (DN vs. nanojansky)

**Goal**: Enable DoPHOT to work with **both DN and nanojansky (nJy)** units

### Current State: DN-Only

All DoPHOT code assumes **Data Numbers (DN)** units:

**readfits.c:**
- Reads image as int (DN)
- Returns `int** big`

**makenoise.c:**
- Computes noise in DN: `noise = image/gain + (rdnoise/gain)²`
- Uses gain (electrons/DN) conversion

**build.c and all fitting code:**
- All thresholds in DN (tune3_.tmin, tune3_.tmax)
- Sky subtraction in DN
- Magnitude conversion assumes DN
- Every fitting routine assumes DN-based photometry

**build.c thresholds (DN-based):**
```c
search_.thresh = tune3_.tmin;      // Starting threshold in DN
while (search_.thresh*powf(2, tune3_.tfac) <= tune3_.tmax){
     // Threshold sweep in DN
}
```

**Parameter file values (DN-based):**
```
THRESHMIN = 24.42  # DN
THRESHMAX = 30000  # DN
```

### DP2 FITS Reality: Usually nanojansky

**What Rubin LSST produces:**
- IMAGE extension: flux-calibrated in **nanojansky (nJy)**
- VARIANCE extension: variance in **nJy²**
- No "gain" in traditional sense (calibrated to nJy)
- No readout noise in DN (included in variance)

**Example DP2 FITS values:**
```
IMAGE: 1000 nJy per pixel (not DN)
VARIANCE: 100 nJy² (photon noise from calibration)
```

### The Problem

Currently, if you pass DP2 FITS (nJy units) to DoPHOT:
- C code interprets nJy values as DN
- Thresholds are way wrong (1000 nJy interpreted as 1000 DN)
- Noise calculation breaks (gain factor doesn't apply to nJy)
- Magnitude calibration assumes DN → magnitude conversion

**Example failure:**
```
Actual: 1000 nJy threshold
Wrong:  DoPHOT reads as 1000 DN
        Uses gain (e.g., 1.0 e/DN) incorrectly
        Interprets small nJy values as noise
        Detects nothing meaningful
```

---

## Required Changes: Unit Awareness

### 1. Detect Image Units from FITS Header

**New Function: detect_image_units.c**

```c
enum ImageUnits {
     UNIT_DN = 0,           // Data Numbers
     UNIT_NJY = 1,          // nanojansky (Rubin DP2)
};

enum ImageUnits detect_image_units_(char* fits_file)
{
     fitsfile* fptr;
     char unit_str[FLEN_VALUE];
     int fio_err = 0;
     
     fits_open_file(&fptr, fits_file, 0, &fio_err);
     
     // DP2 FITS: IMAGE extension has BUNIT = 'nJy'
     fits_movabs_hdu(fptr, 2, NULL, &fio_err);  // IMAGE extension
     fits_read_key(fptr, TSTRING, "BUNIT", unit_str, NULL, &fio_err);
     
     fits_close_file(fptr, &fio_err);
     
     if (fio_err == 0){
          if (strncmp(unit_str, "nJy", 3) == 0){
               return UNIT_NJY;
          }
     }
     
     // Default: DN
     return UNIT_DN;
}
```

**Rubin DP2 FITS headers have:**
```
BUNIT   = 'nJy'         # Image units are nanojansky
FLUXMAG0= 0.0           # Zero-point for magnitude conversion
```

---

### 2. Modify readfits.c: Read as Float for nJy

**Current:** Always returns `int** big` (DN)

**Modified:** Return float array for nJy
```c
// Option A: Create new function for nJy
float** readfits_nJy_(char* r_file, int* nx_ptr, int* ny_ptr)
{
     // Similar to readfits_ but:
     // - Returns float** instead of int**
     // - Reads as TFLOAT from cfitsio
     // - No rescaling by gain
}

// Option B: Detect units and return appropriate type
struct FitsData {
     void* image;           // void* or int** or float**
     enum ImageUnits units;
     int nx, ny;
};

struct FitsData readfits_multiunit_(char* r_file)
{
     struct FitsData data;
     data.units = detect_image_units_(r_file);
     
     if (data.units == UNIT_NJY){
          data.image = (void*)readfits_nJy_(r_file, &data.nx, &data.ny);
     } else {
          data.image = (void*)readfits_(r_file, &data.nx, &data.ny);
     }
     return data;
}
```

**Why separate function:**
- nJy values are floats (can be < 1)
- DN values are integers (counts)
- Math operations differ between units

---

### 3. Modify makenoise.c: Unit-Aware Noise Calculation

**Current:** Computes DN noise using gain

**Modified:** Handle both units

```c
// For DN: use gain-based formula
void makenoise_DN_(int** image, int** noise, int* ndx, int* ndy)
{
     float TEMP1 = (RNOISE/EPERDN)*(RNOISE/EPERDN);
     float TEMP2 = 1.0f/EPERDN;
     
     for (I = 0; I < NSLOW; I++){
          for (J = 0; J < NFAST; J++){
               noise[I][J] = image[I][J]*TEMP2 + TEMP1;
          }
     }
}

// For nJy: use variance directly (no gain conversion)
void makenoise_nJy_(float** variance, float** noise, int* ndx, int* ndy)
{
     // Variance already in nJy² from DP2 FITS
     // Just take square root
     for (I = 0; I < NSLOW; I++){
          for (J = 0; J < NFAST; J++){
               noise[I][J] = sqrtf(variance[I][J]);  // noise in nJy
          }
     }
}
```

**Why different:**
- DN: noise = sqrt(image*gain + readout_noise²) / gain
- nJy: noise = sqrt(variance) [already in nJy²]

---

### 4. Modify build.c: Branch on Unit System

**Current (DN only):**
```c
int** big = readfits_(files[0], &nx, &ny);
int** noise = malloc_int_2darr(nslow, nfast);
makenoise_(big, noise, &nfast, &nslow);
```

**Modified (unit-aware):**
```c
enum ImageUnits units = detect_image_units_(files[0]);

if (units == UNIT_NJY){
     // nJy path
     float** image_nJy = readfits_nJy_(files[0], &nx, &ny);
     float** variance = readfits_variance_(files[0], nx, ny);
     float** noise_nJy = malloc_float_2darr(nslow, nfast);
     
     if (variance != NULL){
          makenoise_nJy_(variance, noise_nJy, &nfast, &nslow);
     } else {
          // For nJy without variance, use simple estimate
          estimate_noise_nJy_(image_nJy, noise_nJy, &nfast, &nslow);
     }
     
     // Convert image/noise to void* pointers for generic processing
     big_generic = (void*)image_nJy;
     noise_generic = (void*)noise_nJy;
     
} else {
     // DN path (existing code)
     int** big = readfits_(files[0], &nx, &ny);
     int** noise = malloc_int_2darr(nslow, nfast);
     makenoise_(big, noise, &nfast, &nslow);
}
```

---

### 5. Modify Parameter Thresholds: Scale by Unit System

**Current (hardcoded DN thresholds):**
```c
search_.thresh = tune3_.tmin;      // e.g., 24.42 DN
```

**Modified (unit-aware):**
```c
if (units == UNIT_NJy){
     // Convert DN thresholds to nJy
     // Example: 24.42 DN * (nJy/DN conversion) = nJy threshold
     float dn_to_njy = get_photometric_calib_(files[0]);  // from FITS header
     search_.thresh = tune3_.tmin * dn_to_njy;
} else {
     search_.thresh = tune3_.tmin;  // DN (unchanged)
}
```

**How to get conversion factor from FITS:**
```c
float get_photometric_calib_(char* fits_file)
{
     // Rubin DP2 provides FLUXMAG0 (zero-point)
     // FLUXMAG0 = magnitude with flux = 1 Jy
     // Can derive DN→nJy conversion from photoCalib
     
     // Simplified: read from FITS header or config
     // E.g., 1 DN = 1000 nJy (depends on exposure)
     return 1000.0f;  // placeholder
}
```

---

### 6. Modify Magnitude Calculations: Unit-Aware Calibration

**Current (DN-based):**
```c
// In postprocessing: convert DN to magnitudes
mag = -2.5 * log10(flux_dn) + zeromag_dn;
```

**Modified (supports both):**
```c
if (units == UNIT_NJy){
     // Direct nJy to AB magnitude conversion
     // m_AB = -2.5 * log10(flux_nJy) - 23.9  (standard nJy zeropoint)
     mag = -2.5 * log10(flux_nJy) - 23.9;
} else {
     // DN to magnitude using stored calibration
     mag = -2.5 * log10(flux_dn) + zeromag_dn;
}
```

---

## Updated Implementation Roadmap

### Phase 1: Variance Support (3-4 hours)
- [ ] Modify readfits.c to accept hdu_num=4
- [ ] Create readfits_variance.c
- [ ] Update makenoise.c

### Phase 2: Unit Detection & Support (4-6 hours)
- [ ] Create detect_image_units.c
- [ ] Create readfits_nJy_() for float image data
- [ ] Create makenoise_nJy_() for nJy noise
- [ ] Create estimate_noise_nJy_() for nJy without variance

### Phase 3: Unit-Aware Pipeline (3-4 hours)
- [ ] Modify build.c to branch on units
- [ ] Update threshold calculations
- [ ] Update parameter file generation
- [ ] Handle generic processing (void* pointers or templating)

### Phase 4: Calibration & Magnitude (2-3 hours)
- [ ] Extract photometric calibration from FITS
- [ ] Update magnitude calculations
- [ ] Handle zero-point transformations

### Phase 5: Testing (2-3 hours)
- [ ] Test DN FITS (backward compat)
- [ ] Test nJy FITS with variance
- [ ] Test nJy FITS without variance
- [ ] Compare photometry (DN vs nJy)

**Total Effort**: ~14-20 hours

---

## Key Design Patterns

### Pattern 1: Parallel Code Paths (Simplest)
```
if (units == UNIT_DN) {
     // existing DN code
} else {
     // new nJy code
}
```
**Pro:** Clear, easy to maintain
**Con:** Code duplication

### Pattern 2: Generic Processing (Flexible)
```
void* image = malloc based on units
void* noise = malloc based on units
process_generic(image, noise, units, ...)  // single function
```
**Pro:** Minimal duplication
**Con:** Complex pointer arithmetic

### Pattern 3: Template-Like (C doesn't support)
Could use macros, but C templating is awkward.

**Recommendation:** Pattern 1 (parallel paths) - clearer and safer for C code.

---

## Unit Conversion Summary

| Aspect | DN | nanojansky |
|--------|----|----|
| **FITS BUNIT** | (missing) or 'count' | 'nJy' |
| **Image type** | int (counts) | float (flux) |
| **Typical values** | 100-60000 | 10-1000000 nJy |
| **Noise formula** | sqrt(image/gain + rdnoise²) | sqrt(variance) |
| **Variance** | Not in FITS | In VARIANCE extension (nJy²) |
| **Zero-point** | Stored in param file | -23.9 (AB magnitude standard) |
| **Calibration** | gain + readout_noise | photoCalib (from DP2 processing) |
| **Threshold scale** | e.g., 24.42 DN | e.g., 50000 nJy |

---

## Conclusion

**What's blocking us**: 
1. C code assumes single-extension FITS with computed noise ← *variance issue*
2. C code assumes DN units only ← **NEW: unit system issue**

**What needs to change**:
1. readfits.c: Accept multi-extension FITS ✅
2. readfits_variance.c: Extract VARIANCE extension ✅
3. makenoise.c: Support both variance and unit-aware noise ✅
4. detect_image_units.c: **NEW** - Determine DN vs nJy
5. readfits_nJy.c: **NEW** - Read nJy as float
6. build.c: **NEW** - Branch on units throughout pipeline

**Benefit**: 
- Use Rubin's pre-computed, error-propagated variance ✅
- Support both DN and nJy units ✅
- Seamlessly work with DP2 FITS data ✅

**Backward compatibility**: 
- Existing DN FITS works unchanged ✅
- Existing single-extension files work unchanged ✅
- New nJy DP2 FITS files work correctly ✅

**Total Effort**: ~14-20 hours (variance ~12-15h + units ~4-6h)

**Priority**: CRITICAL - Without this, DP2 nJy data cannot be processed correctly
