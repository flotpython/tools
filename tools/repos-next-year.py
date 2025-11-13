#!/usr/bin/env python

# for when we mass-rename repos
RENAME = {'web': 'frontend'}

def renamed(old_name):
    for old, new in RENAME.items():
        old_name = old_name.replace(old, new)
    return old_name

"""
a helper tool to transition a repo from one year to the next
e.g.
repos-next-year.py ue22-p23
will check the transition from ue22-p23 to ue22-p24

it will check for:
- pending changes in the old folder
- correct naming and origin's URL in the new folder
- suggest commands to move along the way

exceptions
- when a repo is not migrated on purpose, just create a '.nomigrate'
  file in the local folder, so it is not considered in the transition
- also if an old repo is marked as archived and the corresponding folder
  is not present, it is considered as intentionally not migrated
"""

import json
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from argparse import ArgumentParser

from colorama import Fore, Style

def red(x):
    if isinstance(x, bool):
        x = "YES" if x else "NO "
    return f"{Fore.RED}{x}{Style.RESET_ALL}"

def green(x):
    if isinstance(x, bool):
        x = "YES" if x else "NO "
    return f"{Fore.GREEN}{x}{Style.RESET_ALL}"

def print_orange(*args):
    print(Fore.YELLOW, *args, Style.RESET_ALL)

def print_blue(*args):
    print(Fore.BLUE, *args, Style.RESET_ALL)

def output_of_git_in_path(path, command):
    return subprocess.run(
        f"git -C {path} {command}",
        shell=True,
        check=True,
        capture_output=True).stdout.decode()

def run_git_in_path(path, command):
    return subprocess.run(
        f"git -C {path} {command}",
        shell=True,
        check=True,
        capture_output=False)


@dataclass
class Repo:
    name: str
    isArchived: bool
    isPrivate: bool

    def root_in_my_layout(self, orga):
        """
        my usual layout is this
        ~/git/{orga.name}-{self.name}
        """
        return Path.home() / "git" / f"{orga.name}-{self.name}"


    def expected_url(self, orga, newname=None):
        newname = newname if newname else self.name
        return f"git@github.com:{orga.name}/{newname}.git"


    def check_for_leftovers(self, orga):
        """
        make sure there are no pending changes in the (old) repo
        """
        # my usual layout is this
        root = self.root_in_my_layout(orga)
        if not root.exists():
            print(red(f">> {root} does not exist - ignored in check_for_leftovers"))
            print_orange(f"suggestions for {self.name}:")
            print_blue(f"git clone {self.expected_url(orga)} {root}")
            return
        current_branch = output_of_git_in_path(root, "branch --show-current").strip()
        reported = False
        local_hash = output_of_git_in_path(root, f"rev-parse {current_branch}").strip()
        remote_hash = output_of_git_in_path(root, f"rev-parse origin/{current_branch}").strip()
        if local_hash != remote_hash:
            print(red(f"!! {root.stem} is not in line with origin"))
            print(f"!! {current_branch} local={local_hash[:7]} remote={remote_hash[:7]}")
            run_git_in_path(root, "log --oneline -n 5")
            reported = True
        # check for pending changes
        status = output_of_git_in_path(root, "status --short --untracked-files=no")
        if status:
            print(red(f"!! {root.stem} has pending changes"))
            run_git_in_path(root, "status --short --untracked-files=no")
            reported = True
        if not reported:
            print(green(f"== {root.stem:<30}: branch={current_branch}"))

    def check_origin(self, prev_orga, next_orga):
        """
        make sure the origin remote is correct in the (new) repo
        """
        # my usual layout is this
        root1 = self.root_in_my_layout(prev_orga)
        root2 = self.root_in_my_layout(next_orga)
        expected = self.expected_url(next_orga)
        if not root2.exists():
            print(red(f">> {root2} does not exist - ignored in check_origin"))
            if root1.exists():
                print_orange(f"suggestions for {self.name}:")
                print_blue(f"mv {root1} {root2}")
                print_blue(f"git -C {root2} remote set-url origin {expected}")
            return
        origin_url = output_of_git_in_path(root2, "remote get-url origin").strip()
        if origin_url != expected:
            print(red(f"!! {root2.stem} origin is incorrect"))
            print(f"!! {origin_url=} expected={expected}")
            print_orange(f"suggestion for {self.name}:")
            print_blue("git -C {root2} remote set-url origin {expected}")


class Orga:
    def __init__(self, name, rename_repos):
        self.name = name
        self.rename_repos = rename_repos
        self.repos = []

    def probe(self):
        output = subprocess.run(
            f"gh repo list {self.name} --json name,isArchived,isPrivate",
            shell=True,
            check=True,
            capture_output=True)
        raw = json.loads(output.stdout.decode())
        if self.rename_repos:
            for repo in raw:
                repo_name = renamed(repo['name'])
        self.repos = [Repo(**repo) for repo in raw]

    def __str__(self):
        nb_total = len(self.repos)
        nb_archived = sum(1 for repo in self.repos if repo.isArchived)
        nb_unarchived = nb_total - nb_archived
        nb_private = sum(1 for repo in self.repos if repo.isPrivate)
        nb_public = nb_total - nb_private
        return f"{self.name}, total = {nb_total} {nb_archived}/{nb_unarchived} archived {nb_private}/{nb_public} private"


