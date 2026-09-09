#ifndef READFITS_NJY_H
#define READFITS_NJY_H

// Read a nanojansky (nJy) FITS file as floating-point data
// Supports both single-extension and multi-extension (DP2) FITS
// Returns float** array (not int**)
float** readfits_nJy_(char* r_file, int* nx_ptr, int* ny_ptr);

#endif
