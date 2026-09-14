"""Unit tests for DoPHOT PipelineTask."""

import tempfile
import unittest
from pathlib import Path

from dophot_rubin.config import DoPHOTConfig
from dophot_rubin.task import DoPHOTTask


class TestDoPHOTTask(unittest.TestCase):
    """Test DoPHOT PipelineTask."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = DoPHOTConfig()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config.doPHOTWorkDir = self.temp_dir.name

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_task_creation(self):
        """Test that task can be instantiated."""
        task = DoPHOTTask(config=self.config)
        self.assertIsNotNone(task)
        self.assertEqual(task.name, "DoPHOTTask")

    def test_task_config(self):
        """Test that task has correct config."""
        task = DoPHOTTask(config=self.config)
        self.assertEqual(task.config.psfMinStars, self.config.psfMinStars)
        self.assertEqual(
            task.config.doApertureCorrection,
            self.config.doApertureCorrection
        )

    def test_task_work_dir_creation(self):
        """Test that work directory is created."""
        DoPHOTTask(config=self.config)
        work_dir = Path(self.config.doPHOTWorkDir)
        self.assertTrue(work_dir.exists())

    def test_task_logging(self):
        """Test that task has logging configured."""
        task = DoPHOTTask(config=self.config)
        self.assertIsNotNone(task.log)
        # Verify logger name contains 'task' or 'dophot'
        log_name = task.log.name.lower()
        self.assertTrue("task" in log_name or "dophot" in log_name)

    def test_default_name(self):
        """Test that default name is set."""
        task = DoPHOTTask(config=self.config)
        self.assertEqual(task._DefaultName, "dophot")

    def test_config_class(self):
        """Test that ConfigClass is set correctly."""
        self.assertEqual(DoPHOTTask.ConfigClass, DoPHOTConfig)


class TestDoPHOTTaskWithConfig(unittest.TestCase):
    """Test DoPHOT task with various configurations."""

    def test_task_with_debug_config(self):
        """Test task with debug config."""
        config = DoPHOTConfig()
        config.doDebug = True
        config.logLevel = "DEBUG"

        task = DoPHOTTask(config=config)
        self.assertTrue(task.config.doDebug)
        self.assertEqual(task.config.logLevel, "DEBUG")

    def test_task_with_custom_psf_threshold(self):
        """Test task with custom PSF threshold."""
        config = DoPHOTConfig()
        config.psfDetectionThreshold = 15.0
        config.psfMinStars = 50

        task = DoPHOTTask(config=config)
        self.assertEqual(task.config.psfDetectionThreshold, 15.0)
        self.assertEqual(task.config.psfMinStars, 50)

    def test_task_with_postprocessing_disabled(self):
        """Test task with postprocessing options disabled."""
        config = DoPHOTConfig()
        config.doApertureCorrection = False
        config.doWcsTransform = False
        config.doMagnitudeConversion = False

        task = DoPHOTTask(config=config)
        self.assertFalse(task.config.doApertureCorrection)
        self.assertFalse(task.config.doWcsTransform)
        self.assertFalse(task.config.doMagnitudeConversion)


if __name__ == '__main__':
    unittest.main()
