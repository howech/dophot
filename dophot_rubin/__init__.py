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

from .config import DoPHOTConfig
from .execute_dophot import DoPHOTExecutor, execute_dophot
from .image_scaling import (
    apply_mask_to_scaled_image,
    detect_units,
    scale_image_to_int32,
)
from .parse_dophot_output import convert_to_original_units, parse_obj_out
from .postprocess import DoPHOTPostprocessor, create_source_catalog
from .preprocess_wrapper import DoPHOTPreprocessor, PreprocessingContext
from .psf_measurement import (
    append_psf_to_image,
    generate_parameter_file,
    measure_psf_simple,
)
from .task import DoPHOTConnections, DoPHOTTask

__version__ = '0.1.0'
__all__ = [
    # Configuration
    'DoPHOTConfig',
    'DoPHOTConnections',
    # DoPHOT execution
    'DoPHOTExecutor',
    'DoPHOTPostprocessor',
    # Class-based API (wrappers)
    'DoPHOTPreprocessor',
    # Rubin integration
    'DoPHOTTask',
    'PreprocessingContext',
    'append_psf_to_image',
    'apply_mask_to_scaled_image',
    'convert_to_original_units',
    'create_source_catalog',
    # Core preprocessing (proven working)
    'detect_units',
    'execute_dophot',
    'generate_parameter_file',
    'measure_psf_simple',
    # Output parsing
    'parse_obj_out',
    'scale_image_to_int32',
]
