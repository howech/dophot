/* DoPHOT library wrapper - core photometry interface
 *
 * This wrapper exposes DoPHOT photometry as a callable library function.
 * Input: pre-loaded image data (numpy arrays from Python)
 * Output: structured results (no file I/O)
 *
 * The wrapper:
 * - Initializes global state from params struct
 * - Calls isearch_() and improve_() with correct model function
 * - Extracts results into structured output
 * - Cleans up (if needed)
 * - Never touches files or CFITSIO
 */

#include "headers/dophot_library.h"
#include <string.h>

/* Forward declarations of existing DoPHOT functions */
extern int isearch_(
    double (*model_func)(short int*, float*, float*, int*, int*),
    int** image, int** noise, int* nx, int* ny
);

extern void improve_(
    double (*model_func)(short int*, float*, float*, int*, int*),
    int** image, int** noise, int* nx, int* ny
);

/* Model function pointers */
extern double pgauss2d_(short int* img, float* par, float* err, int* npar, int* nfit);
extern double gauss2d_(short int* img, float* par, float* err, int* npar, int* nfit);
extern double extpgauss2d_(short int* img, float* par, float* err, int* npar, int* nfit);

/* Global state structs (accessed via extern in various .h files) */
extern struct {
    float** starpar;
    int* IMTYPE;
    float** shadow;
    float** shaderr;
    float*** shadcovar;
} starlist_;

extern struct {
    int nstot;
    float thresh;
} search_;

extern struct {
    int NFAST;
    int NSLOW;
} undergnd_;

extern struct {
    int npar;
    int nfit2;
} tune4_;

extern struct {
    int lverb;
} tune14_;

extern struct {
    char** files;
    char** flags;
} tune16_;

extern struct {
    int nthpix;
} tune18_;

extern struct {
    int ufactor;
} unitize_;

extern struct {
    float sigma;
    float beta4;
    float beta6;
    float beta8;
} tune31_;

/* Initialize global state from params struct
 * This is a simplified initialization that sets key parameters
 * that control photometry behavior.
 */
static void init_from_params(const dophot_params_t* params) {
    /* Set PSF parameters */
    tune31_.sigma = params->sigma;
    tune31_.beta4 = 1.0f;  /* Typical Gaussian-like profile */
    tune31_.beta6 = 0.5f;
    tune31_.beta8 = 0.0f;

    /* Set threshold */
    if (params->nthpix > 0) {
        tune18_.nthpix = params->nthpix;
    } else {
        /* Default: sqrt of image size, will be set later */
        tune18_.nthpix = 0;
    }

    /* Set number of fit parameters */
    if (params->nfit > 0) {
        tune4_.nfit2 = params->nfit;
    }

    /* Unitization factor (scale to normalized units) */
    unitize_.ufactor = 100.0f;

    /* Logging off by default (can be enabled with tune14_.lverb) */
    tune14_.lverb = 0;
}

/* Select model function based on params */
static double (*select_model_2d(dophot_model_t model_id))(short int*, float*, float*, int*, int*) {
    switch (model_id) {
        case DOPHOT_MODEL_PGAUSS:
            return &pgauss2d_;
        case DOPHOT_MODEL_GAUSS:
            return &gauss2d_;
        case DOPHOT_MODEL_EXTPGAUSS:
            return &extpgauss2d_;
        default:
            return &pgauss2d_;  /* Default to PGAUSS */
    }
}

/* Main library entry point */
int dophot_photometry(
    int32_t** image,
    int32_t** noise,
    int nx,
    int ny,
    const dophot_params_t* params,
    dophot_results_t* results
) {
    if (!image || !noise || !params || !results) {
        return 1;  /* Error: NULL pointer */
    }

    if (nx <= 0 || ny <= 0) {
        return 2;  /* Error: invalid image size */
    }

    /* Initialize global state from params */
    init_from_params(params);

    /* Set image dimensions in global state */
    undergnd_.NFAST = nx;
    undergnd_.NSLOW = ny;

    /* Set threshold if not already set */
    if (tune18_.nthpix <= 0) {
        int sq = (int)(sqrtf((float)nx));
        tune18_.nthpix = (sq > 0) ? sq : 10;
    }

    /* Select model function */
    double (*model2d)(short int*, float*, float*, int*, int*) = select_model_2d(params->model);

    /* Reset star count */
    search_.nstot = 0;

    /* Perform initial star search */
    int nfast = nx;
    int nslow = ny;
    int n_stars = isearch_(model2d, (int**)image, (int**)noise, &nfast, &nslow);

    if (n_stars < 0) {
        return 3;  /* Error in isearch */
    }

    /* Iterative improvement phase */
    improve_(model2d, (int**)image, (int**)noise, &nfast, &nslow);

    /* Extract results from global starlist_ structure */
    results->n_stars = n_stars;
    results->max_stars = NSMAX;
    results->starpar = starlist_.starpar;
    results->shadow = starlist_.shadow;
    results->shaderr = starlist_.shaderr;
    results->imtype = starlist_.IMTYPE;

    /* Allocate and extract individual result arrays
     * STARPAR matrix layout (per star):
     *   starpar[i][0] = x position
     *   starpar[i][1] = y position
     *   starpar[i][2] = flux (raw)
     *   starpar[i][3] = instrumental magnitude
     *   starpar[i][4+] = additional parameters
     */

    if (n_stars > 0) {
        /* Allocate arrays for result fields */
        results->x = (float*)malloc(n_stars * sizeof(float));
        results->y = (float*)malloc(n_stars * sizeof(float));
        results->mag = (float*)malloc(n_stars * sizeof(float));
        results->err = (float*)malloc(n_stars * sizeof(float));

        if (!results->x || !results->y || !results->mag || !results->err) {
            /* Memory allocation failed */
            if (results->x) free(results->x);
            if (results->y) free(results->y);
            if (results->mag) free(results->mag);
            if (results->err) free(results->err);
            results->n_stars = 0;
            return 4;  /* Error: memory allocation failed */
        }

        /* Extract from STARPAR matrix */
        for (int i = 0; i < n_stars; i++) {
            results->x[i] = starlist_.starpar[i][0];      /* X position */
            results->y[i] = starlist_.starpar[i][1];      /* Y position */
            results->mag[i] = starlist_.starpar[i][3];    /* Instrumental magnitude */

            /* Error extraction: use shaderr diagonal or compute from covariance
             * For now, use simplified approach: sqrt of variance estimate
             * shaderr[i][j] contains error on parameter j
             */
            if (starlist_.shaderr && starlist_.shaderr[i]) {
                /* Use error on magnitude parameter (index 3) */
                results->err[i] = starlist_.shaderr[i][3];
            } else {
                /* Fallback: use generic error estimate */
                results->err[i] = 0.1f;  /* ~0.1 mag uncertainty */
            }
        }
    } else {
        /* No stars detected */
        results->x = NULL;
        results->y = NULL;
        results->mag = NULL;
        results->err = NULL;
    }

    return 0;  /* Success */
}
