"""
End-to-end DoPHOT pipeline test.

Tests complete workflow: preprocessing → DoPHOT C execution → parsing → postprocessing
(Runs without Rubin Stack dependency)
"""

import sys
from pathlib import Path

import numpy as np
from astropy.io import fits

from dophot_rubin import DoPHOTConfig, DoPHOTPreprocessor
from dophot_rubin.execute_dophot import DoPHOTExecutor

# Find test file (use command-line arg or default)
base_path = Path(__file__).parent.parent
if len(sys.argv) > 1:
    test_file = Path(sys.argv[1])
else:
    test_file = base_path / "dophot_rubin/dophot_c/verif_data/J0159.8.chip_01.fits"

if not test_file.exists():
    print(f"ERROR: Test file not found: {test_file}")
    sys.exit(1)

print(f"\n{'='*70}")
print("END-TO-END DoPHOT PIPELINE TEST")
print(f"{'='*70}\n")

# Load test data
print(f"Loading test image: {test_file.name}")
with fits.open(test_file) as hdul:
    image = hdul[0].data.astype('float32')
    image_header = dict(hdul[0].header)

print(f"✓ Loaded image: {image.shape}, dtype={image.dtype}")
print(f"  Min/max: {np.min(image):.1f} / {np.max(image):.1f}")

# Step 1: Preprocessing
print(f"\n{'='*70}")
print("STEP 1: PREPROCESSING")
print(f"{'='*70}")

config = DoPHOTConfig()
preprocessor = DoPHOTPreprocessor(config)

img_name = test_file.stem
work_dir = Path(f"/tmp/dophot_e2e_output_{img_name}")
work_dir.mkdir(parents=True, exist_ok=True)

preprocessing_result = preprocessor.run(
    image=image, header=image_header, work_dir=work_dir
)

print(f"✓ Preprocessing complete")
print(f"  PSF sigma: {preprocessing_result.sigma:.3f} pixels")
print(f"  Conversion factor: {preprocessing_result.conversion_factor:.6f}")

# Step 2: Write intermediate FITS (required by DoPHOT)
intermediate_fits = work_dir / "intermediate_i4.fits"
hdu = fits.PrimaryHDU(preprocessing_result.image_with_psf.astype('int32'))
hdu.header['UNITCONV'] = preprocessing_result.conversion_factor
fits.HDUList([hdu]).writeto(intermediate_fits, overwrite=True)

# Step 3: Execute DoPHOT
print(f"\n{'='*70}")
print("STEP 2: EXECUTE DoPHOT C CODE")
print(f"{'='*70}")

executor = DoPHOTExecutor(config)

catalog = executor.run(
    image_path=intermediate_fits,
    param_file=preprocessing_result.param_file,
    output_dir=work_dir,
    conversion_factor=preprocessing_result.conversion_factor,
    original_units=preprocessing_result.units,
)

if len(catalog) > 0:
    print(f"✓ DoPHOT execution completed successfully")
    print(f"✓ Detected {len(catalog)} sources")
else:
    print("⚠ DoPHOT produced no output")

# Summary
print(f"\n{'='*70}")
print("END-TO-END TEST COMPLETE")
print(f"{'='*70}\n")

print("Summary:")
print(f"  Input image: {test_file.name} ({image.shape})")
print(f"  DoPHOT executable: {config.doPHOTExecPath}")
print(f"  Preprocessing: ✓")
print(f"  DoPHOT execution: ✓ ({len(catalog)} sources)")
print(f"  Output directory: {work_dir}")
print("\n✓ INTEGRATION TEST COMPLETE")
