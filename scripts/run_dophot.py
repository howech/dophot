"""
Run DoPHOT PSF photometry on a FITS image.

Usage:
    python scripts/run_dophot.py input.fits [-o catalog.ecsv] [--workdir DIR]
                                            [--dophot PATH]

The DoPHOT executable must be built first:
    cd dophot_rubin/dophot_c && make dophot
"""

import argparse
import logging
import sys
from pathlib import Path

from astropy.io import fits

from dophot_rubin import DoPHOTConfig, DoPHOTExecutor, DoPHOTPreprocessor

log = logging.getLogger("run_dophot")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path, help="Input FITS image")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output catalog path (.ecsv or .fits). Default: <input>_dophot.ecsv",
    )
    parser.add_argument(
        "--workdir", type=Path,
        help="Directory for intermediate and DoPHOT files. Default: <input>_dophot_work",
    )
    parser.add_argument(
        "--dophot", type=str,
        help="Path to the DoPHOT executable. Default: the one built in dophot_rubin/dophot_c",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not args.input.exists():
        log.error(f"Input image not found: {args.input}")
        return 1

    output = args.output or args.input.with_name(f"{args.input.stem}_dophot.ecsv")
    workdir = args.workdir or args.input.with_name(f"{args.input.stem}_dophot_work")

    config = DoPHOTConfig()
    if args.dophot:
        config.doPHOTExecPath = args.dophot
    if not Path(config.doPHOTExecPath).exists():
        log.error(
            f"DoPHOT executable not found: {config.doPHOTExecPath}\n"
            "Build it with: cd dophot_rubin/dophot_c && make dophot"
        )
        return 1

    with fits.open(args.input) as hdul:
        image = hdul[0].data.astype("float32")
        header = dict(hdul[0].header)

    workdir.mkdir(parents=True, exist_ok=True)

    log.info(f"Preprocessing {args.input.name}")
    pre = DoPHOTPreprocessor(config).run(image=image, header=header, work_dir=workdir)

    intermediate = workdir / "intermediate_i4.fits"
    hdu = fits.PrimaryHDU(pre.image_with_psf.astype("int32"))
    hdu.header["UNITCONV"] = pre.conversion_factor
    fits.HDUList([hdu]).writeto(intermediate, overwrite=True)

    log.info("Running DoPHOT")
    catalog = DoPHOTExecutor(config).run(
        image_path=intermediate,
        param_file=pre.param_file,
        output_dir=workdir,
        conversion_factor=pre.conversion_factor,
        original_units=pre.units,
    )

    if len(catalog) == 0:
        log.error("DoPHOT produced no sources; see the work directory for logs")
        return 2

    catalog.write(output, overwrite=True)
    log.info(f"Wrote {len(catalog)} sources to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
