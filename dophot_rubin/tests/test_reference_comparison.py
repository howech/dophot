"""
Tier A validation: Compare pipeline output against DoPHOT C reference fixture.

Tests the fixed DoPHOTPreprocessor → DoPHOTExecutor pipeline against the
in-repo DoPHOT_C-master/verif_data/compare_out/ reference data for J0159.8.chip_01.fits.

Uses structural/statistical comparison (not byte-exact diff) since our pipeline's
auto-generated parameters differ from the original C-verification workflow's
hand-tuned parameters.
"""

from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits
from astropy.table import Table
from scipy import stats

from dophot_rubin import DoPHOTConfig, DoPHOTPreprocessor
from dophot_rubin.execute_dophot import DoPHOTExecutor
from dophot_rubin.parse_dophot_output import parse_obj_out

# Paths
REPO_ROOT = Path(__file__).parent.parent.parent
TEST_IMAGE = REPO_ROOT / "DoPHOT_C-master/verif_data/J0159.8.chip_01.fits"
REFERENCE_CATALOG = REPO_ROOT / "DoPHOT_C-master/verif_data/compare_out/obj_out_J0159.8.chip_01"
DOPHOT_EXE = REPO_ROOT / "DoPHOT_C-master/working_data/dophot"


@pytest.fixture
def test_image_data():
    """Load test FITS image."""
    if not TEST_IMAGE.exists():
        pytest.skip(f"Test image not found: {TEST_IMAGE}")

    with fits.open(TEST_IMAGE) as hdul:
        image = hdul[0].data.astype('float32')
        header = dict(hdul[0].header)

    return image, header


@pytest.fixture
def reference_sources():
    """Load reference catalog."""
    if not REFERENCE_CATALOG.exists():
        pytest.skip(f"Reference catalog not found: {REFERENCE_CATALOG}")

    return parse_obj_out(str(REFERENCE_CATALOG))


def test_preprocessing_runs(test_image_data):
    """Test that preprocessing completes without errors."""
    image, header = test_image_data

    config = DoPHOTConfig()
    preprocessor = DoPHOTPreprocessor(config)

    result = preprocessor.run(image=image, header=header)

    # Verify all expected fields are present
    assert result.sigma > 0
    assert result.params is not None
    assert result.image_int32 is not None
    assert result.image_with_psf is not None
    assert result.conversion_factor > 0
    assert result.param_file.exists()


def test_dophot_executable_exists():
    """Test that the DoPHOT executable is available."""
    if not DOPHOT_EXE.exists():
        pytest.skip(f"DoPHOT executable not found: {DOPHOT_EXE}")

    # Just verify it's a valid ELF binary
    with open(DOPHOT_EXE, 'rb') as f:
        magic = f.read(4)
        assert magic == b'\x7fELF', "DoPHOT executable is not a valid ELF binary"


@pytest.mark.skipif(not DOPHOT_EXE.exists(), reason="DoPHOT executable not compiled")
def test_full_pipeline(test_image_data, reference_sources, tmp_path):
    """Test full pipeline: preprocessing → DoPHOT execution → parsing."""
    image, header = test_image_data

    # Step 1: Preprocessing
    config = DoPHOTConfig()
    preprocessor = DoPHOTPreprocessor(config)
    preprocessing_result = preprocessor.run(image=image, header=header, work_dir=tmp_path)

    # Write intermediate FITS
    intermediate_fits = tmp_path / "intermediate_i4.fits"
    hdu = fits.PrimaryHDU(preprocessing_result.image_with_psf.astype('int32'))
    hdu.header['UNITCONV'] = preprocessing_result.conversion_factor
    fits.HDUList([hdu]).writeto(intermediate_fits, overwrite=True)

    # Step 2: Execute DoPHOT
    executor = DoPHOTExecutor(config)
    catalog = executor.run(
        image_path=intermediate_fits,
        param_file=preprocessing_result.param_file,
        output_dir=tmp_path,
        conversion_factor=preprocessing_result.conversion_factor,
        original_units=preprocessing_result.units,
    )

    # Verify we detected sources
    assert len(catalog) > 0, "DoPHOT did not detect any sources"

    # Step 3: Structural comparison with reference
    _compare_catalogs(catalog, reference_sources)


def _compare_catalogs(our_catalog: Table, reference_sources):
    """
    Structural comparison of detected sources against reference.

    Checks:
    1. Source count is reasonable (within 50% margin)
    2. Spatial cross-match: find nearby sources within 5 pixels
    3. Flux rank correlation for matched pairs
    """
    # Extract real sources (type == 1)
    our_real = our_catalog[our_catalog['type'] == 1]
    ref_real = [s for s in reference_sources if s.type == 1]

    # Check 1: Source count
    count_ratio = len(our_real) / len(ref_real) if ref_real else 1.0
    assert 0.5 < count_ratio < 2.0, (
        f"Source count mismatch: detected {len(our_real)}, reference {len(ref_real)} "
        f"(ratio {count_ratio:.2f})"
    )

    # Check 2: Spatial cross-match
    if len(our_real) > 0 and ref_real:
        our_positions = np.array([[s['x'], s['y']] for s in our_real])
        ref_positions = np.array([[s.x, s.y] for s in ref_real])

        matched = 0
        for ref_pos in ref_positions:
            # Find nearest detected source
            distances = np.sqrt(np.sum((our_positions - ref_pos) ** 2, axis=1))
            if np.min(distances) < 5.0:  # 5 pixel tolerance
                matched += 1

        recovery_fraction = matched / len(ref_real)
        assert recovery_fraction > 0.5, (
            f"Low recovery fraction: {recovery_fraction:.1%} "
            f"({matched}/{len(ref_real)} reference sources matched)"
        )

    # Check 3: Flux rank correlation for matched pairs
    if len(our_real) > 0 and ref_real:
        our_positions = np.array([[s['x'], s['y']] for s in our_real])
        ref_positions = np.array([[s.x, s.y] for s in ref_real])
        ref_fluxes = np.array([s.flux for s in ref_real])
        our_fluxes = np.array([s['flux'] for s in our_real])

        # Find matches
        our_matched_fluxes = []
        ref_matched_fluxes = []

        for i, ref_pos in enumerate(ref_positions):
            distances = np.sqrt(np.sum((our_positions - ref_pos) ** 2, axis=1))
            if len(distances) > 0 and np.min(distances) < 5.0:
                nearest_idx = np.argmin(distances)
                our_matched_fluxes.append(our_fluxes[nearest_idx])
                ref_matched_fluxes.append(ref_fluxes[i])

        if len(our_matched_fluxes) > 2:
            # Spearman rank correlation (robust to scaling differences)
            rank_corr, _ = stats.spearmanr(our_matched_fluxes, ref_matched_fluxes)
            assert rank_corr > 0.5, (
                f"Low flux rank correlation: {rank_corr:.3f} "
                f"({len(our_matched_fluxes)} matched sources)"
            )


if __name__ == "__main__":
    # Can be run standalone for debugging
    pytest.main([__file__, "-v", "-s"])
