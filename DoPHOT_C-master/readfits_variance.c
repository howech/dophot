#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "logh.h"
#include "tuneable.h"
#include "fitsio.h"
#include "cast_arr.h"
#include "readfits_variance.h"

// Read variance data from DP2 FITS VARIANCE extension (HDU 4)
// Returns NULL if no variance extension found (caller should handle gracefully)
// Variance data is returned as float** array in native units (e² or nJy²)

float** readfits_variance_(char* r_file, int nx, int ny)
{
     int lverb = tune14_.lverb;
     fitsfile* fptr;
     int fio_err = 0;
     int hdu_num;
     short int var_nx, var_ny;
     char comment[FLEN_COMMENT];

     float* var1d;
     float** var2d;
     long npixels = (long)ny * nx;
     long fpixel[2] = {1, 1};
     float nullval = 0.0f;
     int anynull;

     // Open file
     if (lverb > 10){
          fprintf(logfile, "readfits_variance: opening %s for read\n", r_file);
     }
     fits_open_file(&fptr, r_file, 0, &fio_err);
     if (fio_err != 0){
          if (lverb > 10){
               fprintf(logfile, "readfits_variance: error opening file\n");
          }
          return NULL;
     }

     // Check number of HDUs
     fits_get_num_hdus(fptr, &hdu_num, &fio_err);

     // DP2 FITS has 4 HDUs, variance is at HDU 4
     if (hdu_num < 4){
          if (lverb > 10){
               fprintf(logfile, "readfits_variance: file has %d HDUs (need 4 for VARIANCE)\n", hdu_num);
          }
          fits_close_file(fptr, &fio_err);
          return NULL;  // No variance extension
     }

     // Move to VARIANCE extension (HDU 4)
     fits_movabs_hdu(fptr, 4, NULL, &fio_err);
     if (fio_err != 0){
          if (lverb > 10){
               fprintf(logfile, "readfits_variance: error moving to HDU 4\n");
          }
          fits_close_file(fptr, &fio_err);
          return NULL;
     }

     // Verify this is an image extension
     int hdu_type;
     fits_get_hdu_type(fptr, &hdu_type, &fio_err);
     if (hdu_type != 1){  // 1 = IMAGE extension
          if (lverb > 10){
               fprintf(logfile, "readfits_variance: HDU 4 is not an IMAGE extension\n");
          }
          fits_close_file(fptr, &fio_err);
          return NULL;
     }

     // Read dimensions
     fits_read_key(fptr, TSHORT, "NAXIS1", &var_nx, comment, &fio_err);
     fits_read_key(fptr, TSHORT, "NAXIS2", &var_ny, comment, &fio_err);

     if ((var_nx != nx) || (var_ny != ny)){
          printf("readfits_variance: dimension mismatch\n");
          printf("  Image: %d x %d, Variance: %d x %d\n", nx, ny, var_nx, var_ny);
          fits_close_file(fptr, &fio_err);
          return NULL;
     }

     // Allocate variance array
     var1d = malloc_float_1darr(npixels);
     var2d = malloc_float_2darr(ny, nx);

     // Read variance as float
     fits_read_pix(fptr, TFLOAT, fpixel, npixels, &nullval,
          var1d, &anynull, &fio_err);

     if (fio_err != 0){
          printf("readfits_variance: fitsio error reading variance: %d\n", fio_err);
          fits_close_file(fptr, &fio_err);
          free(var1d);
          return NULL;
     }

     // Recast to 2D
     recast_float_1dto2darr(ny, nx, var1d, var2d);
     free(var1d);

     fits_close_file(fptr, &fio_err);

     if (lverb > 10){
          fprintf(logfile, "readfits_variance: successfully read %d x %d variance array\n", nx, ny);
     }

     return var2d;
}

// Free variance array
void free_variance_(float** variance, int ny)
{
     if (variance != NULL){
          free(variance[0]);  // Free data
          free(variance);     // Free pointers
     }
}
