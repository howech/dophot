#ifndef DOPHOT_LIBRARY_H
#define DOPHOT_LIBRARY_H

/* Public library API for DoPHOT photometry
 * Accepts pre-loaded image data, returns results as structured data
 * (no file I/O, no CFITSIO dependency, no interactive prompts)
 */

#include <stdint.h>

/* Model selection */
typedef enum {
    DOPHOT_MODEL_PGAUSS    = 0,  /* Pseudo-Gaussian (default) */
    DOPHOT_MODEL_GAUSS     = 1,  /* Simple Gaussian */
    DOPHOT_MODEL_EXTPGAUSS = 2   /* Extended Pseudo-Gaussian */
} dophot_model_t;

/* Input parameters struct */
typedef struct {
    float sigma;              /* PSF sigma (pixels) */
    float fwhm;               /* PSF FWHM (computed from sigma) */
    float sky_value;          /* Sky background level (DN) */
    float gain;               /* e- per DN */
    float rdnoise;            /* Readout noise (electrons) */
    float saturation;         /* Saturation level (DN) */
    int nthpix;               /* Number of threshold pixels */
    int nfit;                 /* Number of fit parameters */
    dophot_model_t model;     /* PSF model type */
} dophot_params_t;

/* Output results struct */
typedef struct {
    int n_stars;              /* Number of stars detected */
    float* x;                 /* X positions [n_stars] */
    float* y;                 /* Y positions [n_stars] */
    float* mag;               /* Instrumental magnitudes [n_stars] */
    float* err;               /* Magnitude errors [n_stars] */
    float** starpar;          /* Full parameter matrix [NSMAX][NPMAX] */
    float** shadow;           /* PSF shadows [NSMAX][NPMAX] */
    float** shaderr;          /* PSF shadow errors [NSMAX][NPMAX] */
    int* imtype;              /* Image type per star [NSMAX] */
    int max_stars;            /* NSMAX constant (max possible stars) */
} dophot_results_t;

/* Main library entry point
 *
 * Performs star search and photometry on pre-loaded image data.
 *
 * Args:
 *   image     - int32 image array [ny][nx], pre-loaded by caller
 *   noise     - int32 noise array [ny][nx] (can be computed from image)
 *   nx        - image width (pixels)
 *   ny        - image height (pixels)
 *   params    - input parameters struct
 *   results   - output results struct (caller allocates, function populates)
 *
 * Returns:
 *   0 on success
 *   nonzero on error
 *
 * Notes:
 *   - Caller must allocate/deallocate results struct and its arrays
 *   - starpar, shadow, shaderr arrays are managed by DoPHOT globals
 *   - Function does NOT read files, write files, or prompt interactively
 */
int dophot_photometry(
    int32_t** image,
    int32_t** noise,
    int nx,
    int ny,
    const dophot_params_t* params,
    dophot_results_t* results
);

#endif