class OrgaDiff:

    def __init__(self, prev_orga, next_orga):
        self.prev_orga = prev_orga
        self.next_orga = next_orga

    FORMAT_HEAD = "{:^30} {:>17} | {:<17}"
    FORMAT_LINE = "{:>30} pri: {:^3} arc: {:^3} | pri: {:^3} arc: {:^3}"

    def summary(self, *repos):
        summary = defaultdict(dict)
        for repo in self.prev_orga.repos:
            new_name = renamed(repo.name)
            summary[new_name]['prev'] = repo
            if new_name != repo.name:
                print_orange(f"renamed: {new_name} was formerly known as {repo.name}")
                summary[new_name]['old-name'] = repo.name
        for repo in self.next_orga.repos:
            summary[repo.name]['next'] = repo
        if repos:
            summary = {k: v for k, v in summary.items() if k in repos}
        print(40*'-', "summary")
        prev_orga = self.prev_orga.name
        next_orga = self.next_orga.name
        print(self.FORMAT_HEAD.format("", prev_orga, next_orga))
        for new_reponame in sorted(summary.keys()):
            couple = summary[new_reponame]
            old_reponame = couple.get('old-name', new_reponame)
            # duplicated
            if 'prev' in couple and 'next' in couple:
                a, b, c, d = (couple['prev'].isPrivate, couple['prev'].isArchived,
                              couple['next'].isPrivate, couple['next'].isArchived)
                # private remains private
                c = red(c) if a != c else green(c)
                # new not archived
                d = red(d) if d else green(d)
                # colors for alignment
                a = green(a)
                # old one should be archived
                needs_archive = not b
                b = green(b) if b else red(b)
                message = self.FORMAT_LINE.format(new_reponame, a, b, c, d)
                message = green(message) if Fore.RED not in message else red(message)
                print(message)
                if needs_archive:
                    print_orange(f"suggestion for {new_reponame}:")
                    print_blue(f"gh api repos/{prev_orga}/{old_reponame} -X PATCH -f archived=true >& /dev/null && echo OK")
            # not migrated at all
            elif 'prev' in couple:
                root = couple['prev'].root_in_my_layout(self.prev_orga)
                if root.exists() and (root / ".nomigrate").exists():
                    print(green(self.FORMAT_LINE.format(new_reponame, '-i-', '-i-', '   ', '   ')))
                    continue
                a, b = couple['prev'].isPrivate, couple['prev'].isArchived
                a, b = red(a), red(b)
                message = self.FORMAT_LINE.format(new_reponame, a, b, red(" X "), red(" X "))
                message = green(message) if Fore.RED not in message else red(message)
                print(message)
                # check the local repos
                prev_folder = Path.home() / "git" / f"{prev_orga}-{old_reponame}"
                next_folder = Path.home() / "git" / f"{next_orga}-{new_reponame}"
                if not prev_folder.exists():
                    print(red(f"!! cannot suggest move for {new_reponame} as {prev_folder} does not exist"))
                elif next_folder.exists():
                    print(red(f"!! cannot suggest move for {new_reponame} as {next_folder} already exists"))
                else:
                    print_orange(f"suggestion for {new_reponame}:")
                    print_blue(f"( gh api repos/{prev_orga}/{old_reponame}/transfer -f new_owner={next_orga} >& /dev/null &&")
                    if old_reponame != new_reponame:
                        print_blue(f"gh api repos/{next_orga}/{old_reponame} -X PATCH -f name={new_reponame} >& /dev/null &&")
                    print_blue(f"mv {prev_folder} {next_folder} &&")
                    print_blue(f"git -C {next_folder} remote set-url origin {couple['prev'].expected_url(self.next_orga, new_reponame)} &&")
                    print_blue(f"echo OK )")
            # migrated and no longer in the old orga
            elif 'next' in couple:
                c, d = couple['next'].isPrivate, couple['next'].isArchived
                c = green(c)
                # should not be archived
                d = red(d) if d else green(d)
                # call green for preper alignment
                message = self.FORMAT_LINE.format(new_reponame, green("   "), green("   "), c, d)
                message = green(message) if Fore.RED not in message else red(message)
                print(message)


    def check_for_leftovers(self, *repos):
        print(40*'-', "checking for leftovers in old orga")
        for repo in self.prev_orga.repos:
            if repos:
                if repo.name not in repos:
                    continue
            repo.check_for_leftovers(self.prev_orga)
        print(40*'-', "checking for leftovers in new orga")
        for repo in self.next_orga.repos:
            if repos:
                if repo.name not in repos:
                    continue
            repo.check_for_leftovers(self.next_orga)

    def check_origin(self, *repos):
        print(40*'-', "checking for origin in new orga")
        for repo in self.next_orga.repos:
            if repos:
                if repo.name not in repos:
                    continue
            repo.check_origin(self.prev_orga, self.next_orga)


def main():
    parser = ArgumentParser(description="move repos from one year to the next")
    parser.add_argument("orga", help="orga to move repos from")
    parser.add_argument("repos", nargs="*", help="specific repos to move (default: all)")
    args = parser.parse_args()
    prev_organame = args.orga
    print("Moving repos from orga", prev_organame)
    ue, promo = prev_organame.split("-")
    year = int(promo[1:])
    next_year = year + 1
    next_organame = f"{ue}-p{next_year}"
    print(f"{prev_organame=}, -> {next_organame=}")

    prev_orga = Orga(prev_organame, rename_repos=False)
    next_orga = Orga(next_organame, rename_repos=True)

    prev_orga.probe()
    print(prev_orga)

    next_orga.probe()
    print(next_orga)

    orga_diff = OrgaDiff(prev_orga, next_orga)
    orga_diff.summary(*args.repos)
    orga_diff.check_for_leftovers(*args.repos)
    orga_diff.check_origin(*args.repos)

if __name__ == "__main__":
    main()
