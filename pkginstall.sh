#!/usr/bin/env bash

if ! [[ -d 'pipe1' ]]; then
    >&2 echo "This script must be run from the main repo directory!"
    exit 1
fi

# remove any existing 'dist' files in case there are old versions:
if [[ -d 'dist' ]]; then
    rm -r ./dist
fi

# create the blob that pip can install
res=$(python3 setup.py sdist)

if [[ ${res} -ne 0 ]]; then
    >&2 echo "Error code ${res} in setup.py run!"
    exit ${res}
fi

# if the package is currently installed, we don't want to re-install dependencies
# but we do want to re-install if this command has been run
pip3 show pipe1 > /dev/null

if [[ $? -eq 0 ]]; then
    echo "Re-installing package 'pipe1'!"
    pip3 install ./dist/*.gz --no-deps --force-reinstall
else
    echo "Installing pipe1 for the first time!"
    pip3 install ./dist/*.gz
fi