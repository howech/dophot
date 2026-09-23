"""
DoPHOT Configuration.

Supports both standalone and Rubin Stack modes.
When lsst.pex is available, uses Rubin Config; otherwise uses simple dict-like config.
"""

try:
    from lsst.pex import config as pexConfig
    RUBIN_AVAILABLE = True
except ImportError:
    RUBIN_AVAILABLE = False


if RUBIN_AVAILABLE:
    class DoPHOTConfig(pexConfig.Config):
        """Configuration for DoPHOT photometry task (Rubin Stack mode)."""

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
            doc="Path to DoPHOT executable. Can be absolute path or in PATH (default)."
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

else:
    class DoPHOTConfig:
        """Configuration for DoPHOT photometry task (standalone mode, no Rubin Stack)."""

        def __init__(self):
            # PSF Measurement Parameters
            self.psfDetectionThreshold = 10.0
            self.psfMinStars = 20
            self.psfBoxSize = 31
            self.psfEdgeBuffer = 32

            # DoPHOT Execution Parameters
            # Try to find dophot in package first, fallback to PATH
            from pathlib import Path
            dophot_in_package = Path(__file__).parent / "dophot_c" / "working_data" / "dophot"
            if dophot_in_package.exists():
                self.doPHOTExecPath = str(dophot_in_package)
            else:
                self.doPHOTExecPath = "dophot"  # Fallback to PATH
            self.doPHOTWorkDir = "/tmp/dophot_work"
            self.useEmpiricalModel = True
            self.psfModel = "PGAUSS"

            # Image Processing Parameters
            self.skyEstimationMethod = "PERCENTILE"
            self.maskBadPixels = True
            self.useVarianceMap = True

            # Postprocessing Parameters
            self.doAperturePhotometry = True
            self.apertureRadius = 2.0
            self.doApertureCorrection = True
            self.doWcsTransform = True
            self.doMagnitudeConversion = True

            # Quality Flags & Cuts
            self.minPsfSignalToNoise = 5.0
            self.maxCentroidUncertainty = 1.0
            self.minIterativeArea = 0.5

            # Debugging & Output
            self.doDebug = False
            self.saveIntermediateFiles = False
            self.intermediateDir = "./dophot_intermediate"

            # Logging
            self.logLevel = "INFO"


if RUBIN_AVAILABLE:
    from lsst.pipe.base import Connections
    from lsst.pipe.base.connectionTypes import Input, Output

    class DoPHOTTaskConnections(Connections):
        """Data connections for DoPHOT task (Rubin Stack mode)."""

        # Inputs
        calexp = Input(
            doc="Calibrated exposure (DP2 format)",
            name="calexp",
            storageClass="ExposureF",
            dimensions=["instrument", "visit", "detector"]
        )

        psf = Input(
            doc="PSF model",
            name="psf",
            storageClass="PSF",
            dimensions=["instrument", "visit", "detector"]
        )

        photoCalib = Input(
            doc="Photometric calibration",
            name="photoCalib",
            storageClass="PhotoCalib",
            dimensions=["instrument", "visit", "detector"]
        )

        # Outputs
        src = Output(
            doc="DoPHOT source catalog",
            name="src_dophot",
            storageClass="SourceCatalog",
            dimensions=["instrument", "visit", "detector"]
        )
else:
    class DoPHOTTaskConnections:
        """Placeholder for DoPHOT task connections (standalone mode, no Rubin Stack)."""
