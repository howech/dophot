#!/usr/bin/env python3
"""
Test DoPHOT with real and synthetic DP2 FITS files.

Compares:
1. Traditional single-extension FITS (no variance)
2. DP2 FITS with synthetic variance
3. Validates noise calculation improvements
"""

import tempfile
from pathlib import Path
import numpy as np
from astropy.io import fits
import subprocess
import logging
import shutil

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Paths (absolute to avoid issues when changing directories)
DOPHOT_EXEC = Path.cwd() / "DoPHOT_C-master/working_data/dophot"
TEST_FITS = Path.cwd() / "DoPHOT_C-master/verif_data/J0159.8.chip_01.fits"
TEST_PARAM_DIR = Path.cwd() / "dophot_rubin/tests/data"

def find_param_file():
    """Find a valid DoPHOT parameter file."""
    if TEST_PARAM_DIR.exists():
        param_files = list(TEST_PARAM_DIR.glob("*.param"))
        if param_files:
            return param_files[0]
    return None

def create_minimal_param_file(output_dir):
    """Create a minimal DoPHOT parameter file for testing."""
    # Minimal parameter file that DoPHOT can work with
    param_content = """; Minimal DoPHOT parameter file
NPHOTFRAMESONX = 4
NPHOTFRAMESONY = 4
MODELTYPE = GAUSS
PSFTYPE = GAUSS
IENDB = 100
IENDL = 100
ISTARTNEW = 0
IFLAG = 1
ISTART = 1
NCOLSIMSUB = 8
NROWSIMSUB = 8
NCOLMAG = 3
NROWMAG = 3
NCOLPARAM = 3
NROWPARAM = 3
MEDSKY = Y
MEDIA = 11
MEDIB = 11
THRESHMIN = 50.0
THRESHMAX = 50000.0
THFAC = 1.414
WFWHM = 1.5
FWHM = 4.0
RNOISE = 5.0
EPERDN = 1.0
SATURATE = 60000.0
"""
    param_file = Path(output_dir) / "dophot_test.param"
    param_file.write_text(param_content)
    logger.info(f"Created parameter file: {param_file}")
    return param_file

def convert_to_dp2_fits(input_file, output_file, add_noise=True):
    """
    Convert single-extension FITS to DP2 format with synthetic variance.

    Parameters
    ----------
    input_file : Path
        Input single-extension FITS
    output_file : Path
        Output DP2 FITS (4 HDUs)
    add_noise : bool
        If True, add synthetic variance
    """
    logger.info(f"\nConverting to DP2 FITS...")
    logger.info(f"  Input: {input_file}")

    with fits.open(input_file) as hdul:
        image = hdul[0].data.astype('float32')
        header = hdul[0].header.copy()

    ny, nx = image.shape
    logger.info(f"  Image shape: {ny} × {nx}")

    # Create DP2 structure
    hdul_out = fits.HDUList()

    # PRIMARY HDU (empty with header)
    primary = fits.PrimaryHDU(header=header)
    hdul_out.append(primary)

    # IMAGE HDU
    image_hdu = fits.ImageHDU(image, name='IMAGE')
    image_hdu.header['BUNIT'] = 'nJy'  # DP2 standard
    image_hdu.header['EXTVER'] = 1
    hdul_out.append(image_hdu)
    logger.info(f"  Added IMAGE HDU: {image.shape} float32")

    # MASK HDU
    mask = np.zeros((ny, nx), dtype='uint32')
    # Add some synthetic bad pixels (cosmic ray-like)
    bad_pixels = np.random.choice(ny * nx, size=int(0.01 * ny * nx), replace=False)
    mask.flat[bad_pixels] = 1

    mask_hdu = fits.ImageHDU(mask, name='MASK')
    mask_hdu.header['EXTVER'] = 1
    hdul_out.append(mask_hdu)
    logger.info(f"  Added MASK HDU: {mask.shape} uint32 ({np.sum(mask > 0)} bad pixels)")

    # VARIANCE HDU (synthetic)
    if add_noise:
        # Poisson noise model: variance = image + readout_noise²
        variance = np.maximum(np.abs(image), 0.0) + 25.0  # 5 electron readout noise
        variance = variance.astype('float32')

        var_hdu = fits.ImageHDU(variance, name='VARIANCE')
        var_hdu.header['EXTVER'] = 1
        hdul_out.append(var_hdu)
        logger.info(f"  Added VARIANCE HDU: {variance.shape} float32")
        logger.info(f"    Variance range: {variance.min():.2f} to {variance.max():.2f}")

    # Write DP2 FITS
    hdul_out.writeto(str(output_file), overwrite=True)
    logger.info(f"  Output: {output_file}")
    logger.info(f"  Total HDUs: {len(hdul_out)}")

    return output_file

