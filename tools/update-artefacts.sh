#!/usr/bin/env bash

# using the current folder name
COMMAND=$(basename $0 2>/dev/null)
[[ -z "$COMMAND" ]] && COMMAND=update-artefacts.sh
FOLDERNAMEOPT=

ZIP="computed-later"
FILES="computed-later"

VERBOSE=
function verbose() {
    [[ -z "$VERBOSE" ]] && return
    echo "verbose: $@"
}

# compare a zip file with the version in the git index
# returns 0 if identical, 1 if different, 2 on error
function zipdiff-index() {
    local file="$1"
    local tmp="/tmp/git_index_$(basename "$file")"

    # Extract the version from the Git index (staged version)
    git show ":0:./$file" > "$tmp" 2>/dev/null || {
        echo "File not in index: $file" >&2
        return 1
    }

    # Compare with working copy
    zipcmp "$tmp" "$file"
    local status=$?

    if [ $status -eq 0 ]; then
        >&2 echo "✅ No differences in ZIP content ($file)"
    else
        >&2 echo "❌ ZIPs differ ($file)"
    fi

    rm -f "$tmp"
    return $status
}


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
    verbose found artefacts FILES=$FILES
}


# returns 1 (needs update) or 0 (everything up-to-date)
function up-to-update() {
    local zip="$1"; shift
    # local files
    [[ -f "$ZIP" ]] || { return 1; }
    for file in $FILES; do
        verbose checking $ZIP vs $file
        [[ $file -nt $ZIP ]] && {
            echo "found news in $file"
            return 1
        }
    done
    return 0
}


function handle-one-dir() {
    local dir="$1"; shift

    # the arg is expected to be a folder or file; we cd in there
    # if called with a file (typically the ARTEFACTS file itself)
    [[ -f "$dir" ]] && dir=$(dirname $dir)
    [[ -d "$dir" ]] || {
        echo no such folder $dir - ignored
        return
    }
    cd "$dir"
    echo -n "--------  "; basename $(pwd)

    local foldername="$FOLDERNAMEOPT"
    [[ -z "$foldername" ]] && foldername=$(basename $(pwd))

    ZIP=ARTEFACTS-${foldername}.zip
    spot-files

    up-to-update && [[ -z "$FORCE" ]] && {
        echo $ZIP is up-to-date
        return 0
    }
    echo "re-building $ZIP"
    rm -f $ZIP
    zip $ZIP $FILES

    zipdiff-index $ZIP && {
        echo " - no change found - discarding"
        git restore $ZIP ARTEFACTS.list
    }
    echo "- updated"
    unzip -l $ZIP > ARTEFACTS.list
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
    shift $((OPTIND - 1))

    # no argument makes nothing
    local args=""
    [[ -n "$@" ]] && args="$@"

    here=$(pwd)
    for arg in $args; do
        cd $here
        handle-one-dir $arg
    done
}

main "$@"
