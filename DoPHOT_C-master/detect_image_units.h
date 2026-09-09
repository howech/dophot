#ifndef DETECT_IMAGE_UNITS_H
#define DETECT_IMAGE_UNITS_H

enum ImageUnits {
     UNIT_DN = 0,      // Data Numbers (traditional DoPHOT)
     UNIT_NJY = 1      // nanojansky (Rubin DP2 FITS)
};

// Detect image units from FITS BUNIT keyword
enum ImageUnits detect_image_units_(char* fits_file);

// Get human-readable string for units
const char* image_units_string_(enum ImageUnits units);

// Get conversion factor from DN to nJy
float get_dn_to_njy_factor_(char* fits_file);

#endif
