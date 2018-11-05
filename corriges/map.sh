#!/bin/bash
#
# run at toplevel
#
# purpose it to refresh the mapping exercice -> week x sequence
# so that corriges.py can output stuff properly
#

[ "$#" == 2 ] || {
    echo "USAGE $0 mode coursedir";
    exit 1;
}

mode=$1; shift
COURSEDIR=$1; shift

[ -d $COURSEDIR/w1 ] || {
    echo Directory $COURSEDIR does not seem to be the course repo;
    exit 1;
}

case $mode in
    exo)
        >&2 echo "Refreshing exomap"
        (cd $COURSEDIR; grep exo_ w?/w*-x*nb | grep import | grep from)
        ;;
    nb)
        >&2 echo "Refreshing nbmap"
	    (cd $COURSEDIR; git ls-files w?/w?-s?-[cx]*nb)
        ;;
    *)
        >&2 echo "Unknown mode $mode"
        exit 1
        ;;
esac
