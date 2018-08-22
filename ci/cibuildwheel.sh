#!/bin/bash
#
# This script is executed as the cibuildwheel test command.
# It sets up the necessary environment and then runs tox.
# Docs: https://github.com/joerick/cibuildwheel
#

# Exit with nonzero status if anything in this script errors.
set -e

# This should list all of the versions cibuildwheel supports.
ALL_CIBW_VERSIONS="cp27-* cp33-* cp34-* cp35-* cp36-* cp37-*"

# We want to skip all versions EXCEPT the one specified by travis in $CIBW_PY_VER
export CIBW_SKIP=`echo ${ALL_CIBW_VERSIONS} | perl -pe "s/cp${CIBW_PY_VER}.*? //"`

# cibuildwheel mounts the project directory into the docker container at /project
export TOX_CONFIG="/project/tox.ini"

# Only run the tox tests for the CIBW_PY_VER python verison.
export TOXENV=`tox -l -c ${TOX_CONFIG} | grep "py${CIBW_PY_VER}"`

echo ""
echo "---------------- CIBW ENVIRONMENT VARIABLES -------------------"
echo ""
echo "CIBW_PY_VER: ${CIBW_PY_VER}"
echo "CIBW_SKIP: ${CIBW_SKIP}"
echo "TOX_CONFIG: ${TOX_CONFIG}"
echo "TOXENV: ${TOXENV}"
echo ""
echo ""

tox -v -c ${TOX_CONFIG}
