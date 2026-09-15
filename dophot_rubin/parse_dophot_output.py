"""
Parse DoPHOT output catalog and convert back to original units.
"""

from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
from astropy.table import Table


class DoPHOTSource(NamedTuple):
    """A single DoPHOT source measurement."""
    id: np.int_
    type: np.int_
    sky: np.floating[Any]
    x: np.floating[Any]
    y: np.floating[Any]
    flux: np.floating[Any]
    psf_a: np.floating[Any]
    psf_b: np.floating[Any]
    psf_elong: np.floating[Any]
    psf_pa: np.floating[Any]
    chi2_a: np.floating[Any]
    chi2_b: np.floating[Any]




def parse_obj_out(filepath: str) -> list[DoPHOTSource]:
    """
    Parse DoPHOT obj_out file format.

    DoPHOT outputs space-separated columns:
    ID TYPE SKY X Y FLUX PSF_A PSF_B PSF_ELONGATION PSF_PA CHI2_A CHI2_B
    SHARPNESS EXTRAS...

    Returns a list of DoPHOTSource objects.
    """
    data = np.loadtxt(filepath)

    if data.ndim == 1:
        # Single source
        data = data.reshape(1, -1)

    # Create DoPHOTSource object for each row
    sources = []
    for row in data:
        source = DoPHOTSource(
            id=np.int_(row[0]),
            type=np.int_(row[1]),
            sky=np.floating(row[2]),
            x=np.floating(row[3]),
            y=np.floating(row[4]),
            flux=np.floating(row[5]),  # In int32 units
            psf_a=np.floating(row[6]),
            psf_b=np.floating(row[7]),
            psf_elong=np.floating(row[8]),
            psf_pa=np.floating(row[9]),
            chi2_a=np.floating(row[10]) if len(row) > 10 else np.floating(0),
            chi2_b=np.floating(row[11]) if len(row) > 11 else np.floating(0),
        )
        sources.append(source)

    return sources


def convert_to_original_units(
    sources: list[DoPHOTSource],
    conversion_factor: float,
    original_units: str = 'DN'
) -> Table:
    """
    Convert DoPHOT flux from int32 back to original units.

    Parameters
    ----------
    sources : list[DoPHOTSource]
        Source list from parse_obj_out()
    conversion_factor : float
        Scale factor (DN/int32 or nJy/int32)
    original_units : str
        Original units ('DN' or 'nJy')

    Returns
    -------
    catalog : astropy.table.Table
        Source catalog in original units
    """
    # Convert each source and collect into columns
    catalog_data = {
        'id': [s.id for s in sources],
        'type': [s.type for s in sources],
        'x': [s.x for s in sources],
        'y': [s.y for s in sources],
        'flux': [s.flux * conversion_factor for s in sources],
        'flux_dn': [s.flux for s in sources],  # Keep int32 values for reference
        'sky': [s.sky * conversion_factor for s in sources],
        'psf_a': [s.psf_a for s in sources],
        'psf_b': [s.psf_b for s in sources],
        'psf_elong': [s.psf_elong for s in sources],
        'psf_pa': [s.psf_pa for s in sources],
        'chi2_a': [s.chi2_a for s in sources],
        'chi2_b': [s.chi2_b for s in sources],
    }

    # Create output table
    catalog = Table(catalog_data)

    # Add units to columns
    catalog['flux'].unit = original_units
    catalog['sky'].unit = original_units

    return catalog


def validate_photometry(
    catalog_dn: Table,
    catalog_original: Table,
    conversion_factor: float,
    tolerance: float = 0.01
) -> dict[str, Any]:
    """
    Validate round-trip conversion: DN -> int32 -> DN.

    Parameters
    ----------
    catalog_dn : astropy.table.Table
        Original DN catalog
    catalog_original : astropy.table.Table
        Converted back to DN catalog
    conversion_factor : float
        Conversion factor used
    tolerance : float
        Acceptable error fraction (default 1%)

    Returns
    -------
    stats : dict
        Validation statistics
    """
    flux_diff = np.abs(catalog_dn['flux'] - catalog_original['flux'])
    flux_frac_err = flux_diff / (np.abs(catalog_dn['flux']) + 1e-10)

    good = flux_frac_err < tolerance
    bad = flux_frac_err >= tolerance

    stats = {
        'n_total': len(catalog_dn),
        'n_good': np.sum(good),
        'n_bad': np.sum(bad),
        'max_error_fraction': np.max(flux_frac_err),
        'mean_error_fraction': np.mean(flux_frac_err),
        'conversion_factor': conversion_factor,
    }

    return stats


if __name__ == '__main__':
    # Test on DoPHOT output
    obj_file = Path('/tmp/dophot_final_test2/obj_out_intermediate_i4')

    print("Parsing DoPHOT output...")
    sources = parse_obj_out(obj_file)

    print(f"Found {len(sources)} sources")
    flux_values = np.array([s.flux for s in sources])
    flux_min = flux_values.min()
    flux_max = flux_values.max()
    print(f"Flux range (int32): {flux_min:.0f} to {flux_max:.0f}")

    # Convert back to DN
    conversion_factor = 11.8496  # DN/int32
    catalog = convert_to_original_units(sources, conversion_factor, 'DN')

    flux_min = catalog['flux'].min()
    flux_max = catalog['flux'].max()
    sky_min = catalog['sky'].min()
    sky_max = catalog['sky'].max()
    print(f"\nFlux range (DN): {flux_min:.2f} to {flux_max:.2f}")
    print(f"Sky range (DN): {sky_min:.2f} to {sky_max:.2f}")

    print("\nTop 10 brightest sources:")
    sorted_cat = catalog[np.argsort(-catalog['flux'])[:10]]
    for row in sorted_cat:
        print(f"  ID {row['id']:3d}: flux={row['flux']:10.2f} DN, "
              f"x={row['x']:7.2f}, y={row['y']:7.2f}, type={row['type']}")

    print("\nCatalog written to /tmp/dophot_catalog.fits")
    catalog.write('/tmp/dophot_catalog.fits', overwrite=True)
