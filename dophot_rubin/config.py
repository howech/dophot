"""
DoPHOT Configuration for Rubin Pipeline Task.

Defines all configurable parameters for DoPHOT processing.
"""

from lsst.pex import config as pexConfig


class DoPHOTConfig(pexConfig.Config):
    """Configuration for DoPHOT photometry task."""

    # ============================================================
    # PSF Measurement Parameters
    # ============================================================

    psfDetectionThreshold = pexConfig.Field(
        dtype=float,
        default=10.0,
        doc="Detection threshold for bright stars (sigma above sky) "
            "used for PSF measurement. Higher values reject faint stars."
    )

    psfMinStars = pexConfig.Field(
        dtype=int,
        default=20,
        doc="Minimum number of successful PSF measurements required. "
            "Task fails if fewer stars can be measured."
    )

    psfBoxSize = pexConfig.Field(
        dtype=int,
        default=31,
        doc="Postage stamp size for PSF fitting (pixels). Must be odd."
    )

    psfEdgeBuffer = pexConfig.Field(
        dtype=int,
        default=32,
        doc="Minimum distance from image edge for PSF measurement (pixels). "
            "Stars closer to edges are excluded."
    )

    # ============================================================
    # DoPHOT Execution Parameters
    # ============================================================

    doPHOTExecPath = pexConfig.Field(
        dtype=str,
        default="dophot",
        doc="Path to DoPHOT executable. Can be absolute path or in PATH."
    )

    doPHOTWorkDir = pexConfig.Field(
        dtype=str,
        default="/tmp/dophot_work",
        doc="Working directory for DoPHOT temporary files."
    )

    useEmpiricalModel = pexConfig.Field(
        dtype=bool,
        default=True,
        doc="Use empirical PSF model in DoPHOT for improved accuracy."
    )

    psfModel = pexConfig.ChoiceField(
        dtype=str,
        default="PGAUSS",
        allowed={"PGAUSS": "Pseudo-Gaussian (recommended)",
                 "GAUSS": "Simple Gaussian",
                 "EXTPGAUSS": "Extended Pseudo-Gaussian"},
        doc="PSF model to use in DoPHOT fitting."
    )

    # ============================================================
    # Image Processing Parameters
    # ============================================================

    skyEstimationMethod = pexConfig.ChoiceField(
        dtype=str,
        default="PERCENTILE",
        allowed={"PERCENTILE": "Percentile-based (robust)",
                 "MEDIAN": "Median filter"},
        doc="Method for estimating sky background in DoPHOT."
    )

    maskBadPixels = pexConfig.Field(
        dtype=bool,
        default=True,
        doc="Mask bad pixels and cosmic rays before DoPHOT processing."
    )

    useVarianceMap = pexConfig.Field(
        dtype=bool,
        default=True,
        doc="Use variance extension from DP2 FITS for weighting."
    )

    # ============================================================
    # Postprocessing Parameters
    # ============================================================

    doAperturePhotometry = pexConfig.Field(
        dtype=bool,
        default=True,
        doc="Measure aperture photometry for comparison."
    )

    apertureRadius = pexConfig.Field(
        dtype=float,
        default=2.0,
        doc="Aperture radius for aperture photometry (arcsec)."
    )

    doApertureCorrection = pexConfig.Field(
        dtype=bool,
        default=True,
        doc="Apply aperture correction to convert aperture mag to total mag."
    )

    doWcsTransform = pexConfig.Field(
        dtype=bool,
        default=True,
        doc="Transform pixel coordinates to RA/Dec using WCS from calexp."
    )

    doMagnitudeConversion = pexConfig.Field(
        dtype=bool,
        default=True,
        doc="Convert instrumental magnitudes to AB magnitudes using photoCalib."
    )

    # ============================================================
    # Quality Flags & Cuts
    # ============================================================

    minPsfSignalToNoise = pexConfig.Field(
        dtype=float,
        default=5.0,
        doc="Minimum S/N for a measurement to be flagged as good."
    )

    maxCentroidUncertainty = pexConfig.Field(
        dtype=float,
        default=1.0,
        doc="Maximum allowed centroid uncertainty (pixels) for good measurements."
    )

    minIterativeArea = pexConfig.Field(
        dtype=float,
        default=0.5,
        doc="Minimum area for iterative fit (relative to PSF area)."
    )

    # ============================================================
    # Debugging & Output
    # ============================================================

    doDebug = pexConfig.Field(
        dtype=bool,
        default=False,
        doc="Enable debug output and intermediate file retention."
    )

    saveIntermediateFiles = pexConfig.Field(
        dtype=bool,
        default=False,
        doc="Save parameter files and DoPHOT output for inspection."
    )

    intermediateDir = pexConfig.Field(
        dtype=str,
        default="./dophot_intermediate",
        doc="Directory for saving intermediate files (if saveIntermediateFiles=True)."
    )

    # ============================================================
    # Logging
    # ============================================================

    logLevel = pexConfig.ChoiceField(
        dtype=str,
        default="INFO",
        allowed={"DEBUG": "Verbose debug output",
                 "INFO": "Informational messages",
                 "WARNING": "Warnings only",
                 "ERROR": "Errors only"},
        doc="Logging level for DoPHOT task."
    )


class DoPHOTTaskConnections:
    """
    Data connections for DoPHOT task (requires lsst.pipe.base).

    This is a placeholder for the actual connections when Rubin Stack is available.
    Real implementation will use @pipelineConnections decorator.
    """

    # Inputs
    calexp = "Calibrated exposure (DP2 format with IMAGE/MASK/VARIANCE extensions)"
    skyMap = "Sky map for WCS"
    photoCalib = "Photometric calibration for magnitude conversion"
    psf = "PSF model from reprocessVisitImage"

    # Outputs
    src = "SourceCatalog with DoPHOT photometry"
    srcMetadata = "Metadata for source catalog"

    # Optional outputs
    srcDoPHOT = "Raw DoPHOT output (if saveIntermediateFiles=True)"
    doPHOTParams = "Parameter file used (if saveIntermediateFiles=True)"