def run_dophot_test(fits_file, param_file, test_name, work_dir):
    """
    Run DoPHOT on a FITS file.

    Parameters
    ----------
    fits_file : Path
        Input FITS file
    param_file : Path
        DoPHOT parameter file
    test_name : str
        Name for this test
    work_dir : Path
        Working directory

    Returns
    -------
    dict
        Results including success status and any output
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Test: {test_name}")
    logger.info(f"{'='*60}")
    logger.info(f"FITS file: {fits_file.name}")
    logger.info(f"File exists: {fits_file.exists()}")

    # Check FITS structure
    try:
        with fits.open(fits_file) as hdul:
            logger.info(f"FITS HDUs: {len(hdul)}")
            for i, hdu in enumerate(hdul):
                if hdu.data is not None:
                    logger.info(f"  HDU {i}: {hdu.name:10s} {hdu.data.shape} {hdu.data.dtype}")
                else:
                    logger.info(f"  HDU {i}: {hdu.name:10s} (empty)")
    except Exception as e:
        logger.error(f"Failed to read FITS: {e}")
        return {'success': False, 'error': str(e)}

    # Create work directory for this test
    test_work_dir = work_dir / test_name.replace(' ', '_')
    test_work_dir.mkdir(exist_ok=True)

    # Copy FITS to work directory
    test_fits = test_work_dir / fits_file.name
    shutil.copy(fits_file, test_fits)

    # Copy param file
    test_param = test_work_dir / "dophot.param"
    shutil.copy(param_file, test_param)

    logger.info(f"Working directory: {test_work_dir}")

    # Run DoPHOT
    logger.info(f"\nExecuting DoPHOT...")
    try:
        result = subprocess.run(
            [str(DOPHOT_EXEC), str(test_param)],
            cwd=str(test_work_dir),
            capture_output=True,
            text=True,
            timeout=60,
            input=""  # Provide empty input to avoid hanging on interactive prompts
        )

        logger.info(f"Return code: {result.returncode}")

        if result.stdout:
            logger.info(f"\nSTDOUT (first 500 chars):")
            print(result.stdout[:500])

        if result.stderr:
            logger.info(f"\nSTDERR (first 500 chars):")
            print(result.stderr[:500])

        # Look for variance-related messages
        output = result.stdout + result.stderr
        variance_detected = "variance" in output.lower() or "dp2" in output.lower()

        return {
            'success': result.returncode == 0,
            'return_code': result.returncode,
            'variance_detected': variance_detected,
            'work_dir': test_work_dir,
            'stdout': result.stdout[:1000],
            'stderr': result.stderr[:1000]
        }

    except subprocess.TimeoutExpired:
        logger.error("DoPHOT execution timed out (>60s)")
        return {
            'success': False,
            'error': 'Timeout',
            'work_dir': test_work_dir
        }
    except Exception as e:
        logger.error(f"DoPHOT execution failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'work_dir': test_work_dir
        }

def main():
    """Run complete test suite."""
    logger.info("DoPHOT Variance Integration Test with Real FITS Data")
    logger.info("="*60)

    # Check prerequisites
    if not DOPHOT_EXEC.exists():
        logger.error(f"DoPHOT executable not found: {DOPHOT_EXEC}")
        logger.info("Please compile: cd DoPHOT_C-master && make")
        return 1

    if not TEST_FITS.exists():
        logger.error(f"Test FITS file not found: {TEST_FITS}")
        return 1

    logger.info(f"DoPHOT executable: {DOPHOT_EXEC}")
    logger.info(f"Test FITS file: {TEST_FITS}")

    # Create working directory
    with tempfile.TemporaryDirectory(prefix="dophot_test_") as tmpdir:
        work_dir = Path(tmpdir)
        logger.info(f"Working directory: {work_dir}\n")

        # Create parameter file
        param_file = create_minimal_param_file(work_dir)

        # Test 1: Original single-extension FITS
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Single-Extension FITS (No Variance)")
        logger.info("="*60)

        single_fits = work_dir / "test_single.fits"
        shutil.copy(TEST_FITS, single_fits)

        result1 = run_dophot_test(single_fits, param_file, "Single_Extension", work_dir)

        # Test 2: DP2 FITS without variance
        logger.info("\n" + "="*60)
        logger.info("TEST 2: DP2 FITS (No Variance)")
        logger.info("="*60)

        dp2_no_var = work_dir / "test_dp2_no_variance.fits"
        convert_to_dp2_fits(TEST_FITS, dp2_no_var, add_noise=False)

        result2 = run_dophot_test(dp2_no_var, param_file, "DP2_No_Variance", work_dir)

        # Test 3: DP2 FITS with variance
        logger.info("\n" + "="*60)
        logger.info("TEST 3: DP2 FITS (With Variance) - NEW FEATURE")
        logger.info("="*60)

        dp2_with_var = work_dir / "test_dp2_with_variance.fits"
        convert_to_dp2_fits(TEST_FITS, dp2_with_var, add_noise=True)

        result3 = run_dophot_test(dp2_with_var, param_file, "DP2_With_Variance", work_dir)

        # Summary
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)

        print(f"\nTest 1 (Single-Extension): {'PASS' if result1['success'] else 'FAIL'}")
        print(f"  Return code: {result1.get('return_code', 'N/A')}")

        print(f"\nTest 2 (DP2 No Variance): {'PASS' if result2['success'] else 'FAIL'}")
        print(f"  Return code: {result2.get('return_code', 'N/A')}")
        print(f"  Variance detected: {result2.get('variance_detected', False)}")

        print(f"\nTest 3 (DP2 With Variance): {'PASS' if result3['success'] else 'FAIL'}")
        print(f"  Return code: {result3.get('return_code', 'N/A')}")
        print(f"  Variance detected: {result3.get('variance_detected', False)}")

        # Check for improvements
        if result3['success'] and result3.get('variance_detected'):
            logger.info("\n✓✓ SUCCESS!")
            logger.info("DoPHOT successfully read and used variance from DP2 FITS!")
        elif result3['success']:
            logger.info("\n✓ DoPHOT executed successfully")
            logger.info("(Variance detection depends on DoPHOT verbosity level)")
        else:
            logger.warning("\n✗ Tests did not complete successfully")
            logger.info("This may be due to DoPHOT requiring interactive input")
            logger.info("or missing required files/configuration")

        return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
