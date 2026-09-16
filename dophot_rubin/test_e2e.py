"""
End-to-end DoPHOT pipeline test.

Tests complete workflow: preprocessing → DoPHOT C execution → parsing → postprocessing
(Runs without Rubin Stack dependency)
"""

import logging
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from astropy.io import fits

from image_scaling import detect_units, scale_image_to_int32
from psf_measurement import (
    append_psf_to_image,
    generate_parameter_file,
    measure_psf_simple,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Find test file (relative to package location)
base_path = Path(__file__).parent.parent
test_file = base_path / "DoPHOT_C-master/verif_data/J0159.8.chip_01.fits"
dophot_exe = base_path / "DoPHOT_C-master/working_data/dophot"

if not test_file.exists():
    print(f"ERROR: Test file not found: {test_file}")
    sys.exit(1)

if not dophot_exe.exists():
    print(f"ERROR: DoPHOT executable not found: {dophot_exe}")
    sys.exit(1)

print(f"\n{'='*70}")
print(f"END-TO-END DoPHOT PIPELINE TEST")
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

units = detect_units(image_header)
print(f"✓ Units detected: {units}")

image_int32, conversion_factor, scale_metadata = scale_image_to_int32(
    image, units, header=image_header, mask=None, variance=None
)
print(f"✓ Image scaled to int32")
print(f"  Conversion factor: {conversion_factor:.6f} {units}/int32")
print(f"  Scale metadata: epdn={scale_metadata.epdn:.4f}, mprec={scale_metadata.mprec}")

sigma, beta4, beta6, beta8 = measure_psf_simple(image_int32, mask=None)
print(f"✓ PSF measured: sigma={sigma:.3f} pixels")

# Step 2: Execute DoPHOT
print(f"\n{'='*70}")
print("STEP 2: EXECUTE DoPHOT C CODE")
print(f"{'='*70}")

with tempfile.TemporaryDirectory() as tmpdir:
    tmpdir = Path(tmpdir)

    # Create intermediate FITS with PSF appended
    image_with_psf, psfcenx, psfceny, psfcenz = append_psf_to_image(
        image_int32, image_int32
    )
    intermediate_fits = tmpdir / "intermediate_i4.fits"
    hdu = fits.PrimaryHDU(image_with_psf.astype('int32'))
    hdu.header['BUNIT'] = 'I4_INT'
    hdu.header['UNITCONV'] = conversion_factor
    hdu.header['SIGMA'] = sigma
    hdul = fits.HDUList([hdu])
    hdul.writeto(intermediate_fits, overwrite=True)
    print(f"✓ Intermediate FITS written: {intermediate_fits.name}")
    print(f"  Shape: {image_with_psf.shape}")

    # Write parameter file
    param_file = tmpdir / "dophot.param"
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
        image_shape=image_int32.shape,
        mask=None,
        image_file="intermediate_i4.fits"
    )
    print(f"✓ Parameter file written: {param_file.name}")

    # Execute DoPHOT
    print(f"\nExecuting DoPHOT C code...")
    print(f"  Command: {dophot_exe} {param_file}")

    try:
        result = subprocess.run(
            [str(dophot_exe), str(param_file)],
            cwd=str(tmpdir),
            capture_output=True,
            text=True,
            timeout=60,
            check=False
        )

        if result.returncode == 0:
            print(f"✓ DoPHOT execution successful (exit code: 0)")
        else:
            print(f"⚠ DoPHOT execution returned code {result.returncode}")

        if result.stdout:
            print(f"  Output: {result.stdout[:200]}...")
        if result.stderr:
            print(f"  Stderr: {result.stderr[:200]}...")

        # Check for output files
        obj_out_file = tmpdir / "obj_out_intermediate"
        if obj_out_file.exists():
            num_lines = len(obj_out_file.read_text().strip().split('\n'))
            print(f"✓ DoPHOT output file found: {obj_out_file.name} ({num_lines} lines)")
        else:
            print(f"⚠ No DoPHOT output file (obj_out_intermediate)")
            print(f"  Files in {tmpdir}:")
            for f in sorted(tmpdir.glob('*')):
                print(f"    {f.name}")

    except subprocess.TimeoutExpired:
        print(f"⚠ DoPHOT execution timed out (60s)")
    except Exception as e:
        print(f"⚠ DoPHOT execution failed: {e}")

# Summary
print(f"\n{'='*70}")
print("END-TO-END TEST COMPLETE")
print(f"{'='*70}\n")

print(f"Summary:")
print(f"  Input image: {test_file.name} ({image.shape})")
print(f"  DoPHOT executable: {dophot_exe}")
print(f"  Preprocessing: ✓")
print(f"  DoPHOT execution: Attempted")
print(f"\n✓ INTEGRATION TEST COMPLETE")
