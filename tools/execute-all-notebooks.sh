shopt -s globstar

EXTENDED=""
VERBOSE=""
LIST=""
CLEAN=""
FORCE=""

function help() {
    echo "Usage: $0 [-v] [-x] [notebooks]"
    echo "  Execute notebooks"
    echo "    with no arg: all visible notebooks (not under a hidden folder)"
    echo "    with -x: all notebooks including the ones under a hidden folder"
    echo "    or pass you own list of notebooks as arguments"
    echo "  For each run"
    echo "    the execution log is stored in notebook.execlog"
    echo "    and a .fail file exists iff the run fails "
    echo "  With the -l option, just lists notebooks"
    echo "  With the -c option, the .execlog and .fail files are cleaned up"
    echo "  With the -f option, always execute even if .execlog is more recent"
}

function main() {

    while getopts "xlcfvh" arg; do
        case $arg in
            x) EXTENDED=true ;;
            l) LIST=true ;;
            c) CLEAN=true ;;
            f) FORCE=true ;;
            v) VERBOSE=true ;;
            h) help ;;
        esac
    done
    shift $((OPTIND-1))

    local focus
    if [[ -n "$@" ]]; then
        focus="$@"
    elif [[ -n "$EXTENDED" ]]; then
        focus=$(find . -name '*-nb.py' -o -name '*-nb.md' | egrep -v '_build|ipynb_checkpoints' | sort)
    else
        # this does not capture hidden folders
        focus=$(ls **/*-nb.{md,py} | grep -v _build/)
    fi

    local notebook
    for notebook in $focus; do
        local log=$notebook.execlog
        local fail=$notebook.fail
        # saving in /dev/null won't work
        local out=${notebook}-trash.md
        [[ -n "$CLEAN" ]] && { rm -f $log $fail; continue; }
        if [[ -n "$FORCE" ]] || [[ $log -ot $notebook ]]; then
            [[ -n "$LIST" ]] && { echo $notebook; continue; }
            [[ -n "$VERBOSE" ]] && echo -n "$notebook "
            function control-c () {
                echo Interrupted - cleaning $log
                rm -f $log $out
                exit 1
            }
            trap control-c SIGINT
            jupytext --execute $notebook -o $out >& $log
            if [[ $? == 0 ]]; then
                [[ -n "$VERBOSE" ]] && echo OK
                rm -f $fail
            else
                [[ -n "$VERBOSE" ]] && echo BROKEN
                touch $fail
            fi
            rm -f $out
        else
            if [[ -n "$VERBOSE" ]]; then
                echo -n $notebook skipped as execlog is more recent
                [[ -f $fail ]] && echo "(BROKEN)" || echo "(OK)"
            fi
        fi
    done
}

main "$@"
