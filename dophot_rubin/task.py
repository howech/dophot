"""
DoPHOT PipelineTask for Rubin Observatory.

Orchestrates PSF-based photometry using DoPHOT on calibrated visit images.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from astropy.io import fits
from astropy.table import Table

from .config import DoPHOTConfig
from .execute_dophot import DoPHOTExecutor
from .postprocess import DoPHOTPostprocessor
from .preprocess_wrapper import DoPHOTPreprocessor, PreprocessingContext

if TYPE_CHECKING:
    from lsst.afw.image import ExposureF, PhotoCalib


class ConversionFactors(NamedTuple):
    """Conversion factors for transforming photometry units."""
    units: str
    factor: float
    description: str

try:
    from lsst.pex.config import Config
    from lsst.pipe.base import PipelineTask, PipelineTaskConnections
    from lsst.pipe.base import connectionTypes as cT
    HAS_RUBIN_STACK = True
except ImportError:
    HAS_RUBIN_STACK = False
    # Fallback for development
    class PipelineTask:
        def __init__(self, config: DoPHOTConfig, name: str | None = None) -> None:
            self.config = config
            self.name = name or self.__class__.__name__

    class PipelineTaskConnections:
        pass

    class Config:
        pass

    # Mock connectionTypes for development
    class MockConnectionTypes:
        class Input:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass
        class Output:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

    cT = MockConnectionTypes()

logger = logging.getLogger(__name__)


class DoPHOTInputConnections(PipelineTaskConnections):
    """Input connections for DoPHOT task."""
    if HAS_RUBIN_STACK:
        calexp = cT.Input(
            doc="Calibrated exposure from reprocessVisitImage (DP2 format)",
            name="calexp",
            storageClass="ExposureF",
            dimensions=["visit", "detector"]
        )
        photoCalib = cT.Input(
            doc="Photometric calibration",
            name="calexp.photoCalib",
            storageClass="PhotoCalib",
            dimensions=["visit", "detector"]
        )
        psf = cT.Input(
            doc="PSF model",
            name="calexp.psf",
            storageClass="PSF",
            dimensions=["visit", "detector"],
            optional=True
        )


class DoPHOTOutputConnections(PipelineTaskConnections):
    """Output connections for DoPHOT task."""
    if HAS_RUBIN_STACK:
        src = cT.Output(
            doc="SourceCatalog with DoPHOT photometry",
            name="dophot_src",
            storageClass="SourceCatalog",
            dimensions=["visit", "detector"]
        )
        srcMetadata = cT.Output(
            doc="Metadata about DoPHOT processing",
            name="dophot_srcMetadata",
            storageClass="PropertySet",
            dimensions=["visit", "detector"],
            optional=True
        )


class DoPHOTConnections(DoPHOTInputConnections, DoPHOTOutputConnections):
    """Full connections for DoPHOT task."""


class DoPHOTTask(PipelineTask):
    """
    Perform PSF-based photometry using DoPHOT.

    This task orchestrates the complete DoPHOT workflow:
    1. Measure PSF from bright stars in the image
    2. Generate DoPHOT tuning parameters automatically
    3. Execute DoPHOT C photometry code
    4. Postprocess results (aperture corrections, WCS, magnitudes)

    Inputs:
        calexp: Calibrated exposure from reprocessVisitImage
                (DP2 format: IMAGE, MASK, VARIANCE extensions)
        photoCalib: Photometric calibration for magnitude conversion
        psf: PSF model from previous processing

    Outputs:
        src: SourceCatalog with DoPHOT photometry
        srcMetadata: Metadata about processing
    """

    if HAS_RUBIN_STACK:
        ConnectionsClass = DoPHOTConnections

    ConfigClass = DoPHOTConfig
    _DefaultName = "dophot"

    config: DoPHOTConfig

    def __init__(
        self,
        config: DoPHOTConfig,
        name: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize DoPHOT task."""
        super().__init__(config, name=name, **kwargs)

        # Set up logging
        self.log = logging.getLogger(self.name)
        self.log.setLevel(getattr(logging, self.config.logLevel))

        # Create working directory
        self.work_dir = Path(self.config.doPHOTWorkDir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

        self.log.info(f"DoPHOT task initialized. Working directory: {self.work_dir}")

    def runQuantum(self, butlerQC: Any, inputRefs: Any, outputRefs: Any) -> None:
        """
        Execute DoPHOT photometry for a single visit/detector.

        This is the main entry point called by the Rubin pipeline for each
        dataId (typically per-detector per-visit).

        Parameters
        ----------
        butlerQC : ButlerQuantumContext
            Data access object for this quantum
        inputRefs : InputQuantumContext
            References to input datasets
        outputRefs : OutputQuantumContext
            References to output datasets
        """
        self.log.info(f"Running DoPHOT for {inputRefs.calexp.dataId}")

        try:
            # Load inputs
            calexp = butlerQC.get(inputRefs.calexp)
            photoCalib = butlerQC.get(inputRefs.photoCalib)

            # Run preprocessing
            preprocessing_result = self._preprocessing(calexp)

            # Run DoPHOT
            catalog, conversion_factors = self._run_dophot(preprocessing_result)

            # Run postprocessing
            src = self._postprocessing(calexp, catalog, photoCalib, conversion_factors)

            # Write outputs
            butlerQC.put(src, outputRefs.src)

            self.log.info(f"DoPHOT completed: {len(src)} sources detected")

        except Exception as e:
            self.log.error(f"DoPHOT failed: {e}")
            raise

    def _preprocessing(self, calexp: "ExposureF"):
        """
        Measure PSF and generate DoPHOT parameters.

        Parameters
        ----------
        calexp : lsst.afw.image.ExposureF
            Calibrated exposure

        Returns
        -------
        result : PreprocessingResult
            Complete preprocessing result with all intermediate data
        """

        with PreprocessingContext(self.work_dir) as work_dir:
            preprocessor = DoPHOTPreprocessor(self.config)

            # Extract image data
            image = calexp.image.array
            variance = calexp.variance.array if calexp.variance else None
            mask = calexp.mask.array if calexp.mask else None
            header = calexp.getMetadata()

            # Run preprocessing
            result = preprocessor.run(
                image=image,
                variance=variance,
                mask=mask,
                header=header,
                work_dir=work_dir,
            )

            self.log.info(f"✓ Preprocessing complete: sigma={result.sigma:.3f} pixels")
            return result

    def _run_dophot(self, preprocessing_result) -> tuple[Any, ConversionFactors]:
        """
        Execute DoPHOT photometry on preprocessed image.

        Parameters
        ----------
        preprocessing_result : PreprocessingResult
            Complete preprocessing output

        Returns
        -------
        catalog : astropy.table.Table
            DoPHOT source catalog with fluxes in original units
        conversion_factors : ConversionFactors
            Conversion factors for unit tracking
        """
        import shutil

        self.log.info("Running DoPHOT photometry")

        # Check if DoPHOT executable exists
        exec_path = self.config.doPHOTExecPath
        if shutil.which(exec_path) is None:
            self.log.warning(f"DoPHOT executable not found: {exec_path}")
            self.log.warning("Returning empty catalog (DoPHOT not available)")
            return Table(), ConversionFactors(
                units=preprocessing_result.units,
                factor=preprocessing_result.conversion_factor,
                description="DoPHOT executable not found",
            )

        try:
            # Write intermediate I*4 FITS file
            intermediate_fits = Path(self.work_dir) / "intermediate_i4.fits"
            self.log.info(f"Writing intermediate I*4 FITS: {intermediate_fits}")

            primary_hdu = fits.PrimaryHDU(
                preprocessing_result.image_with_psf.astype("int32")
            )
            primary_hdu.header["BUNIT"] = "I4_INT"
            primary_hdu.header["UNITCONV"] = preprocessing_result.conversion_factor
            primary_hdu.header["ORIGUNIT"] = preprocessing_result.units
            primary_hdu.header["SIGMA"] = preprocessing_result.sigma
            primary_hdu.header["PSFCENX"] = preprocessing_result.psfcenx
            primary_hdu.header["PSFCENY"] = preprocessing_result.psfceny
            primary_hdu.header["PSFCENZ"] = preprocessing_result.psfcenz

            hdul = fits.HDUList([primary_hdu])
            hdul.writeto(str(intermediate_fits), overwrite=True)
            self.log.info("✓ Intermediate I*4 FITS written")

            # Execute DoPHOT
            self.log.info("Executing DoPHOT on intermediate I*4 image")
            executor = DoPHOTExecutor(self.config)
            catalog = executor.run(
                image_path=intermediate_fits,
                param_file=preprocessing_result.param_file,
                output_dir=self.work_dir,
                conversion_factor=preprocessing_result.conversion_factor,
                original_units=preprocessing_result.units,
            )

            self.log.info(f"✓ DoPHOT complete: {len(catalog)} sources detected")

            # Create conversion factors record
            conversion_factors = ConversionFactors(
                units=preprocessing_result.units,
                factor=preprocessing_result.conversion_factor,
                description=f"{preprocessing_result.units} = int32 * {preprocessing_result.conversion_factor:.6f}",
            )

            return catalog, conversion_factors

        except (ValueError, RuntimeError, FileNotFoundError) as e:
            self.log.error(f"DoPHOT execution failed: {e}")
            import traceback
            traceback.print_exc()
            return Table(), ConversionFactors(
                units=preprocessing_result.units,
                factor=1.0,
                description="error",
            )

    def _postprocessing(
        self,
        calexp: "ExposureF",
        catalog: Any,
        photoCalib: "PhotoCalib",
        conversion_factors: ConversionFactors | None = None
    ) -> Any:
        """
        Postprocess DoPHOT output.

        Convert photometry from int32 back to original units (nJy),
        apply aperture corrections, WCS transformation, magnitude conversion.

        Parameters
        ----------
        calexp : lsst.afw.image.ExposureF
            Calibrated exposure
        catalog : astropy.table.Table
            DoPHOT source catalog (in int32 units)
        photoCalib : lsst.afw.image.PhotoCalib
            Photometric calibration
        conversion_factors : dict, optional
            Conversion factors from preprocessing

        Returns
        -------
        src : lsst.afw.table.SourceCatalog
            Rubin SourceCatalog with photometry in nJy
        """
        from .postprocess import create_source_catalog

        # Step 1: Convert photometry back to original units
        if conversion_factors and len(catalog) > 0:
            factor = conversion_factors.factor
            units = conversion_factors.units

            self.log.info(
                f"Converting photometry from int32 to {units} "
                f"using factor {factor:.6f}"
            )

            # Typical DoPHOT output columns that need conversion
            photometry_cols = ["flux", "flux_err", "peak", "background"]

            for col in photometry_cols:
                if col in catalog.colnames:
                    catalog[col] *= factor
                    if "_err" in col or "err" in col:
                        # Error columns scale linearly with factor
                        pass

        postprocessor = DoPHOTPostprocessor(self.config)

        # Step 2: Run postprocessing (aperture corrections, WCS, etc.)
        catalog_out = postprocessor.run(
            catalog,
            calexp=calexp,
            psf=calexp.getPsf() if calexp else None,
            photoCalib=photoCalib
        )

        # Step 3: Convert to SourceCatalog
        if HAS_RUBIN_STACK:
            src = create_source_catalog(catalog_out, self.config)
        else:
            # Fallback for development
            src = catalog_out

        self.log.info("✓ Postprocessing complete")
        return src
