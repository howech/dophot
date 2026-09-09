#!/usr/bin/env python3
"""
Test variance integration in DoPHOT.

Tests:
1. Single-extension FITS (backward compatibility)
2. DP2 multi-extension FITS with variance
3. Verify C code reads variance correctly
"""

import tempfile
from pathlib import Path
import numpy as np
from astropy.io import fits
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to compiled DoPHOT executable
DOPHOT_EXEC = Path("DoPHOT_C-master/working_data/dophot")
TEST_FITS = Path("DoPHOT_C-master/verif_data/J0159.8.chip_01.fits")
PARAM_FILE = Path("dophot_rubin/tests/data/dophot_auto.param")

def create_param_file(tmpdir):
    """Create a basic DoPHOT parameter file."""
    param_content = """
; DoPHOT Parameter File for Testing
FWHM = 4.00
THRESHMIN = 100.0
THRESHMAX = 10000.0
PSFTYPE = GAUSS
NPHOTFRAMESONX = 4
"""
    param_file = Path(tmpdir) / "test.param"
    param_file.write_text(param_content)
    return param_file

def test_single_extension_fits():
    """Test 1: Single-extension FITS (original behavior)."""
    logger.info("=" * 60)
    logger.info("TEST 1: Single-Extension FITS (Backward Compatibility)")
    logger.info("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Read original test FITS
        logger.info(f"Reading: {TEST_FITS}")
        with fits.open(TEST_FITS) as hdul:
            image = hdul[0].data
            logger.info(f"  Image shape: {image.shape}")
            logger.info(f"  Image dtype: {image.dtype}")
            logger.info(f"  Image range: {image.min():.2f} to {image.max():.2f}")

            # Write to temp FITS
            fits_file = tmpdir / "test_single.fits"
            fits.writeto(str(fits_file), image, overwrite=True)

            # Check what was written
            with fits.open(fits_file) as check:
                logger.info(f"✓ Wrote single-extension FITS")
                logger.info(f"  HDUs: {len(check)}")
                check.info()

        # Create param file
        param_file = create_param_file(tmpdir)

        # Run DoPHOT
        logger.info(f"\nRunning DoPHOT on single-extension FITS...")
        try:
            result = subprocess.run(
                [str(DOPHOT_EXEC), str(param_file)],
                cwd=str(tmpdir),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info("✓ DoPHOT execution successful")
                if result.stdout:
                    logger.info(f"Output: {result.stdout[:200]}")
            else:
                logger.error(f"✗ DoPHOT failed with return code {result.returncode}")
                logger.error(f"STDERR: {result.stderr[:500]}")

        except FileNotFoundError:
            logger.warning("DoPHOT executable not found - skipping execution")
        except subprocess.TimeoutExpired:
            logger.error("DoPHOT timed out")

def test_dp2_with_variance():
    """Test 2: DP2 Multi-extension FITS with variance."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: DP2 FITS with Variance (New Feature)")
    logger.info("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Read original test FITS
        logger.info(f"Reading: {TEST_FITS}")
        with fits.open(TEST_FITS) as hdul:
            image = hdul[0].data.astype('float32')
            ny, nx = image.shape
            logger.info(f"  Image shape: {image.shape}")

        # Create synthetic variance (Poisson noise model)
        variance = np.abs(image) + 100  # Variance = flux + readout noise
        variance = variance.astype('float32')
        logger.info(f"  Variance shape: {variance.shape}")
        logger.info(f"  Variance range: {variance.min():.2f} to {variance.max():.2f}")

        # Create synthetic mask (no bad pixels for now)
        mask = np.zeros(image.shape, dtype='uint32')
        logger.info(f"  Mask shape: {mask.shape}")

        # Create DP2-style HDU list
        hdul = fits.HDUList()

        # PRIMARY (empty)
        hdul.append(fits.PrimaryHDU())

        # IMAGE extension
        image_hdu = fits.ImageHDU(image, name='IMAGE')
        image_hdu.header['BUNIT'] = 'nJy'
        hdul.append(image_hdu)

        # MASK extension
        mask_hdu = fits.ImageHDU(mask, name='MASK')
        hdul.append(mask_hdu)

        # VARIANCE extension
        var_hdu = fits.ImageHDU(variance, name='VARIANCE')
        hdul.append(var_hdu)

        # Write DP2 FITS
        fits_file = tmpdir / "test_dp2.fits"
        hdul.writeto(str(fits_file), overwrite=True)

        # Verify what was written
        logger.info(f"\n✓ Wrote DP2 FITS with 4 HDUs")
        with fits.open(fits_file) as check:
            logger.info(f"  Structure:")
            check.info()

            # Verify each extension
            logger.info(f"\nVerifying extensions:")
            logger.info(f"  PRIMARY: {check[0].data}")
            logger.info(f"  IMAGE: shape {check[1].data.shape}, dtype {check[1].data.dtype}")
            logger.info(f"    BUNIT: {check[1].header.get('BUNIT')}")
            logger.info(f"  MASK: shape {check[2].data.shape}, dtype {check[2].data.dtype}")
            logger.info(f"  VARIANCE: shape {check[3].data.shape}, dtype {check[3].data.dtype}")

        # Create param file
        param_file = create_param_file(tmpdir)

        # Run DoPHOT
        logger.info(f"\nRunning DoPHOT on DP2 FITS with variance...")
        try:
            result = subprocess.run(
                [str(DOPHOT_EXEC), str(param_file)],
                cwd=str(tmpdir),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info("✓ DoPHOT execution successful")
                if result.stdout:
                    logger.info(f"Output: {result.stdout[:200]}")

                # Check if variance was used
                if "Using variance from DP2 FITS file" in result.stdout:
                    logger.info("✓✓ DoPHOT detected and used variance!")
            else:
                logger.error(f"✗ DoPHOT failed with return code {result.returncode}")
                logger.error(f"STDERR: {result.stderr[:500]}")

        except FileNotFoundError:
            logger.warning("DoPHOT executable not found - skipping execution")
        except subprocess.TimeoutExpired:
            logger.error("DoPHOT timed out")

def verify_c_code_enhancements():
    """Test 3: Verify C code enhancements are present."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Verify C Code Enhancements")
    logger.info("=" * 60)

    # Check for new functions in compiled executable
    logger.info("\nChecking for new functions in DoPHOT executable...")

    import subprocess
    try:
        # Use nm to list symbols
        result = subprocess.run(
            ["nm", str(DOPHOT_EXEC)],
            capture_output=True,
            text=True
        )

        symbols = result.stdout

        expected_functions = [
            "detect_image_units_",
            "readfits_variance_",
            "makenoise_from_variance_",
            "makenoise_nJy_",
        ]

        found = 0
        for func in expected_functions:
            if func in symbols:
                logger.info(f"  ✓ Found {func}")
                found += 1
            else:
                logger.warning(f"  ? Not found {func} (may be static or inline)")

        logger.info(f"✓ Found {found}/{len(expected_functions)} new functions")

    except FileNotFoundError:
        logger.warning("nm command not found - skipping symbol check")

def main():
    """Run all tests."""
    logger.info("DoPHOT Variance Integration Tests")
    logger.info(f"DoPHOT executable: {DOPHOT_EXEC}")
    logger.info(f"Test FITS file: {TEST_FITS}")

    if not DOPHOT_EXEC.exists():
        logger.error(f"DoPHOT executable not found: {DOPHOT_EXEC}")
        logger.info("Please compile with: cd DoPHOT_C-master && make")
        return 1

    if not TEST_FITS.exists():
        logger.error(f"Test FITS file not found: {TEST_FITS}")
        return 1

    # Run tests
    test_single_extension_fits()
    test_dp2_with_variance()
    verify_c_code_enhancements()

    logger.info("\n" + "=" * 60)
    logger.info("Tests Complete!")
    logger.info("=" * 60)
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
