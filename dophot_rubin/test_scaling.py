"""
Test script for DoPHOT image scaling workflow.

Tests the complete preprocessing pipeline on 47Tuc FITS file.
"""

import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from image_scaling import apply_mask_to_scaled_image, detect_units, scale_image_to_int32
from psf_measurement import (
    append_psf_to_image,
    generate_parameter_file,
    measure_psf_simple,
)

# Find test file (relative to package location)
base_path = Path(__file__).parent.parent
test_file = base_path / "DoPHOT_C-master/verif_data/J0159.8.chip_01.fits"
if not test_file.exists():
    print(f"ERROR: Test file not found: {test_file}")
    sys.exit(1)

fits_file = test_file
print(f"\n{'='*70}")
print(f"Testing DoPHOT preprocessing on: {fits_file}")
print(f"{'='*70}\n")

# Load FITS file
with fits.open(fits_file) as hdul:
    header = hdul[0].header

    # Try to get IMAGE extension (DP2 format)
    if 'IMAGE' in hdul:
        image = hdul['IMAGE'].data.astype('float32')
        image_header = hdul['IMAGE'].header
    else:
        image = hdul[0].data.astype('float32')
        image_header = header

    # Get mask if available
    if 'MASK' in hdul:
        mask = hdul['MASK'].data.astype('uint32')
        n_flagged = np.sum(mask > 0)
        print(f"✓ MASK extension found: {mask.shape}, {n_flagged} flagged pixels")
    else:
        mask = None
        print("⚠ No MASK extension")

    # Get variance if available
    if 'VARIANCE' in hdul:
        variance = hdul['VARIANCE'].data.astype('float32')
        print(f"✓ VARIANCE extension found: {variance.shape}")
    else:
        variance = None
        print("⚠ No VARIANCE extension")

    print(f"✓ IMAGE extension: {image.shape}, dtype={image.dtype}")
    print(f"  Min/max: {np.min(image[image>0]):.1f} / {np.max(image):.1f}")

print("\n" + "="*70)
print("STEP 1: Detect Units")
print("="*70)

units = detect_units(image_header)
print(f"✓ Detected units: {units}")

print("\n" + "="*70)
print("STEP 2: Scale to int32")
print("="*70)

image_int32, conversion_factor, scale_metadata = scale_image_to_int32(
    image, units, header=image_header, mask=mask, variance=variance
)

print("✓ Image scaled to int32")
print(f"  Shape: {image_int32.shape}, dtype: {image_int32.dtype}")
img_min = np.min(image_int32[image_int32 > -30000])
img_max = np.max(image_int32)
print(f"  Min/max: {img_min:.1f} / {img_max:.1f}")
print("\nScale metadata:")
for key, val in scale_metadata._asdict().items():
    if isinstance(val, float):
        print(f"  {key}: {val:.4f}")
    else:
        print(f"  {key}: {val}")

print(f"\nConversion factor: {conversion_factor:.6f} {units}/int32")

print("\n" + "="*70)
print("STEP 3: Apply Mask")
print("="*70)

if mask is not None:
    image_int32_masked = apply_mask_to_scaled_image(image_int32, mask)
    sentinel_count = np.sum(image_int32_masked <= -30000)
    print("✓ Mask applied to scaled image")
    print(f"  Sentinel pixels: {sentinel_count}")
else:
    image_int32_masked = image_int32
    print("✓ No mask to apply")

print("\n" + "="*70)
print("STEP 4: Measure PSF")
print("="*70)

sigma, beta4, beta6, beta8 = measure_psf_simple(image_int32_masked, mask=mask)
print("✓ PSF measured:")
print(f"  sigma: {sigma:.2f} pixels")
print(f"  beta4: {beta4:.2f}, beta6: {beta6:.2f}, beta8: {beta8:.2f}")

print("\n" + "="*70)
print("STEP 5: Generate Parameter File")
print("="*70)

param_file = Path("/tmp/dophot_test_params.txt")
saturation = float(image_header.get('SATURATE', 65535))
params = generate_parameter_file(
    str(param_file),
    sigma=sigma,
    beta4=beta4,
    beta6=beta6,
    beta8=beta8,
    skyval=scale_metadata.skyval,
    epdn=scale_metadata.epdn,
    fpdn=1.0 / scale_metadata.gain,
    gain=scale_metadata.gain,
    saturation=saturation,
    mprec=scale_metadata.mprec,
    image_shape=image_int32_masked.shape,
    mask=mask
)
print(f"✓ Parameter file written to: {param_file}")

print("\n" + "="*70)
print("STEP 6: Append PSF to Image")
print("="*70)

image_with_psf, psfcenx, psfceny, psfcenz = append_psf_to_image(
    image_int32_masked, image_int32_masked
)
print("✓ PSF appended to image")
print(f"  Original shape: {image_int32_masked.shape}")
print(f"  New shape: {image_with_psf.shape}")
print(f"  PSF center: ({psfcenx:.1f}, {psfceny:.1f}), value: {psfcenz}")

print("\n" + "="*70)
print("STEP 7: Write Intermediate FITS")
print("="*70)

intermediate_fits = Path("/tmp/intermediate_i4.fits")
hdul = fits.HDUList()
hdul.append(fits.PrimaryHDU())

image_hdu = fits.ImageHDU(image_with_psf, name='IMAGE')
image_hdu.header['BUNIT'] = 'I4_INT'
image_hdu.header['UNITCONV'] = conversion_factor
image_hdu.header['ORIGUNIT'] = units
image_hdu.header['SIGMA'] = sigma
image_hdu.header['BETA4'] = beta4
image_hdu.header['BETA6'] = beta6
image_hdu.header['BETA8'] = beta8
image_hdu.header['PSFCENX'] = psfcenx
image_hdu.header['PSFCENY'] = psfceny
image_hdu.header['PSFCENZ'] = psfcenz
image_hdu.header['EPDN'] = scale_metadata.epdn
image_hdu.header['MPREC'] = scale_metadata.mprec
image_hdu.header['SATVAL'] = saturation
hdul.append(image_hdu)

if mask is not None:
    mask_hdu = fits.ImageHDU(mask.astype('uint32'), name='MASK')
    hdul.append(mask_hdu)

hdul.writeto(str(intermediate_fits), overwrite=True)
print(f"✓ Intermediate I*4 FITS written: {intermediate_fits}")

print("\n" + "="*70)
print("PREPROCESSING COMPLETE")
print("="*70)
print("\nSummary:")
print(f"  Input: {fits_file.name}")
print(f"  Units: {units}")
print(f"  Scale factor (epdn): {scale_metadata.epdn:.4f} {units}/int32")
print(f"  Median precision (mprec): {scale_metadata.mprec}")
print(f"  PSF sigma: {sigma:.2f} pixels")
print(f"  Output FITS: {intermediate_fits}")
print(f"  Parameter file: {param_file}")
print("\n✓ Pipeline ready for DoPHOT execution\n")
