#!/usr/bin/env python

"""
Description: a script to manage a collection of git repositories,
with one folder per student

\b
Config files:
00.ids: where to store the students ids (and optionally reponames)
00.reponame (optional): how the student repo is supposed to be named

\b
Workflow:
0. you start with creating a file `00.ids` containing the github ids of the students
   all the ones that you are aware of at least
1. ask each student to create a github repo named like e.g. numerique-homework
   usually repo should be private (so students can't see each other's work),
   in this case, they invite you, the teacher, as a collaborator
2. beware to accept their invitation in a timely manner, as a github
   invitation expires after typically 7 days
3. create a fresh folder, named after the target reponame
   so typically you could put all this in a folder
   $HOME/git/ue12-p23-numerique/numerique-homework
   alternately, if this convention does not suit you, you can instead
   create a file named `00.reponame` containing the name of the repo
   (e.g. numerique-homework)
   this will be used to locate the student repos to be cloned
4. as you receive new invitations, add them to a file named 00.ids if missing
   see below for details on this file format
5. run this script to clone all the repos with
   collect-homework clone
   this can be done several times, the existing folders will be skipped
   so only the missing students are tried again
6. if a student has misspelled their repo name
   e.g. it is called homework-num instead of the expected numerique-homework
   then tweak 00.ids (see the format below)
7. iterate until you have all the ids and all the repos cloned

in the meanwhile, you can use all the functions below

collect-homework --help

\b
collect-homework clone      will clone all repos
collect-homework summary    will output a summary of all repos (nb of commits, last commit date, ...)
collect-homework ids        will output all ids on stdout
collect-homework repos      will output all ids on stdout
collect-homework fetch      will fetch all repos
collect-homework pull       will pull all repos
collect-homework log1       will show the (full) last commit of each repo
collect-homework l1         will show the last commit of each repo (one line per commit)
collect-homework ln 4       same on the 4 last commits of each repo
collect-homework missing    will output the folders missing
                            i.e. students that have not yet created their repo

you can use the -s option to restrict to one or several students, like so

  collect-homework -s "bobarteam, john/ albert"

the -s option expects exactly one argument, it will then use
either space, comma or slash to cut the student names

Format for 00.ids:

\b
00.ids is supposed to contain, one per line, the github ids of the students
it can contain comments, starting with a #
for each student you can use any of the following formats
 - https://github.com/student/repo
 - student/repo
 - student

when the repo is not provided, it is assumed to be
  either the content of 00.reponame if that file exists
  otherwise the name of the current folder
"""

import sys
from pathlib import Path
import re
import subprocess

import click

CFG_REPONAME = "00.reponame"
CFG_IDS = "00.ids"


def get_reponame():
    cfg_reponame = Path(CFG_REPONAME)
    if not cfg_reponame.exists():
        return Path(".").absolute().parts[-1]
    with cfg_reponame.open() as f:
        return f.read().strip()


def get_ids(default_reponame):
    cfg_ids = Path(CFG_IDS)
    result = {}
    with cfg_ids.open() as f:
        for line in f:
            if line.startswith('#'):
                continue
            line = line.strip()
            if "/" in line:
                slug, reponame = line.split("/")
                slug = slug.replace("https://github.com/", "")
            else:
                slug = line
                reponame = default_reponame
            result[slug] = reponame
    return result


def get_actual_repos():
    for dir in Path(".").glob("*/.git"):
        yield dir.parent.parts[-1]


def _git_proxy(message, *git_command):
    """
    Run a git command on all DIRS
    """
    for slug in get_actual_repos():
        if slug not in IDS:
            continue
        if message:
            print(f"===== {message} in {slug}")
        command = ["git", "-C", slug, *git_command]
        # print(command)
        subprocess.run(command)

# globals

REPONAME = get_reponame()
IDS = get_ids(REPONAME)
DIRS = list(get_actual_repos())


# the click CLI object
@click.group(chain=True, help=sys.modules[__name__].__doc__)
@click.option('-s', '--students', help="comma-separated")
def cli(students):
    if students is None:
        return
    global IDS
    focus_ids = {}
    students = re.split(r'[/,\s]+', students)
    for student in students:
        if not student:
            continue
        if student not in IDS:
            print(f"unknown student {student} in {CFG_IDS} - -s option ignored")
            return
        focus_ids[student] = IDS[student]
    IDS = focus_ids


# commands
@cli.command('ids')
def ids():
    for slug, reponame in IDS.items():
        print(f"{slug}/{reponame}")

@cli.command('dirs')
def dirs():
    for dir in DIRS:
        print(dir)

@cli.command('missing')
def missing():
    for slug, reponame in IDS.items():
        if slug not in DIRS:
            print(slug)

@cli.command('clone')
def clone():
    for slug, reponame in IDS.items():
        gitrepo = Path(slug) / "git"
        if gitrepo.exists() and gitrepo.is_dir():
            print(f"{slug} OK")
            continue
        command = ["git", "clone", "git@github.com:{slug}/{reponame}.git", slug]
        subprocess.run(command)

@cli.command('urls')
def urls(): _git_proxy("", "remote", "get-url", "origin")
@cli.command('status')
def status(): _git_proxy("STATUS", "status")
@cli.command('pull')
def pull(): _git_proxy("PULL", "pull")
@cli.command('fetch')
def fetch(): _git_proxy("FETCH", "fetch")
@cli.command('reset')
def reset(): _git_proxy("RESET", "reset", "--hard")
@cli.command('merge')
def merge(): _git_proxy("MERGE", "merge", "origin/main")

@cli.command('log1')
def log1():
    _git_proxy("last commit", "log", "-1")
@cli.command('l1')
def l1():
    _git_proxy(
        "",
        "log", "-1",
        "--format=format:'%C(bold blue)%h%C(reset) - %C(bold green)(%ar)%C(reset) %C(dim bold red)%an%C(reset) - %s%C(red)%d%C(reset)'"
    )
@cli.command('l5')
def l5():
    _git_proxy(
        "LISTING 5",
        "log", "--oneline", "--all", "--graph", "-5",
        "--format=format:'%C(bold blue)%h%C(reset) - %C(bold green)(%ar)%C(reset) %C(dim bold red)%an%C(reset) - %s%C(red)%d%C(reset)'"
    )
@cli.command('ln')
@click.argument('n', type=int)
def ln(n):
    _git_proxy(
        f"LISTING {n}",
        "log", "--oneline", "--all", "--graph", f"-{n}",
        "--format=format:'%C(bold blue)%h%C(reset) - %C(bold green)(%ar)%C(reset) %C(dim bold red)%an%C(reset) - %s%C(red)%d%C(reset)'"
    )


if __name__ == '__main__':
    # import sys
    # thismodule = sys.modules[__name__]
    # doctring = thismodule.__doc__
    # print(doctring)
    cli()
