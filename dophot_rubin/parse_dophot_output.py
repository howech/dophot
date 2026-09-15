"""
Parse DoPHOT output catalog and convert back to original units.
"""

from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
from astropy.table import Table
from numpy.typing import NDArray


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


class DoPHOTSources(NamedTuple):
    """Parsed DoPHOT source catalog from obj_out file (columnar format)."""
    id: NDArray[np.int_]
    type: NDArray[np.int_]
    sky: NDArray[np.floating[Any]]
    x: NDArray[np.floating[Any]]
    y: NDArray[np.floating[Any]]
    flux: NDArray[np.floating[Any]]
    psf_a: NDArray[np.floating[Any]]
    psf_b: NDArray[np.floating[Any]]
    psf_elong: NDArray[np.floating[Any]]
    psf_pa: NDArray[np.floating[Any]]
    chi2_a: NDArray[np.floating[Any]]
    chi2_b: NDArray[np.floating[Any]]


def parse_obj_out(filepath: str) -> DoPHOTSources:
    """
    Parse DoPHOT obj_out file format.

    DoPHOT outputs space-separated columns:
    ID TYPE SKY X Y FLUX PSF_A PSF_B PSF_ELONGATION PSF_PA CHI2_A CHI2_B
    SHARPNESS EXTRAS...

    Returns a dict with source data.
    """
    data = np.loadtxt(filepath)

    if data.ndim == 1:
        # Single source
        data = data.reshape(1, -1)

    # Extract columns (based on DoPHOT output format)
    return DoPHOTSources(
        id=data[:, 0].astype(int),
        type=data[:, 1].astype(int),
        sky=data[:, 2],
        x=data[:, 3],
        y=data[:, 4],
        flux=data[:, 5],  # In int32 units
        psf_a=data[:, 6],
        psf_b=data[:, 7],
        psf_elong=data[:, 8],
        psf_pa=data[:, 9],
        chi2_a=data[:, 10] if data.shape[1] > 10 else np.zeros(len(data)),
        chi2_b=data[:, 11] if data.shape[1] > 11 else np.zeros(len(data)),
    )


def convert_to_original_units(
    sources: DoPHOTSources,
    conversion_factor: float,
    original_units: str = 'DN'
) -> Table:
    """
    Convert DoPHOT flux from int32 back to original units.

    Parameters
    ----------
    sources : DoPHOTSources
        Source data from parse_obj_out()
    conversion_factor : float
        Scale factor (DN/int32 or nJy/int32)
    original_units : str
        Original units ('DN' or 'nJy')

    Returns
    -------
    catalog : astropy.table.Table
        Source catalog in original units
    """
    # Convert flux and sky from int32 to original units
    flux_original = sources.flux * conversion_factor
    sky_original = sources.sky * conversion_factor

    # Create output table
    catalog = Table({
        'id': sources.id,
        'type': sources.type,
        'x': sources.x,
        'y': sources.y,
        'flux': flux_original,
        'flux_dn': sources.flux,  # Also keep int32 values for reference
        'sky': sky_original,
        'psf_a': sources.psf_a,
        'psf_b': sources.psf_b,
        'psf_elong': sources.psf_elong,
        'psf_pa': sources.psf_pa,
        'chi2_a': sources.chi2_a,
        'chi2_b': sources.chi2_b,
    })

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

    print(f"Found {len(sources.id)} sources")
    flux_min = sources.flux.min()
    flux_max = sources.flux.max()
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
