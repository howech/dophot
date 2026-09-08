"""Unit tests for DoPHOT configuration."""

import unittest
from dophot_rubin.config import DoPHOTConfig


class TestDoPHOTConfig(unittest.TestCase):
    """Test DoPHOT configuration."""

    def test_config_creation(self):
        """Test that config can be instantiated."""
        config = DoPHOTConfig()
        self.assertIsNotNone(config)

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = DoPHOTConfig()

        # PSF measurement defaults
        self.assertEqual(config.psfDetectionThreshold, 10.0)
        self.assertEqual(config.psfMinStars, 20)
        self.assertEqual(config.psfBoxSize, 31)
        self.assertEqual(config.psfEdgeBuffer, 32)

        # DoPHOT execution defaults
        self.assertEqual(config.doPHOTExecPath, "dophot")
        self.assertTrue(config.useEmpiricalModel)
        self.assertEqual(config.psfModel, "PGAUSS")

        # Postprocessing defaults
        self.assertTrue(config.doApertureCorrection)
        self.assertTrue(config.doWcsTransform)
        self.assertTrue(config.doMagnitudeConversion)

        # Logging defaults
        self.assertEqual(config.logLevel, "INFO")

    def test_config_modification(self):
        """Test that config values can be modified."""
        config = DoPHOTConfig()

        # Modify values
        config.psfDetectionThreshold = 5.0
        config.psfMinStars = 10
        config.logLevel = "DEBUG"

        # Verify modifications
        self.assertEqual(config.psfDetectionThreshold, 5.0)
        self.assertEqual(config.psfMinStars, 10)
        self.assertEqual(config.logLevel, "DEBUG")

    def test_config_types(self):
        """Test that config values have correct types."""
        config = DoPHOTConfig()

        self.assertIsInstance(config.psfDetectionThreshold, float)
        self.assertIsInstance(config.psfMinStars, int)
        self.assertIsInstance(config.useEmpiricalModel, bool)
        self.assertIsInstance(config.doPHOTExecPath, str)
        self.assertIsInstance(config.logLevel, str)


if __name__ == '__main__':
    unittest.main()
