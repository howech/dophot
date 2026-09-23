#!/bin/bash
# Helper script to run DoPHOT with stdin input
# Usage: run_dophot.sh <dophot_exe> <param_file> <param_default_file> <workdir>

DOPHOT_EXE="$1"
PARAM_FILE="$2"
PARAM_DEFAULT="$3"
WORKDIR="$4"

cd "$WORKDIR"
(echo "$PARAM_FILE"; echo "$PARAM_DEFAULT") | "$DOPHOT_EXE"
