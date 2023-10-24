# Description: a script to manage a git repository with one folder per student
#
# Workflow:
#
# 1. ask each student to create a github repo named like e.g. pe-homework
#    repo should be private, they invite you as a collaborator
# 2. beware to accept their invitation in a timely manner, as a github
#    invitation expires after a few days
# 3. create a fresh folder, named after the target reponame
#    so typically you could put all this in a folder
#    $HOME/git/ue12-p23/numerique/pe-homework
#    alternately, if this convention does not suit you, you can instead
#    create a file named `00.reponame` containing the name of the repo (e.g. pe-homework)
#    this will be used to locate the student repos to be cloned
# 4. as you receive invitations, add them to a file named 00.ids
#    you can use '#' for comments in that file
#    this script arbitrarily assumes all student ids start with a letter
#    and so all local files starting with a letter is deemed a student folder
# 5. run this script to clone all the repos with
#    00.sh clone
#    this can be done several times, the existing folders will be skipped
#    so only the missing students are tried again
# 6. if a student has misspelled their repo name, you can edit 00.ids
#    and add the correct repo name after the id, separated by a space
#    this will take precedence over the default reponame (pe-homework in our example)
# 7. iterate until you have all the ids and all the repos cloned
#    in the meanwhile, you can use all the functions below

# Usage:
#
# each function in this script can be called from the command line
# e.g. (read through the file for more details)
# ./00.sh summary    will output a summary of all repos (nb of commits, last commit date, ...)
# ./00.sh list       will output all ids on stdout
# ./00.sh fetch      will fetch all repos
# ./00.sh pull       will pull all repos
# ./00.sh log1       will show the last commit of each repo
# ./00.sh oldies     will output the folders present but that are no longer in 00.ids
#                    i.e. students that have switched to another group




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

# a rather fancy summary, shows the ones missing, the ones empty, and so on
function summary() {
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
