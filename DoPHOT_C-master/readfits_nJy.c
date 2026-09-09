#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "logh.h"
#include "tuneable.h"
#include "fitsio.h"
#include "cast_arr.h"
#include "readfits_nJy.h"

// Read a nanojansky (nJy) FITS file as floating-point data
// Similar to readfits_ but:
// - Returns float** instead of int**
// - Handles multi-extension DP2 FITS format
// - No rescaling by gain (data is already flux-calibrated)

float** readfits_nJy_(char* r_file, int* nx_ptr, int* ny_ptr)
{
     int lverb = tune14_.lverb;
     fitsfile* fptr;
     int fio_err = 0;
     int file_ver = 0;
     int hdu_num, hdu_type, img_type;
     short int naxis;
     short int nx = 0, ny = 0;
     char NAXIS_comment[FLEN_COMMENT];
     char NAXIS1_comment[FLEN_COMMENT];
     char NAXIS2_comment[FLEN_COMMENT];

     float* arr1d;
     float** arr2d;
     long npixels, fpixel[2] = {1, 1};
     float nullval = 0.0f;
     int anynull;

     // Open file
     if (lverb > 10){
          fprintf(logfile, "readfits_nJy: opening %s for read\n", r_file);
     }
     fits_open_file(&fptr, r_file, 0, &fio_err);
     if (fio_err != 0){
          printf("readfits_nJy: fitsio error in open_file: %d\n", fio_err);
          fits_close_file(fptr, &fio_err);
          return NULL;
     }

     // Get file info to verify file type
     fits_get_num_hdus(fptr, &hdu_num, &fio_err);
     file_ver += fio_err;
     fits_get_hdu_type(fptr, &hdu_type, &fio_err);
     file_ver += fio_err;
     fits_read_key(fptr, TSHORT, "NAXIS", &naxis, NAXIS_comment, &fio_err);
     file_ver += fio_err;

     if (file_ver != 0){
          printf("readfits_nJy: file verification error: %d\n", file_ver);
          fits_close_file(fptr, &fio_err);
          return NULL;
     }

     // For DP2 FITS: move to IMAGE extension (HDU 2)
     if (hdu_num >= 4){
          fits_movabs_hdu(fptr, 2, NULL, &fio_err);
          if (fio_err != 0){
               printf("readfits_nJy: error moving to IMAGE extension\n");
               fits_close_file(fptr, &fio_err);
               return NULL;
          }
          // Re-read HDU type after moving
          fits_get_hdu_type(fptr, &hdu_type, &fio_err);
     }

     // Verify this HDU has 2D image data
     if ((hdu_type != 0) || (naxis != 2)){
          printf("readfits_nJy: HDU is not a 2D image\n");
          printf("  HDU type: %d (expect 0 for PRIMARY/IMAGE)\n", hdu_type);
          printf("  NAXIS: %d (expect 2)\n", naxis);
          fits_close_file(fptr, &fio_err);
          return NULL;
     }

     if (lverb > 10){
          fprintf(logfile, "     num HDUs = %d\n", hdu_num);
          fprintf(logfile, "     HDU type = %d\n", hdu_type);
          fprintf(logfile, "     NAXIS    = %d\n", naxis);
     }

     // Get image dimensions
     fits_get_img_type(fptr, &img_type, &fio_err);
     fits_read_key(fptr, TSHORT, "NAXIS1", &nx, NAXIS1_comment, &fio_err);
     fits_read_key(fptr, TSHORT, "NAXIS2", &ny, NAXIS2_comment, &fio_err);

     if ((nx == 0) || (ny == 0)){
          printf("readfits_nJy: no NAXIS1 or NAXIS2 keywords found\n");
          fits_close_file(fptr, &fio_err);
          return NULL;
     }

     if (lverb > 10){
          fprintf(logfile, "     NAXIS1 (nx)  = %d\n", nx);
          fprintf(logfile, "     NAXIS2 (ny)  = %d\n", ny);
          fprintf(logfile, "     data_type    = %d\n", img_type);
     }

     // Allocate arrays for float data
     npixels = ny * nx;
     arr1d = malloc_float_1darr(npixels);
     arr2d = malloc_float_2darr(ny, nx);

     // Read image as TFLOAT (nJy data is typically 32-bit float)
     fits_read_pix(fptr, TFLOAT, fpixel, npixels, &nullval,
          arr1d, &anynull, &fio_err);

     if (fio_err != 0){
          printf("readfits_nJy: fitsio error in read_img: %d\n", fio_err);
          fits_close_file(fptr, &fio_err);
          free(arr1d);
          return NULL;
     }

     // Recast 1D array to 2D
     recast_float_1dto2darr(ny, nx, arr1d, arr2d);
     free(arr1d);

     fits_close_file(fptr, &fio_err);
     if (fio_err != 0){
          printf("readfits_nJy: fitsio error in close_file: %d\n", fio_err);
     }

     *nx_ptr = nx;
     *ny_ptr = ny;

     if (lverb > 10){
          fprintf(logfile, "readfits_nJy: successfully read %d x %d float image\n", nx, ny);
     }

     return arr2d;
}
