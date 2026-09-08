"""
DoPHOT Rubin Integration Package.

Provides a PipelineTask for running DoPHOT photometry within
the Rubin Observatory LSST data processing pipeline.

Classes:
    DoPHOTConfig: Configuration for DoPHOT processing
    DoPHOTTask: Main PipelineTask for orchestrating photometry

Usage:
    from dophot_rubin import DoPHOTTask, DoPHOTConfig

    # Create task
    config = DoPHOTConfig()
    task = DoPHOTTask(config=config)

    # Run on data (requires Rubin Stack)
    # task.runQuantum(butlerQC, inputRefs, outputRefs)
"""

from .config import DoPHOTConfig, DoPHOTTaskConnections
from .task import DoPHOTTask, create_dophot_task

__version__ = '0.1.0'
__all__ = [
    'DoPHOTConfig',
    'DoPHOTTask',
    'DoPHOTTaskConnections',
    'create_dophot_task',
]
