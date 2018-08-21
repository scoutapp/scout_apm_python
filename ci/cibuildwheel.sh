#!/bin/bash

set -e

export TOX_CONFIG="/project/tox.ini"
export PY_VER=`echo $PATH | awk -F\- '{print $1}' | awk -F\/ '{print $4}' | tr 'cp' 'py'`
export TOXENV=`tox -l -c ${TOX_CONFIG} | grep ${PY_VER}`

echo "PY_VER: ${PY_VER}"
echo "TOX_CONFIG: ${TOX_CONFIG}"
echo "TOXENV: ${TOXENV}"

tox -v -c ${TOX_CONFIG}
