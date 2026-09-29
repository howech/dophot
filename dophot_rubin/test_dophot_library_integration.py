"""
Integration test for DoPHOT library via ctypes.

This test loads a real astronomical image, runs DoPHOT photometry via the
C library (not subprocess), and verifies results match the reference.

Note: This test requires libdophot.so to be compiled and available.
It will be skipped if the library is not found or if CFITSIO is not installed.
"""

import pytest
import numpy as np
from pathlib import Path
from typing import Optional

try:
    from astropy.io import fits
    HAS_ASTROPY = True
except ImportError:
    HAS_ASTROPY = False

try:
    from dophot_rubin.test_library_wrapper import DoPHOTLibrary, DoPHOTParams
    HAS_LIBRARY = True
except ImportError:
    HAS_LIBRARY = False


class TestDoPHOTLibrary:
    """Integration tests for DoPHOT library photometry."""

    @pytest.fixture
    def test_image_path(self) -> Optional[Path]:
        """Get path to test image."""
        path = Path(__file__).parent.parent / "dophot_c" / "verif_data" / "J0159.8.chip_01.fits"
        return path if path.exists() else None

    @pytest.fixture
    def dophot_lib(self) -> Optional[DoPHOTLibrary]:
        """Load DoPHOT library."""
        try:
            return DoPHOTLibrary()
        except OSError:
            return None  # Library not available

    @pytest.mark.skipif(not HAS_ASTROPY, reason="astropy not installed")
    @pytest.mark.skipif(not HAS_LIBRARY, reason="dophot_rubin.test_library_wrapper not available")
    def test_photometry_on_test_image(self, test_image_path, dophot_lib):
        """Test photometry on reference image.

        Expected: ~316 stars detected (matches subprocess version)
        """
        if test_image_path is None:
            pytest.skip("Test image not found")
        if dophot_lib is None:
            pytest.skip("DoPHOT library not available")

        # Load test image
        with fits.open(test_image_path) as hdul:
            image = hdul[0].data.astype("float32")
            header = dict(hdul[0].header)

        # Convert to int32 (same as preprocessing)
        image_int32 = np.asarray(image, dtype=np.int32)

        # Create noise array (simplified: based on image statistics)
        sky_value = np.median(image_int32)
        noise = np.sqrt(np.abs(image_int32 - sky_value) + 100)
        noise_int32 = np.asarray(noise, dtype=np.int32)

        # Create parameters struct
        params = DoPHOTParams(
            sigma=1.661,      # From preprocessing
            fwhm=3.91,         # Computed: 2.35 * sigma
            sky_value=float(sky_value),
            gain=1.0,
            rdnoise=15.0,
            saturation=60000.0,
            nthpix=30,         # From preprocessing
            nfit=5,            # Number of fit parameters
            model=0,           # PGAUSS
        )

        # Run photometry
        retcode, results = dophot_lib.run(image_int32, noise_int32, params)

        # Verify success
        assert retcode == 0, f"DoPHOT failed with code {retcode}: {dophot_lib._interpret_error_code(retcode)}"
        assert results is not None, "Results should not be None on success"
        assert results["n_stars"] > 0, "Should detect at least some stars"

        # Check reference: expect ~316 stars
        n_stars = results["n_stars"]
        print(f"\nDetected {n_stars} stars (expected ~316)")
        assert n_stars > 200, f"Expected >200 stars, got {n_stars}"
        assert n_stars < 500, f"Expected <500 stars, got {n_stars}"

        # Verify result arrays
        assert len(results["x"]) == n_stars, "X array size mismatch"
        assert len(results["y"]) == n_stars, "Y array size mismatch"
        assert len(results["mag"]) == n_stars, "Magnitude array size mismatch"
        assert len(results["err"]) == n_stars, "Error array size mismatch"

        # Check that positions are reasonable (within image bounds)
        image_h, image_w = image_int32.shape
        assert np.all(results["x"] > 0) and np.all(results["x"] < image_w), "X positions out of bounds"
        assert np.all(results["y"] > 0) and np.all(results["y"] < image_h), "Y positions out of bounds"

        # Check that magnitudes are reasonable
        mags = results["mag"]
        assert np.all(np.isfinite(mags)), "Some magnitudes are NaN or inf"
        assert np.nanmin(mags) > -30, "Magnitude too faint"
        assert np.nanmax(mags) < 30, "Magnitude too bright (saturation?)"

        print(f"✓ Position range: X=[{np.min(results['x']):.1f}, {np.max(results['x']):.1f}]")
        print(f"✓ Position range: Y=[{np.min(results['y']):.1f}, {np.max(results['y']):.1f}]")
        print(f"✓ Magnitude range: [{np.min(mags):.2f}, {np.max(mags):.2f}]")
        print(f"✓ Error range: [{np.min(results['err']):.4f}, {np.max(results['err']):.4f}]")

    def test_library_loading(self, dophot_lib):
        """Test that library can be loaded and is callable."""
        if dophot_lib is None:
            pytest.skip("DoPHOT library not available")

        assert dophot_lib is not None, "Library should load successfully"
        assert hasattr(dophot_lib, "dophot_photometry"), "Should have dophot_photometry function"
        assert hasattr(dophot_lib, "run"), "Should have run() method"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
