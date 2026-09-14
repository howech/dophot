"""Unit tests for preprocessing wrapper."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from dophot_rubin.config import DoPHOTConfig
from dophot_rubin.preprocess_wrapper import DoPHOTPreprocessor


class TestDoPHOTPreprocessor(unittest.TestCase):
    """Test DoPHOT preprocessing wrapper."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = DoPHOTConfig()
        self.preprocessor = DoPHOTPreprocessor(self.config)
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_preprocessor_creation(self):
        """Test that preprocessor can be instantiated."""
        self.assertIsNotNone(self.preprocessor)
        self.assertEqual(self.preprocessor.config, self.config)

    def test_image_stats_extraction_no_header(self):
        """Test image statistics extraction without header."""
        # Create synthetic image
        image = np.random.normal(1000, 100, (100, 100))

        stats = self.preprocessor._extract_image_stats(header=None, image=image)

        self.assertIn('sky_value', stats)
        self.assertIn('sky_rms', stats)
        self.assertIn('gain', stats)
        self.assertIn('saturation', stats)
        self.assertIn('rdnoise', stats)

        # Check types
        self.assertIsInstance(stats['sky_value'], float)
        self.assertIsInstance(stats['gain'], float)

    def test_image_stats_extraction_with_defaults(self):
        """Test that default values are used when header is None."""
        image = np.random.normal(1000, 100, (50, 50))
        stats = self.preprocessor._extract_image_stats(header=None, image=image)

        # Verify default values
        self.assertEqual(stats['gain'], 1.0)
        self.assertEqual(stats['saturation'], 60000)
        self.assertEqual(stats['rdnoise'], 10.0)

    def test_image_stats_with_dict_header(self):
        """Test image statistics extraction with dictionary header."""
        image = np.random.normal(1000, 100, (50, 50))
        header = {
            'GAINA': 2.0,
            'SATURATE': 50000,
            'RDNOISEA': 8.0,
        }

        stats = self.preprocessor._extract_image_stats(header=header, image=image)

        self.assertEqual(stats['gain'], 2.0)
        self.assertEqual(stats['saturation'], 50000)
        self.assertEqual(stats['rdnoise'], 8.0)

    def test_psf_measurement_empty_image(self):
        """Test PSF measurement on empty image."""
        # Create uniform image (no stars)
        image = np.ones((100, 100)) * 1000.0

        stats = {
            'sky_value': 1000,
            'sky_rms': 10,
            'gain': 1.0,
            'saturation': 60000,
            'rdnoise': 10.0
        }

        sigma, n_stars, success = self.preprocessor._measure_psf(image, stats)

        # Should fail due to no stars detected
        self.assertFalse(success)
        self.assertEqual(n_stars, 0)

    def test_psf_measurement_needs_stars(self):
        """Test that PSF measurement requires minimum stars."""
        # Create image with very few stars
        image = np.ones((100, 100)) * 1000.0
        # Add one very bright pixel
        image[50, 50] = 5000.0

        stats = {
            'sky_value': 1000,
            'sky_rms': 10,
            'gain': 1.0,
            'saturation': 60000,
            'rdnoise': 10.0
        }

        sigma, n_stars, success = self.preprocessor._measure_psf(image, stats)

        # Should fail if fewer than psfMinStars
        if n_stars < self.config.psfMinStars:
            self.assertFalse(success)


class TestPreprocessingContext(unittest.TestCase):
    """Test preprocessing context manager."""

    def test_context_manager(self):
        """Test that context manager works."""
        from dophot_rubin.preprocess_wrapper import PreprocessingContext

        with PreprocessingContext() as work_dir:
            self.assertIsNotNone(work_dir)
            self.assertTrue(work_dir.exists())

    def test_context_with_custom_dir(self):
        """Test context manager with custom directory."""
        import tempfile

        from dophot_rubin.preprocess_wrapper import PreprocessingContext

        with tempfile.TemporaryDirectory() as tmpdir:
            with PreprocessingContext(tmpdir) as work_dir:
                self.assertEqual(work_dir, Path(tmpdir))
                self.assertTrue(work_dir.exists())


if __name__ == '__main__':
    unittest.main()
