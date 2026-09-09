#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "fitsio.h"
#include "detect_image_units.h"

// Detect whether a FITS image is in DN (Data Numbers) or nJy (nanojansky)
// by reading the BUNIT keyword from the IMAGE extension (HDU 2 in DP2)
// or PRIMARY extension (HDU 1 in single-extension files)

enum ImageUnits detect_image_units_(char* fits_file)
{
     fitsfile* fptr;
     char unit_str[FLEN_VALUE];
     int fio_err = 0;
     int hdu_num;

     // Open file
     fits_open_file(&fptr, fits_file, 0, &fio_err);
     if (fio_err != 0){
          printf("detect_image_units: error opening FITS file\n");
          return UNIT_DN;  // Default to DN on error
     }

     // Get total number of HDUs
     fits_get_num_hdus(fptr, &hdu_num, &fio_err);

     // For DP2 FITS (4 HDUs): IMAGE is at HDU 2
     // For single-extension FITS (1 HDU): image is at HDU 1
     if (hdu_num >= 4){
          // DP2 format: try to move to IMAGE extension (HDU 2)
          fits_movabs_hdu(fptr, 2, NULL, &fio_err);
          if (fio_err != 0){
               printf("detect_image_units: error moving to IMAGE extension\n");
               fits_close_file(fptr, &fio_err);
               return UNIT_DN;
          }
     }
     // else: stay at PRIMARY (HDU 1)

     // Try to read BUNIT keyword
     fits_read_key(fptr, TSTRING, "BUNIT", unit_str, NULL, &fio_err);

     fits_close_file(fptr, &fio_err);

     // Determine units from BUNIT value
     if (fio_err == 0){  // Successfully read BUNIT
          // Check for nJy variants
          if (strncmp(unit_str, "nJy", 3) == 0){
               return UNIT_NJY;
          }
          if (strncmp(unit_str, "nanojansky", 10) == 0){
               return UNIT_NJY;
          }
          // Check for DN variants
          if (strncmp(unit_str, "DN", 2) == 0 ||
              strncmp(unit_str, "count", 5) == 0 ||
              strncmp(unit_str, "adu", 3) == 0){
               return UNIT_DN;
          }
     }

     // Default: assume DN if BUNIT not found or unrecognized
     return UNIT_DN;
}

// Get a human-readable string for the image units
const char* image_units_string_(enum ImageUnits units)
{
     if (units == UNIT_NJY){
          return "nanojansky";
     }
     return "DN (Data Numbers)";
}

// Get conversion factor from DN to nJy (if applicable)
// For DN images, this returns 1.0 (no conversion needed)
// For nJy images, this should be extracted from FITS header
// This is a placeholder - actual value depends on photometric calibration
float get_dn_to_njy_factor_(char* fits_file)
{
     fitsfile* fptr;
     float flux_dn_to_njy = 1.0f;  // Default (DN images)
     int fio_err = 0;
     float fluxmag0 = 0.0f;
     int hdu_num;

     enum ImageUnits units = detect_image_units_(fits_file);
     if (units == UNIT_DN){
          return 1.0f;  // No conversion for DN
     }

     // For nJy FITS, try to read photometric zero-point
     // Rubin DP2 provides FLUXMAG0 (magnitude with flux = 1 Jy = 1e9 nJy)
     fits_open_file(&fptr, fits_file, 0, &fio_err);
     if (fio_err != 0) return 1.0f;

     fits_get_num_hdus(fptr, &hdu_num, &fio_err);
     if (hdu_num >= 4){
          fits_movabs_hdu(fptr, 2, NULL, &fio_err);
     }

     // Read FLUXMAG0 if available (Rubin convention)
     fits_read_key(fptr, TFLOAT, "FLUXMAG0", &fluxmag0, NULL, &fio_err);
     if (fio_err == 0 && fluxmag0 != 0.0f){
          // FLUXMAG0 = magnitude with flux 1 Jy
          // Can compute DN->nJy if we have reference flux
          // For now, assume it's already in nJy
          flux_dn_to_njy = 1.0f;
     }

     fits_close_file(fptr, &fio_err);

     return flux_dn_to_njy;
}
