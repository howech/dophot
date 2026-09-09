#ifndef MAKENOISE_H
#define MAKENOISE_H

// Compute noise map from image (original algorithm)
void makenoise_(int** BIG, int** NOISE, int* NFAST_ptr, int* NSLOW_ptr);

// Compute noise from pre-computed variance (DN units)
void makenoise_from_variance_(
     float** variance,      // Input: variance in electrons²
     int** noise,           // Output: noise in DN
     int* ndx, int* ndy);

#endif
