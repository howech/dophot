#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include "logh.h"
#include "tuneable.h"
#include "makenoise_nJy.h"

// Compute noise for nanojansky (nJy) data from pre-computed variance
// Variance comes from DP2 FITS in nJy² units
// Output noise is in nJy (square root of variance)

void makenoise_nJy_from_variance_(
     float** variance,      // Input: variance in nJy² (or e²)
     float** noise,         // Output: noise in nJy (or e)
     int* ndx, int* ndy)
{
     int i, j, nstot = (*ndx) * (*ndy);
     float sum = 0.0f;
     float rms = 0.0f;

     for (i = 0; i < *ndy; i++){
          for (j = 0; j < *ndx; j++){
               // noise = sqrt(variance)
               if (variance[i][j] > 0.0f){
                    noise[i][j] = sqrtf(variance[i][j]);
               } else {
                    noise[i][j] = 0.0f;
               }
               sum += noise[i][j];
          }
     }

     rms = sum / nstot;
     if (tune14_.lverb > 10){
          fprintf(logfile, "makenoise_nJy: computed noise from variance\n");
          fprintf(logfile, "  Mean noise: %.2f\n", rms);
     }
}

// Compute noise for nJy data without variance (estimate from image)
// Simple model: noise = sqrt(image_value)
// This is less accurate than using actual variance

void makenoise_nJy_estimate_(
     float** image,         // Input: image in nJy
     float** noise,         // Output: noise estimate in nJy
     int* ndx, int* ndy)
{
     int i, j, nstot = (*ndx) * (*ndy);
     float sum = 0.0f;
     float rms = 0.0f;

     for (i = 0; i < *ndy; i++){
          for (j = 0; j < *ndx; j++){
               // Estimate noise as sqrt(image)
               // Conservative assumption: noise scales with flux
               if (image[i][j] > 0.0f){
                    noise[i][j] = sqrtf(image[i][j]);
               } else {
                    noise[i][j] = 1.0f;  // Floor value
               }
               sum += noise[i][j];
          }
     }

     rms = sum / nstot;
     if (tune14_.lverb > 10){
          fprintf(logfile, "makenoise_nJy: estimated noise from image\n");
          fprintf(logfile, "  Mean noise: %.2f\n", rms);
          fprintf(logfile, "  WARNING: using image-based estimate (prefer variance)\n");
     }
}

// Wrapper: compute nJy noise (use variance if available, otherwise estimate from image)
void makenoise_nJy_(
     float** image,         // Input: image in nJy
     float** variance,      // Input: variance (can be NULL)
     float** noise,         // Output: noise in nJy
     int* ndx, int* ndy)
{
     if (variance != NULL){
          // Use variance (preferred)
          makenoise_nJy_from_variance_(variance, noise, ndx, ndy);
     } else {
          // Fall back to image-based estimate
          makenoise_nJy_estimate_(image, noise, ndx, ndy);
     }
}
