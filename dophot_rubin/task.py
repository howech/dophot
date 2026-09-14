"""
DoPHOT PipelineTask for Rubin Observatory.

Orchestrates PSF-based photometry using DoPHOT on calibrated visit images.
"""

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, NamedTuple, Optional, Tuple

from .config import DoPHOTConfig

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
        def __init__(self, config: DoPHOTConfig, name: Optional[str] = None) -> None:
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

from .config import DoPHOTConfig
from .execute_dophot import DoPHOTExecutor
from .image_scaling import (
    apply_mask_to_scaled_image,
    detect_units,
    scale_image_to_int32,
)
from .postprocess import DoPHOTPostprocessor
from .preprocess_wrapper import DoPHOTPreprocessor, PreprocessingContext
from .psf_measurement import (
    append_psf_to_image,
    generate_parameter_file,
    measure_psf_simple,
)

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
    pass


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
        name: Optional[str] = None,
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
            sigma, params = self._preprocessing(calexp)

            # Run DoPHOT
            catalog, conversion_factors = self._run_dophot(calexp, params)

            # Run postprocessing
            src = self._postprocessing(calexp, catalog, photoCalib, conversion_factors)

            # Write outputs
            butlerQC.put(src, outputRefs.src)

            self.log.info(f"DoPHOT completed: {len(src)} sources detected")

        except Exception as e:
            self.log.error(f"DoPHOT failed: {e}")
            raise

    def _preprocessing(self, calexp: "ExposureF") -> Tuple[float, Dict[str, Any]]:
        """
        Measure PSF and generate DoPHOT parameters.

        Parameters
        ----------
        calexp : lsst.afw.image.ExposureF
            Calibrated exposure

        Returns
        -------
        sigma : float
            Measured PSF width (pixels)
        params : dict
            DoPHOT tuning parameters
        """
        with PreprocessingContext(self.work_dir) as work_dir:
            preprocessor = DoPHOTPreprocessor(self.config)

            # Extract image data
            image = calexp.image.array
            variance = calexp.variance.array if calexp.variance else None
            mask = calexp.mask.array if calexp.mask else None
            header = calexp.getMetadata()

            # Run preprocessing
            sigma, params, metadata = preprocessor.run(
                image=image,
                variance=variance,
                mask=mask,
                header=header,
                work_dir=work_dir
            )

            self.log.info(f"✓ Preprocessing complete: sigma={sigma:.3f} pixels")
            return sigma, params

    def _run_dophot(
        self,
        calexp: "ExposureF",
        params: Any,
    ) -> Tuple[Any, ConversionFactors]:
        """
        Execute DoPHOT photometry using IDL-style workflow.

        Following the IDL approach:
        1. Detect image units (DN or nJy)
        2. Scale to int32 intermediate with conversion factor tracking
        3. Write intermediate I*4 FITS file
        4. Run DoPHOT on intermediate I*4
        5. Read DoPHOT output
        6. Convert results back to original units
        7. Clean up intermediate files

        Parameters
        ----------
        calexp : lsst.afw.image.ExposureF
            Calibrated exposure
        params : dict
            DoPHOT tuning parameters

        Returns
        -------
        catalog : astropy.table.Table
            DoPHOT source catalog
        conversion_factors : dict
            Conversion factors (units -> int32 scale -> back to units)
        """
        import shutil

        from astropy.io import fits
        from astropy.table import Table
        from dophot_preprocess import param_file_writer

        self.log.info("Running DoPHOT photometry (IDL-style workflow)")

        # Get image data
        image = calexp.image.array
        header = calexp.getMetadata()

        # Detect units
        units = detect_units(header)
        self.log.info(f"Image units: {units}")

        # Write temporary parameter file
        with tempfile.TemporaryDirectory(dir=self.work_dir) as tmpdir:
            tmpdir = Path(tmpdir)
            param_file = tmpdir / "dophot.param"
            param_file_writer.write_param_file(str(param_file), params, verbose=False)
            self.log.debug(f"Parameter file: {param_file}")

            # Check if DoPHOT executable exists
            exec_path = self.config.doPHOTExecPath
            if shutil.which(exec_path) is None:
                self.log.warning(f"DoPHOT executable not found: {exec_path}")
                self.log.warning("Returning empty catalog (DoPHOT not available)")
                return Table(), {}

            try:
                # Get mask and variance before scaling (for sky_gain calculation)
                mask = calexp.mask.array if calexp.mask else None
                variance = calexp.variance.array if calexp.variance else None

                # Step 1: Scale image to int32 (excluding masked pixels)
                self.log.info("Scaling image to int32 intermediate representation")
                image_int32, conversion_factor, scale_metadata = scale_image_to_int32(
                    image,
                    units,
                    header=header,
                    mask=mask,
                    variance=variance,
                )
                self.log.info(f"Scale metadata: mprec={scale_metadata.get('mprec')}, "
                             f"epdn={scale_metadata.get('epdn'):.4f}")

                # Step 1b: Apply mask to scaled image (set bad pixels to sentinel)
                if mask is not None:
                    self.log.info("Applying mask to scaled image")
                    image_int32 = apply_mask_to_scaled_image(image_int32, mask)

                # Step 2: Measure PSF from image
                self.log.info("Measuring PSF from image")
                sigma, beta4, beta6, beta8 = measure_psf_simple(image_int32, mask=mask)
                self.log.info(f"PSF measured: sigma={sigma:.2f}, beta4={beta4:.2f}")

                # Step 3: Generate parameter file
                param_file = tmpdir / "dophot_params.txt"
                # Get saturation value from header or use 65535 as default
                saturation = float(header.get('SATURATE', 65535.0))
                self.log.info(f"Generating parameter file: {param_file}")
                params = generate_parameter_file(
                    str(param_file),
                    sigma=sigma,
                    beta4=beta4,
                    beta6=beta6,
                    beta8=beta8,
                    skyval=scale_metadata.get('skyval', 0),
                    epdn=scale_metadata.get('epdn', 1.0),
                    fpdn=1.0 / scale_metadata.get('gain', 1.0),
                    gain=scale_metadata.get('gain', 1.0),
                    saturation=saturation,
                    mprec=scale_metadata.get('mprec', 2),
                    image_shape=image_int32.shape,
                    mask=mask
                )

                # Step 4: Append PSF to image for DoPHOT input
                self.log.info("Appending PSF to image")
                image_with_psf, psfcenx, psfceny, psfcenz = append_psf_to_image(
                    image_int32, image_int32  # Use simplified PSF for now
                )

                # Step 6: Write intermediate I*4 FITS file (DoPHOT-compatible format)
                # DoPHOT requires simple FITS with 2D data in primary HDU, no extensions
                intermediate_fits = tmpdir / "intermediate_i4.fits"
                self.log.info(f"Writing intermediate I*4 FITS: {intermediate_fits}")

                # Create primary HDU with int32 image data
                primary_hdu = fits.PrimaryHDU(image_with_psf.astype('int32'))

                # Store all metadata in primary header
                primary_hdu.header['BUNIT'] = 'I4_INT'
                primary_hdu.header['UNITCONV'] = conversion_factor
                primary_hdu.header['ORIGUNIT'] = units
                # PSF parameters
                primary_hdu.header['SIGMA'] = sigma
                primary_hdu.header['BETA4'] = beta4
                primary_hdu.header['BETA6'] = beta6
                primary_hdu.header['BETA8'] = beta8
                primary_hdu.header['PSFCENX'] = psfcenx
                primary_hdu.header['PSFCENY'] = psfceny
                primary_hdu.header['PSFCENZ'] = psfcenz
                # Scaling parameters
                primary_hdu.header['EPDN'] = scale_metadata.get('epdn', 1.0)
                primary_hdu.header['MPREC'] = scale_metadata.get('mprec', 2)
                primary_hdu.header['SATVAL'] = saturation if saturation else 65535

                # Write single-HDU FITS file (DoPHOT compatible)
                hdul = fits.HDUList([primary_hdu])
                hdul.writeto(str(intermediate_fits), overwrite=True)
                self.log.info(
                    "✓ Intermediate I*4 FITS written (DoPHOT-compatible format)"
                )

                # Step 7: Run DoPHOT on intermediate I*4
                self.log.info("Executing DoPHOT on intermediate I*4 image")
                executor = DoPHOTExecutor(self.config)
                catalog = executor.run(
                    image_path=intermediate_fits,
                    param_file=param_file,
                    output_dir=tmpdir
                )

                self.log.info(f"✓ DoPHOT complete: {len(catalog)} sources detected")

                # Step 4: Convert results back to original units
                # (This would be done by postprocessing based on the conversion factor)
                conversion_factors = ConversionFactors(
                    units=units,
                    factor=conversion_factor,
                    description=f'{units} = int32 * {conversion_factor:.6f}'
                )

                msg = (
                    f"Conversion factor for postprocessing: "
                    f"{conversion_factor:.6f} {units}/int32"
                )
                self.log.info(msg)

                return catalog, conversion_factors

            except Exception as e:
                self.log.error(f"DoPHOT execution failed: {e}")
                import traceback
                traceback.print_exc()
                return Table(), ConversionFactors(units='unknown', factor=1.0, description='error')

    def _postprocessing(
        self,
        calexp: "ExposureF",
        catalog: Any,
        photoCalib: "PhotoCalib",
        conversion_factors: Optional[ConversionFactors] = None
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

        # Step 1: Convert photometry back to original units if we have conversion factors
        if conversion_factors and len(catalog) > 0:
            factor = conversion_factors.get('factor', 1.0)
            units = conversion_factors.get('units', 'unknown')

            self.log.info(f"Converting photometry from int32 to {units} "
                         f"using factor {factor:.6f}")

            # Typical DoPHOT output columns that need conversion
            photometry_cols = ['flux', 'flux_err', 'peak', 'background']

            for col in photometry_cols:
                if col in catalog.colnames:
                    catalog[col] *= factor
                    if '_err' in col or 'err' in col:
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
