#!/usr/bin/env bash
# Build a manylinux wheel containing the DoPHOT executable with a static CFITSIO.
#
# Run inside quay.io/pypa/manylinux_2_28_x86_64 so the executable only needs the
# glibc baseline of that image:
#   docker run --rm -v "$PWD:/src" -w /src quay.io/pypa/manylinux_2_28_x86_64 \
#       scripts/build_linux_wheel.sh
set -euo pipefail

CFITSIO_VERSION=4.7.0
PY=/opt/python/cp312-cp312/bin/python
REPO=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'chown -R "$(stat -c %u:%g "$REPO")" "$REPO" 2>/dev/null || true' EXIT

yum install -y -q zlib-devel make >/dev/null

curl -fsSL "https://heasarc.gsfc.nasa.gov/FTP/software/fitsio/c/cfitsio-${CFITSIO_VERSION}.tar.gz" \
    | tar xz -C "$WORK"
(
    cd "$WORK/cfitsio-${CFITSIO_VERSION}"
    ./configure --disable-curl --enable-reentrant --disable-shared \
        --prefix="$WORK/cfitsio" CFLAGS="-O2 -fPIC" >/dev/null
    make -j"$(nproc)" >/dev/null
    make install >/dev/null
)

"$PY" -m pip install -q build auditwheel
CFITSIO_PREFIX="$WORK/cfitsio" "$PY" -m build --wheel --outdir "$WORK/dist" "$REPO"
"$PY" -m auditwheel repair -w "$REPO/dist" "$WORK"/dist/*.whl
