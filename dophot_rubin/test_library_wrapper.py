"""
Ctypes skeleton for DoPHOT library bindings.

This shows how Python would call the dophot_photometry() C function
via ctypes, passing numpy arrays and getting structured results.

This is NOT functional yet - it's a design blueprint for Phase 2.
"""

import ctypes
import numpy as np
from pathlib import Path
from typing import Optional, Tuple

# ============================================================================
# Ctypes Structure Definitions (mirror of dophot_library.h)
# ============================================================================

class DoPHOTParams(ctypes.Structure):
    """Input parameters for DoPHOT photometry."""
    _fields_ = [
        ("sigma", ctypes.c_float),
        ("fwhm", ctypes.c_float),
        ("sky_value", ctypes.c_float),
        ("gain", ctypes.c_float),
        ("rdnoise", ctypes.c_float),
        ("saturation", ctypes.c_float),
        ("nthpix", ctypes.c_int),
        ("nfit", ctypes.c_int),
        ("model", ctypes.c_int),  # enum: 0=PGAUSS, 1=GAUSS, 2=EXTPGAUSS
    ]


class DoPHOTResults(ctypes.Structure):
    """Output results from DoPHOT photometry."""
    _fields_ = [
        ("n_stars", ctypes.c_int),
        ("x", ctypes.POINTER(ctypes.c_float)),
        ("y", ctypes.POINTER(ctypes.c_float)),
        ("mag", ctypes.POINTER(ctypes.c_float)),
        ("err", ctypes.POINTER(ctypes.c_float)),
        ("starpar", ctypes.POINTER(ctypes.POINTER(ctypes.c_float))),
        ("shadow", ctypes.POINTER(ctypes.POINTER(ctypes.c_float))),
        ("shaderr", ctypes.POINTER(ctypes.POINTER(ctypes.c_float))),
        ("imtype", ctypes.POINTER(ctypes.c_int)),
        ("max_stars", ctypes.c_int),
    ]


# ============================================================================
# Library Loader & Function Binding
# ============================================================================

class DoPHOTLibrary:
    """Wrapper for DoPHOT C library via ctypes."""

    def __init__(self, libpath: Optional[str] = None):
        """Load DoPHOT library.

        Args:
            libpath: Path to libdophot.so. If None, searches standard locations.
        """
        if libpath is None:
            # Try to find in package
            libpath = str(Path(__file__).parent / "dophot_c" / "libdophot.so")

        self.lib = ctypes.CDLL(libpath)

        # Define function signature
        self.dophot_photometry = self.lib.dophot_photometry
        self.dophot_photometry.argtypes = [
            ctypes.POINTER(ctypes.POINTER(ctypes.c_int32)),  # image
            ctypes.POINTER(ctypes.POINTER(ctypes.c_int32)),  # noise
            ctypes.c_int,                                     # nx
            ctypes.c_int,                                     # ny
            ctypes.POINTER(DoPHOTParams),                    # params
            ctypes.POINTER(DoPHOTResults),                   # results
        ]
        self.dophot_photometry.restype = ctypes.c_int

    def run(
        self,
        image: np.ndarray,
        noise: np.ndarray,
        params: DoPHOTParams,
    ) -> Tuple[int, DoPHOTResults]:
        """Execute DoPHOT photometry on image.

        Args:
            image: int32 numpy array [ny, nx]
            noise: int32 numpy array [ny, nx]
            params: DoPHOTParams struct with photometry parameters

        Returns:
            Tuple of (return_code, results)
            return_code: 0 on success, nonzero on error
            results: DoPHOTResults struct with star catalog
        """
        # Validate input
        if image.dtype != np.int32 or noise.dtype != np.int32:
            raise ValueError("Image and noise must be int32")

        if image.shape != noise.shape:
            raise ValueError("Image and noise must have same shape")

        ny, nx = image.shape

        # Convert numpy arrays to C pointers
        # ctypes needs array pointers: create pointers to row pointers
        image_ptr = image.ctypes.data_as(ctypes.POINTER(ctypes.c_int32))
        noise_ptr = noise.ctypes.data_as(ctypes.POINTER(ctypes.c_int32))

        # Create a "2D pointer" - this is tricky, would need helper function
        # For now, this is pseudocode showing the intent:
        # image_2d_ptr = [pointer to row 0, pointer to row 1, ...]
        # noise_2d_ptr = [pointer to row 0, pointer to row 1, ...]

        # TODO: Implement array_to_2d_ptr() helper
        # image_2d_ptr = self._array_to_2d_ptr(image)
        # noise_2d_ptr = self._array_to_2d_ptr(noise)

        # Allocate output struct
        results = DoPHOTResults()

        # Call C function
        # retcode = self.dophot_photometry(
        #     image_2d_ptr,
        #     noise_2d_ptr,
        #     nx,
        #     ny,
        #     ctypes.byref(params),
        #     ctypes.byref(results),
        # )

        # return retcode, results

        raise NotImplementedError("Full ctypes binding not yet implemented")

    @staticmethod
    def _array_to_2d_ptr(arr: np.ndarray) -> ctypes.POINTER(ctypes.POINTER(ctypes.c_int32)):
        """Convert numpy 2D array to C 2D pointer array.

        This is a non-trivial operation:
        - Need to create array of row pointers
        - Each row pointer points to that row in the numpy array
        - Must manage lifetime carefully
        """
        ny, nx = arr.shape
        row_ptrs = (ctypes.POINTER(ctypes.c_int32) * ny)()

        for i in range(ny):
            row_ptrs[i] = arr[i, :].ctypes.data_as(ctypes.POINTER(ctypes.c_int32))

        return row_ptrs


# ============================================================================
# Example Usage (pseudocode - would work once library is built)
# ============================================================================

def example_usage():
    """Demonstrate how Python would use DoPHOT library.

    This is example/documentation code, not runnable yet.
    """
    # Load library
    lib = DoPHOTLibrary()

    # Create dummy image
    image = np.ones((512, 512), dtype=np.int32) * 1000
    noise = np.ones((512, 512), dtype=np.int32) * 30

    # Set parameters
    params = DoPHOTParams(
        sigma=2.0,
        fwhm=4.7,
        sky_value=1000.0,
        gain=1.0,
        rdnoise=15.0,
        saturation=60000,
        nthpix=20,
        nfit=3,
        model=0,  # PGAUSS
    )

    # Run photometry
    retcode, results = lib.run(image, noise, params)

    # Extract results
    if retcode == 0:
        print(f"Found {results.n_stars} stars")

        # Access star positions from starpar matrix
        for i in range(min(5, results.n_stars)):
            x = results.starpar[i][0]
            y = results.starpar[i][1]
            flux = results.starpar[i][2]
            mag = results.starpar[i][3]
            print(f"  Star {i}: ({x:.1f}, {y:.1f}) mag={mag:.2f}")
    else:
        print(f"Error: return code {retcode}")


if __name__ == "__main__":
    print(__doc__)
    print("\nThis is a design blueprint for ctypes bindings.")
    print("Run after libdophot.so is built in Phase 2.")
