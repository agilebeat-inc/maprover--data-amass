#! /usr/bin/env bash

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

srvs=(a b c)
re='^[0-9]+$'
i=0
sleep_interval=25

echo "Input file: ${filename}"

if [[ $# -gt 1 ]]; then
    ndl="$2"
    echo "ndl = ${ndl}"
    if ! [[ ${ndl} =~ ${re} ]]; then
        echo "If a second arg is passed, it must be a positive integer"
        exit 1
    fi
else
    ndl=1000000 # just something very large
fi


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
    url="https://${srvs[ix]}.tile.openstreetmap.org/${z}/${x}/${y}.png"
    file="${z}_${x}_${y}.png"
    
    cmd="wget -O ${file} ${url}"
    # echo "${i}: ${cmd}"
    eval "${cmd}"
    ((i++))
    if [[ $i -gt ndl ]]; then
        break
    fi

    if (($i % $sleep_interval == 0)); then
        echo "zzz..."
        sleep 1.1
    fi
done < "${filename}"
