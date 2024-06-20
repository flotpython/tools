#!/bin/bash

# this script is a convenience to check that the typical setup for a TP is
#
# - under git
# tps/foo/ARTEFACTS
# tps/foo/ARTEFACTS-foo.zip
# tps/foo/.teacher/README-foo-conrrige-nb.md    (or .py)
# tps/foo/data/...
# tps/foo/media/...
# tps/foo/.teacher/data ../data
# tps/foo/.teacher/media ../media
#
# - not under git - for convenience
# tps/foo/teacher -> .teacher

dots=$(find . -name .teacher | grep -v _build)
dirs=$(ls -d $dots | sed -e 's/\/\..*//g')

function list() {
    for dir in $dirs; do
        echo $dir
    done
}

function check-under-git() {
    local dir=$1; shift
    local subdir=$1; shift
    (cd $dir; git ls-files | grep -q "^${subdir}$")
}

function check-subdir() {
    local dir=$1; shift
    local subdir=$1; shift
    if [[ -d $dir/$subdir ]]; then
        if [[ ! -d $dir/.teacher/$subdir ]]; then
            echo "No .teacher/$subdir in $dir" - creating
            (cd $dir/.teacher; ln -s ../$subdir .; git add $subdir)
        else
            if ! check-under-git $dir/.teacher $subdir; then
                echo "Not under git $dir/.teacher/$subdir - adding"
                (cd $dir/.teacher; git add $subdir)
            fi
        fi
    else
        echo "No $subdir in $dir"
    fi
}

function summary() {
    for dir in $dirs; do
        echo ==== "$dir: "
        [[ -f $dir/ARTEFACTS ]] || { echo "No ARTEFACTS in $dir"; }
        grep -q '{download}' $dir/.teacher/*-nb.* || { echo "No {download} in $dir/.teacher/*-nb.*"; }
        check-subdir $dir data
        check-subdir $dir media
    done
}

"$@"
