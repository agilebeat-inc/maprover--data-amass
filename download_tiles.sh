#! /usr/bin/env bash

# get tiles from input file


USAGE="download_tiles.sh --file|-f FILENAME [--outdir|-o DIR] [--numtiles|-n N]"

if [[ $# -lt 2 ]]; then
    echo "${USAGE}"
    exit 1
fi

filename=""
outdir="."
ndl=1000000

while (($#)); do
    case $1 in
        --file|-f)
            shift
            filename=$1
            shift
        ;;
        --outdir|-o)
            shift
            outdir=$1
            shift
        ;;
        --numtiles|-n)
            shift
            ndl=$1
            shift
        ;;
        *)
            shift
        ;;
    esac
done

# chop off trailing /
fslash='.+/$'
if [[ "${outdir}" =~ $fslash ]]; then
    outdir="${outdir::-1}"
fi
if [[ ! -d "${outdir}" ]]; then
    mkdir -p "${outdir}"
fi

if [[ ! -e "${filename}" ]]; then
    >&2 echo "File ${filename} not found!"
    exit 1
fi

re='^[0-9]+$'
srvs=(a b c)
i=0
sleep_interval=25


while IFS=$'\t'; read -r -a line; do

    # before executing, check that inputs are numbers (no '; rm -rf ' entries)
    # x,y,z must be integers
    x=${line[0]}
    y=${line[1]}
    z=$(echo ${line[2]} | tr -d '\r') # in case there are evil carriage returns
    if ! [[ ${x} =~ ${re} ]] || ! [[ ${y} =~ ${re} ]] || ! [[ ${z} =~ ${re} ]]; then
        >&2 echo "Non-integer in the input on line ${i}: ${x}, ${y}, ${z}"
        exit 1
    fi
    
    file="${outdir}/${z}_${x}_${y}.png"
    # if the file already exists in this directory, no need to download it
    if [[ -f "${file}" ]]; then
        echo "Already have file ${file}!"
        continue
    fi
    
    ix=$(shuf -i 0-2 -n 1)
    url="https://${srvs[ix]}.tile.openstreetmap.org/${z}/${x}/${y}.png"
    # wget -O "${file}" ${url}
    curl ${url} --output "${file}" --silent
    rv=$?
    if [[ $rv -gt 0 ]]; then
        >&2 echo "Failed on URL ${url} with code ${rv}"
        echo ${url} >> failed.txt
    else
        echo "Saved file #$i: ${file}"
    fi
    ((i++))
    if [[ $i -gt $ndl ]]; then
        break
    fi

    if (($i % $sleep_interval == 0)); then
        echo "zzz..."
        sleep 1.1
    fi
done < "${filename}"

