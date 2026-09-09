#ifndef MAKENOISE_NJY_H
#define MAKENOISE_NJY_H

// Compute noise for nanojansky (nJy) data from variance
void makenoise_nJy_from_variance_(
     float** variance,      // Input: variance in nJy²
     float** noise,         // Output: noise in nJy
     int* ndx, int* ndy);

// Estimate nJy noise from image (when variance not available)
void makenoise_nJy_estimate_(
     float** image,         // Input: image in nJy
     float** noise,         // Output: noise estimate in nJy
     int* ndx, int* ndy);

// Wrapper: use variance if available, estimate otherwise
void makenoise_nJy_(
     float** image,         // Input: image in nJy
     float** variance,      // Input: variance (can be NULL)
     float** noise,         // Output: noise in nJy
     int* ndx, int* ndy);

#endif
