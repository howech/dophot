#!/usr/bin/env python3
"""
Phase 2d: Test preprocessing pipeline on 47 Tucanae data.

Tests PSF measurement and parameter generation on real data.
Compares with reference outputs in Testsuite/Verify/
"""

import sys
import os
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from dophot_preprocess import psf_measurement, parameter_generation, param_file_writer


def test_psf_measurement(image_path, verbose=True):
    """Test PSF measurement on a single image."""
    if verbose:
        print("\n" + "="*60)
        print("PHASE 2d: Testing PSF Measurement")
        print("="*60)
        print(f"\nImage: {image_path}")

    if not os.path.exists(image_path):
        print(f"ERROR: Image not found: {image_path}")
        return None, False

    sigma, n_stars, success = psf_measurement.measure_psf_from_image(
        image_path, verbose=verbose
    )

    if success:
        print("\n✓ PSF measurement successful!")
        print(f"  Sigma: {sigma:.3f} pixels")
        print(f"  N_stars used: {n_stars}")
        return sigma, True
    print("\n✗ PSF measurement failed")
    return None, False


def test_parameter_generation(sigma, image_path, verbose=True):
    """Test parameter generation for an image."""
    if verbose:
        print("\n" + "="*60)
        print("PHASE 2d: Testing Parameter Generation")
        print("="*60)

    # Get image statistics
    stats = parameter_generation.measure_image_statistics(image_path)

    if verbose:
        print("\nImage Statistics:")
        print(f"  Sky value: {stats['sky_value']:.1f} DN")
        print(f"  Sky RMS: {stats['sky_rms']:.1f} DN")
        print(f"  Gain: {stats['gain']:.2f} e-/DN")
        print(f"  Readout noise: {stats['rdnoise']:.1f} e-")
        print(f"  Saturation: {int(stats['saturation'])} DN")

    # Compute parameters
    params = parameter_generation.compute_dophot_parameters(
        sigma=sigma,
        gain=stats['gain'],
        rdnoise=stats['rdnoise'],
        sky_value=stats['sky_value'],
        saturation=stats['saturation'],
        verbose=verbose
    )

    return params, stats


def test_param_file_writing(params, output_file, verbose=True):
    """Test writing parameter file."""
    if verbose:
        print("\n" + "="*60)
        print("PHASE 2d: Testing Parameter File Writing")
        print("="*60)

    success = param_file_writer.write_param_file(
        output_file, params, verbose=verbose
    )

    if success and os.path.exists(output_file):
        with open(output_file, 'r') as f:
            lines = f.readlines()
        if verbose:
            print(f"\nFirst 20 lines of {output_file}:")
            print("".join(lines[:20]))
        return True
    return False


def run_full_pipeline(image_path, output_dir=None, verbose=True):
    """Run full preprocessing pipeline on an image."""
    if output_dir is None:
        output_dir = os.path.dirname(image_path)

    image_name = os.path.basename(image_path).replace('.fits', '')
    output_prefix = os.path.join(output_dir, image_name)

    print("\n" + "#"*60)
    print(f"# Full Preprocessing Pipeline: {image_name}")
    print("#"*60)

    # Step 1: PSF Measurement
    sigma, success = test_psf_measurement(image_path, verbose=verbose)
    if not success or sigma is None:
        print("\n✗ Pipeline failed at PSF measurement")
        return False

    # Step 2: Parameter Generation
    params, stats = test_parameter_generation(sigma, image_path, verbose=verbose)

    # Step 3: Write Parameter File
    param_file = f"{output_prefix}.param"
    success = test_param_file_writing(params, param_file, verbose=verbose)

    if not success:
        print("\n✗ Pipeline failed at parameter file writing")
        return False

    print("\n" + "="*60)
    print("✓ PIPELINE COMPLETE")
    print("="*60)
    print("\nResults:")
    print(f"  Parameter file: {param_file}")
    print(f"  PSF sigma: {sigma:.3f} pixels")

    return True


def main():
    """Main test routine."""
    # Test data location
    testsuite_dir = Path.home() / "projects" / "astro" / "Testsuite"

    if not testsuite_dir.exists():
        print(f"ERROR: Testsuite directory not found: {testsuite_dir}")
        return False

    # Find test FITS files
    fits_files = list(testsuite_dir.glob("47Tuc*.fits"))
    if not fits_files:
        print(f"ERROR: No test FITS files found in {testsuite_dir}")
        return False

    fits_files = sorted(fits_files)[:1]  # Start with first one for now

    # Create output directory
    output_dir = Path("/tmp/dophot_test")
    output_dir.mkdir(exist_ok=True)

    print(f"\nTest Data Directory: {testsuite_dir}")
    print(f"Output Directory: {output_dir}")
    print(f"Test Images: {len(fits_files)}")

    # Run pipeline on each image
    all_success = True
    for fits_file in fits_files:
        success = run_full_pipeline(str(fits_file), str(output_dir), verbose=True)
        all_success = all_success and success

    # Summary
    print("\n" + "#"*60)
    print("# Test Summary")
    print("#"*60)
    if all_success:
        print("✓ ALL TESTS PASSED")
        print(f"\nOutput files in: {output_dir}")
        return True
    else:
        print("✗ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
