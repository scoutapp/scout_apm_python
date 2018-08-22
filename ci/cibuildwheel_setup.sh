#!/bin/bash
#
# This script is executed prior to the cibuildwheel docker
# test command. It is executed on the Travis container.
# It sets up the necessary environment.
# Docs: https://github.com/joerick/cibuildwheel
#

# Exit with nonzero status if anything in this script errors.
set -e

# This should list all of the versions cibuildwheel supports.
ALL_CIBW_VERSIONS="cp27-* cp33-* cp34-* cp35-* cp36-* cp37-*"

# We want to skip all versions EXCEPT the one specified by travis in $CIBW_PY_VER
export CIBW_SKIP=`echo ${ALL_CIBW_VERSIONS} | perl -pe "s/cp${CIBW_PY_VER}.*? //"`

echo ""
echo "---------------- CIBW SETUP ENVIRONMENT VARIABLES -------------------"
echo ""
echo "CIBW_PY_VER: ${CIBW_PY_VER}"
echo "CIBW_SKIP: ${CIBW_SKIP}"
echo ""
echo ""
