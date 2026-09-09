#ifndef READFITS_VARIANCE_H
#define READFITS_VARIANCE_H

// Read variance data from DP2 FITS VARIANCE extension (HDU 4)
// Returns NULL if variance not found (e.g., single-extension FITS)
// Variance data is in native units: electrons² for DN, nJy² for nanojansky
float** readfits_variance_(char* r_file, int nx, int ny);

// Free variance array
void free_variance_(float** variance, int ny);

#endif
