#! /usr/env/bash

# get tiles from input file

if [[ $# -eq 0 ]]; then
    echo "No arguments provided: need a file with x y z coordinates as input"
    exit 1
fi

filename="$1"

if [[ ! -e "${filename}" ]]; then
    echo "File ${filename} not found!"
    exit 1
fi

echo "Input file: ${filename}"

srvs=(a b c)
re='^[0-9]+$'
i=0
sleep_freq=2

while IFS=$'\t'; read -r -a line; do

    # before executing, check that inputs are numbers (no '; rm -rf ' entries)
    # x,y,z must be integers
    x=${line[0]}
    y=${line[1]}
    z=$(echo ${line[2]} | tr -d '\r') # in case there are evil carriage returns
    if ! [[ ${x} =~ ${re} ]] || ! [[ ${y} =~ ${re} ]] || ! [[ ${z} =~ ${re} ]]; then
        echo "Non-integer in the input on line ${i}: ${x}, ${y}, ${z}"
        exit 1
    fi
    ix=$(shuf -i 0-2 -n 1)
    # echo "Server will be ${srvs[ix]}"
    url="https://${srvs[ix]}.tile.openstreetmap.org/${z}/${x}/${y}.png"
    file="${z}_${x}_${y}.png"
    # echo "url is: ${url}"
    cmd="wget -O ${file} ${url}"
    eval "${cmd}"
    ((i++))
    # echo "i = ${i}"
    if (($i % $sleep_freq == 0)); then
        echo "zzz..."
        sleep 1.1
    fi
done < "${filename}"
