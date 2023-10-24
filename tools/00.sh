# get standardized github repo name (like e.g. pe-homework)
# for the name of the current folder
# unless you need to overwrite it
if [ -f 00.reponame ]; then
    REPONAME=$(cat 00.reponame)
else
    REPONAME=$(basename $(pwd -P))
fi

# 00.ids is supposed to contain the github ids of all the students
ids=$(cat 00.ids | sed -e 's/#.*//' | awk '{print $1}')
id_repos=$(cat 00.ids | sed -e 's/#.*//' | grep -v '^[ \t]*$' | awk '{print $1":"$2}')

# all these are considered as belonging to students
dirs=$(ls -d [a-zA-Z]*)

# students that have switched to another group
function oldies() {
    for d in $dirs; do
        echo $ids | grep -q $d || { echo OLDY $d; }
    done
}

function list() {
    echo $ids
}
function list-repos() {
    for id_repo in $id_repos; do
        local id=$(echo $id_repo | cut -d: -f1)
        local repo=$(echo $id_repo | cut -d: -f2)
        [[ -z $repo ]] && repo=$REPONAME
        echo $id is using repo $repo
    done
}
# how many do we even know about ?
function how-many() {
    echo we have $(wc -w <<< $ids) known ids
}

# which ones are missing
function missing() {
    for id in $ids; do
        [[ -d $id ]] || { echo MISSING $id; continue; }
        git -C $id log >& /dev/null || { echo EMPTY $id; continue; }
    done
}

function -git-proxy() {
    local message="$1"; shift
    for d in $dirs; do
        [[ -n "$message" ]] && echo ===== $message in $d
        git -C $d "$@"
    done
}

function clone() {
    for id_repo in $id_repos; do
        local id=$(echo $id_repo | cut -d: -f1)
        local repo=$(echo $id_repo | cut -d: -f2)
        [[ -z $repo ]] && repo=$REPONAME
        [ -d $id ] && { echo $id OK; continue; }
        echo cloning into $id from repo $repo
        git clone git@github.com:$id/$repo.git $id
    done
}

function urls() { -git-proxy "" remote get-url origin; }
function log1() { -git-proxy "" log -1 --format=format:'%C(bold blue)%h%C(reset) - %C(bold green)(%ar)%C(reset) %C(dim bold red)%an%C(reset) - %s%C(red)%d%C(reset)'; }
function log5() { -git-proxy "LISTING 5" log --oneline --all --graph -5; }
function status() { -git-proxy "STATUS" status; }
function fetch() { -git-proxy "FETCHING" fetch --all; }
function pull() { -git-proxy "pulling" pull; }
function reset() { -git-proxy "resetting-hard" reset --hard; }
function merge() { -git-proxy "merging" merge origin/main; }
function lastcommit() { -git-proxy "last commit" log -1; }

# initially in git-tp-add-by-lines
function list-git() {
    local nb_ids=$(echo $ids | wc -w)
    echo we have $nb_ids ids
    local counter=0
    for id in $ids; do
        [[ -d $id ]] || { printf '%27s ' $id; echo MISSING; continue; }
        git -C $id log >& /dev/null || { printf '%27s ' $id; echo EMPTY; continue; }
        counter=$(($counter + 1))
        printf '%02d ' $counter
        printf '%24s ' $id
        local dateh=$(git -C $id log -1 --format='%ah')
        local date=$(git -C $id log -1 --format='%ar')
        local nb_folders=$(find $id -type d | fgrep -v '/.git/' | wc -l)
        local nb_files=$(find $id -type f | fgrep -v '/.git/' | wc -l)
        local nb_git_files=$(git -C $id ls-files | wc -l)
        local nb_commits=$(git -C $id log --oneline | wc -l)
        echo $nb_folders folders - $nb_files files - $nb_git_files git files - $nb_commits commits - "last on $dateh ($date)"
    done
    echo we have $counter actual ids
}

function -spot-and-run() {
    local pattern="$1"; shift
    local run="$1"; shift
    for id in $ids; do
        echo -n ===== $id
        local found=$(find $id -name "$pattern")
        if [ -z "$found" ]; then
            echo MISSING pattern "$pattern"
            continue
        fi
        if [ -z "$run" ]; then
            echo FOUND pattern "$pattern" = $found
            continue
        fi
        echo RUNNING $found
        python $found
    done
}
function missing-snake() { -spot-and-run 'snake*.py'; }
function run-snake() { -spot-and-run 'snake*.py' run; }

for step in "$@"; do $step; done
