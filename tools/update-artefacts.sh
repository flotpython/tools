#!/usr/bin/env bash

# using the current folder name
COMMAND=$(basename $0)
FOLDERNAMEOPT=

ZIP="computed-later"
FILES="computed-later"

function spot-files() {
    FILES=""
    local line
    for line in $(grep -v '#' ARTEFACTS); do
    FILES="$FILES $(git ls-files $line)"
    done
    local file
    for file in $FILES; do
        [[ -f "$file" ]] || { echo WARNING: file $file not found; }
    done
}


# returns 1 (needs update) or 0 (everything up-to-date)
function up-to-update() {
    local zip="$1"; shift
    local files
    [[ -f "$ZIP" ]] || { return 1; }
    for file in $files; do
        [[ $file -nt $ZIP ]] && { return 1; }
    done
    return 0
}

function help() {
    echo "Usage: $COMMAND [-f] [-n name] [folder]"
    echo "  refresh ARTEFACTS-foldername.zip from the contents of ARTEFACTS"
    echo "  -f: force re-zipping"
    echo "  -n name: override foldername, that by default is computed from the folder"
    echo "  folder: where to run (defaults to .)"
    exit 1
}

function main() {

    while getopts "fvn:h" arg; do
        case $arg in
            f) FORCE=true ;;
            v) VERBOSE=true ;;
            n) FOLDERNAMEOPT=$OPTARG ;;
            h) help ;;
        esac
    done
    shift $((OPTIND-1))

    # no argument means .
    local args="."
    [[ -n "$@" ]] && args="$@"

    here=$(pwd)
    for arg in $args; do
        cd $here
        handle-one-dir $arg
    done
}

function handle-one-dir() {
    local dir="$1"; shift

    # the arg is expected to be a folder or file; we cd in there
    # if called with a file (typically the ARTEFACTS file itself)
    [[ -f "$dir" ]] && dir=$(dirname $dir)
    [[ -d "$dir" ]] || { echo no such folder $dir - ignored; return; }
    cd "$dir"; echo "$COMMAND in $(pwd)";

    local foldername="$FOLDERNAMEOPT"
    [[ -z "$foldername" ]] && foldername=$(basename $(pwd))

    ZIP=ARTEFACTS-${foldername}.zip
    spot-files

    up-to-update && [[ -z "$FORCE" ]] && { echo $ZIP is up-to-date; return 0; }
    echo "$COMMAND in $(pwd)"
    echo "re-building $ZIP"
    rm -f $ZIP
    zip $ZIP $FILES
}

main "$@"
