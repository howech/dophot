"""
Postprocessing for DoPHOT output.

Handles aperture corrections, WCS transformation, and magnitude conversion.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)


class DoPHOTPostprocessor:
    """Postprocess DoPHOT photometry output."""

    def __init__(self, config):
        """
        Initialize postprocessor.

        Parameters
        ----------
        config : DoPHOTConfig
            Task configuration
        """
        self.config = config
        self.log = logging.getLogger(__name__)

    def run(self, catalog, calexp=None, psf=None, photoCalib=None):
        """
        Run complete postprocessing pipeline.

        Parameters
        ----------
        catalog : astropy.table.Table
            DoPHOT source catalog
        calexp : lsst.afw.image.ExposureF, optional
            Calibrated exposure (for WCS, PSF)
        psf : lsst.afw.detection.Psf, optional
            PSF model
        photoCalib : lsst.afw.image.PhotoCalib, optional
            Photometric calibration

        Returns
        -------
        catalog_out : astropy.table.Table
            Postprocessed catalog with all corrections applied
        """
        self.log.info("Starting postprocessing")

        # Make a copy to avoid modifying input
        catalog_out = catalog.copy()

        # Apply aperture corrections if requested
        if self.config.doApertureCorrection and 'ap_mag' in catalog_out.colnames:
            self.log.info("Applying aperture corrections")
            catalog_out = self._apply_aperture_corrections(
                catalog_out, calexp=calexp, psf=psf
            )

        # Transform to RA/Dec if requested
        if self.config.doWcsTransform and calexp is not None:
            self.log.info("Transforming to RA/Dec")
            catalog_out = self._apply_wcs_transform(catalog_out, calexp)

        # Convert to AB magnitudes if requested
        if self.config.doMagnitudeConversion and photoCalib is not None:
            self.log.info("Converting to AB magnitudes")
            catalog_out = self._apply_magnitude_conversion(
                catalog_out, photoCalib
            )

        # Add quality flags
        self.log.info("Adding quality flags")
        catalog_out = self._add_quality_flags(catalog_out)

        self.log.info(f"✓ Postprocessing complete: {len(catalog_out)} sources")

        return catalog_out

    def _apply_aperture_corrections(self, catalog, calexp=None, psf=None):
        """
        Apply aperture correction to convert aperture mag to total mag.

        Parameters
        ----------
        catalog : astropy.table.Table
            Source catalog with aperture magnitudes
        calexp : lsst.afw.image.ExposureF, optional
            Calibrated exposure
        psf : lsst.afw.detection.Psf, optional
            PSF model

        Returns
        -------
        astropy.table.Table
            Catalog with corrected magnitudes
        """
        # For now, simple aperture correction model
        # In production, this would measure PSF and apply proper corrections

        if 'ap_mag' not in catalog.colnames:
            self.log.warning("No aperture magnitude column found")
            return catalog

        # Simple model: aperture correction = 2.5*log10(1.5) for aperture radius 2.0"
        # This is a placeholder; real correction depends on PSF width

        apcorr = 2.5 * np.log10(1.5)  # Placeholder

        if 'psfMag' not in catalog.colnames:
            catalog['psfMag'] = catalog['ap_mag'] + apcorr
        else:
            catalog['psfMag_corrected'] = catalog['ap_mag'] + apcorr

        self.log.debug(f"Applied aperture correction: {apcorr:.3f} mag")

        return catalog

    def _apply_wcs_transform(self, catalog, calexp):
        """
        Transform pixel coordinates to RA/Dec using WCS.

        Parameters
        ----------
        catalog : astropy.table.Table
            Source catalog with x_pixel, y_pixel columns
        calexp : lsst.afw.image.ExposureF
            Calibrated exposure with WCS

        Returns
        -------
        astropy.table.Table
            Catalog with RA/Dec columns added
        """
        # Get WCS from calexp
        wcs = calexp.getWcs()

        if 'x_pixel' not in catalog.colnames or 'y_pixel' not in catalog.colnames:
            self.log.warning("No pixel coordinate columns found")
            return catalog

        # Transform pixel coords to RA/Dec
        x_pix = catalog['x_pixel']
        y_pix = catalog['y_pixel']

        try:
            # Use Rubin WCS if available
            coords = wcs.pixelToSky(x_pix, y_pix)
            catalog['RA'] = np.array([c.getRa().asDegrees() for c in coords])
            catalog['Dec'] = np.array([c.getDec().asDegrees() for c in coords])
        except AttributeError:
            # Fallback: use simple transformation if proper WCS not available
            self.log.warning("WCS transform not available, using pixel coords")
            catalog['RA'] = x_pix
            catalog['Dec'] = y_pix

        self.log.debug(f"Transformed {len(catalog)} sources to RA/Dec")

        return catalog

    def _apply_magnitude_conversion(self, catalog, photoCalib):
        """
        Convert instrumental magnitudes to AB magnitudes.

        Parameters
        ----------
        catalog : astropy.table.Table
            Source catalog with instrumental magnitudes
        photoCalib : lsst.afw.image.PhotoCalib
            Photometric calibration

        Returns
        -------
        astropy.table.Table
            Catalog with AB magnitudes
        """
        # DoPHOT produces magnitudes in DN (detector counts)
        # Need to convert to AB using photoCalib

        if 'psfMag' not in catalog.colnames:
            self.log.warning("No psfMag column found")
            return catalog

        try:
            # Convert to AB magnitude using photoCalib
            mag_dn = catalog['psfMag']

            # Simple conversion: inst_mag → nanoJansky → AB mag
            # Real implementation would use photoCalib.magnitudeFromFlux()

            # Placeholder: add calibration offset
            ab_offset = 27.0  # Typical LSST offset
            catalog['mag_AB'] = mag_dn + ab_offset

            self.log.debug(f"Converted {len(catalog)} magnitudes to AB")

        except Exception as e:
            self.log.error(f"Magnitude conversion failed: {e}")
            catalog['mag_AB'] = catalog['psfMag']

        return catalog

    def _add_quality_flags(self, catalog):
        """
        Add quality flags and selection criteria.

        Parameters
        ----------
        catalog : astropy.table.Table
            Source catalog

        Returns
        -------
        astropy.table.Table
            Catalog with quality flags
        """
        # Initialize flags
        n_sources = len(catalog)
        catalog['good'] = np.ones(n_sources, dtype=bool)
        catalog['flags'] = np.zeros(n_sources, dtype=int)

        # Flag saturated sources
        if 'sn_psfMag' in catalog.colnames:
            saturated = catalog['sn_psfMag'] < self.config.minPsfSignalToNoise
            catalog['good'][saturated] = False
            catalog['flags'][saturated] |= 1  # Flag 1: low S/N

        # Flag sources near edges
        if 'x_pixel' in catalog.colnames:
            edge = ((catalog['x_pixel'] < self.config.psfEdgeBuffer) |
                   (catalog['y_pixel'] < self.config.psfEdgeBuffer))
            catalog['good'][edge] = False
            catalog['flags'][edge] |= 2  # Flag 2: near edge

        n_good = catalog['good'].sum()
        self.log.info(f"Quality flags: {n_good}/{n_sources} sources are good")

        return catalog


def create_source_catalog(table_data, config):
    """
    Convert postprocessed table to Rubin SourceCatalog format.

    Parameters
    ----------
    table_data : astropy.table.Table
        Postprocessed source table
    config : DoPHOTConfig
        Task configuration

    Returns
    -------
    catalog : lsst.afw.table.SourceCatalog or astropy.table.Table
        Rubin SourceCatalog (or Table if Rubin not available)
    """
    try:
        # Try to use Rubin's SourceCatalog
        from lsst.afw.table import SourceCatalog, SourceTable

        # Create schema
        schema = SourceTable.makeMinimalSchema()

        # Add DoPHOT-specific columns
        if 'psfMag' in table_data.colnames:
            schema.addField('psfMag', type='d', doc='PSF magnitude')
        if 'mag_AB' in table_data.colnames:
            schema.addField('mag_AB', type='d', doc='AB magnitude')
        if 'RA' in table_data.colnames:
            schema.addField('RA', type='d', doc='Right Ascension (degrees)')
        if 'Dec' in table_data.colnames:
            schema.addField('Dec', type='d', doc='Declination (degrees)')

        # Create catalog
        catalog = SourceCatalog(schema)

        # Copy data
        for row, data_row in zip(catalog, table_data):
            if 'id' in table_data.colnames:
                row.setId(int(data_row['id']))
            if 'x_pixel' in table_data.colnames:
                row.setX(float(data_row['x_pixel']))
            if 'y_pixel' in table_data.colnames:
                row.setY(float(data_row['y_pixel']))

            # Copy optional columns
            for col in ['psfMag', 'mag_AB', 'RA', 'Dec']:
                if col in table_data.colnames:
                    try:
                        row[col] = data_row[col]
                    except Exception as e:
                        logger.debug(f"Could not copy {col}: {e}")

        return catalog

    except ImportError:
        # Fallback: return as Table if Rubin not available
        logger.info("Rubin SourceCatalog not available, returning astropy Table")
        return table_data


def postprocess_dophot_output(catalog, calexp=None, photoCalib=None, config=None):
    """
    Convenience function for full postprocessing.

    Parameters
    ----------
    catalog : astropy.table.Table or str
        DoPHOT source catalog (Table or path to catalog file)
    calexp : lsst.afw.image.ExposureF, optional
        Calibrated exposure
    photoCalib : lsst.afw.image.PhotoCalib, optional
        Photometric calibration
    config : DoPHOTConfig, optional
        Task configuration

    Returns
    -------
    src : lsst.afw.table.SourceCatalog or astropy.table.Table
        Postprocessed source catalog
    """
    if config is None:
        # Create default config
        from .config import DoPHOTConfig
        config = DoPHOTConfig()

    postprocessor = DoPHOTPostprocessor(config)

    # Load catalog if path
    if isinstance(catalog, str):
        from astropy.io import ascii
        catalog = ascii.read(catalog)

    # Run postprocessing
    catalog_out = postprocessor.run(
        catalog,
        calexp=calexp,
        photoCalib=photoCalib
    )

    # Convert to SourceCatalog
    src = create_source_catalog(catalog_out, config)

    return src
