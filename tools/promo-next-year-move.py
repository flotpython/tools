#!/usr/bin/env python3

"""
Report the migration status from one promo's orga to the next, and emit
ready-to-paste shell commands for any pending actions.

Usage:
  promo-next-year.py ue12-p26                    # checks ue12-p25 -> ue12-p26
  promo-next-year.py ue12-p26 intro git          # restrict to specific repo names
  promo-next-year.py ue12-p26 intro --recreate   # restart a repo from a snapshot of the old one

This script is suggestion-only: it never mutates GitHub or your local repos.
It probes both orgas via `gh`, walks your local clones in ~/git/{orga}-{repo},
and prints colored shell snippets that you can copy and run yourself to fix
any drift (archive old repos, transfer to the new orga, fix origin URLs, ...).

For repos not yet present in the new orga, the default suggestion uses
GitHub's transfer endpoint (preserves history). Pass --recreate to instead
suggest creating a fresh repo seeded with a single snapshot commit of the
old repo's HEAD.

Exceptions:
- mark a repo as intentionally not migrated by creating a `.nomigrate` file
  in its local folder
- if the old repo is archived AND has no local folder, it is also treated
  as intentionally not migrated
"""

import json
import re
import shlex
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from colorama import Fore, Style


USE_COLOR = True


def _wrap(color, x):
    if not USE_COLOR:
        return str(x)
    return f"{color}{x}{Style.RESET_ALL}"

def red(x):
    if isinstance(x, bool):
        x = "YES" if x else "NO "
    return _wrap(Fore.RED, x)

def green(x):
    if isinstance(x, bool):
        x = "YES" if x else "NO "
    return _wrap(Fore.GREEN, x)

def print_orange(*args):
    if not USE_COLOR:
        print(*args)
        return
    print(Fore.YELLOW, *args, Style.RESET_ALL)

def print_blue(*args):
    if not USE_COLOR:
        print(*args)
        return
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


def get_pages_cname(orga_name, reponame):
    """Return the custom-domain cname configured on the repo's Pages, or None."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{orga_name}/{reponame}/pages"],
            capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        return None
    return json.loads(result.stdout).get("cname")


@dataclass
class Repo:
    name: str
    isArchived: bool
    isPrivate: bool
    description: str = ""

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
            print_blue(f"git -C {root2} remote set-url origin {expected}")


class Orga:
    def __init__(self, name):
        self.name = name
        self.repos = []

    def probe(self):
        output = subprocess.run(
            f"gh repo list {self.name} --json name,isArchived,isPrivate,description",
            shell=True,
            check=True,
            capture_output=True)
        raw = json.loads(output.stdout.decode())
        self.repos = [Repo(**repo) for repo in raw]

    def __str__(self):
        nb_total = len(self.repos)
        nb_archived = sum(1 for repo in self.repos if repo.isArchived)
        nb_unarchived = nb_total - nb_archived
        nb_private = sum(1 for repo in self.repos if repo.isPrivate)
        nb_public = nb_total - nb_private
        return f"{self.name}, total = {nb_total} {nb_archived}/{nb_unarchived} archived {nb_private}/{nb_public} private"


class OrgaDiff:

    def __init__(self, prev_orga, next_orga, recreate=False, cname_cache=None):
        self.prev_orga = prev_orga
        self.next_orga = next_orga
        self.recreate = recreate
        self.cname_cache = cname_cache or {}

    FORMAT_HEAD = "{:^30} {:>17} | {:<17}"
    FORMAT_LINE = "{:>30} pri: {:^3} arc: {:^3} | pri: {:^3} arc: {:^3}"

    def summary(self, *repos):
        summary = defaultdict(dict)
        for repo in self.prev_orga.repos:
            summary[repo.name]['prev'] = repo
        for repo in self.next_orga.repos:
            summary[repo.name]['next'] = repo
        if repos:
            summary = {k: v for k, v in summary.items() if k in repos}
        print(40*'-', "summary")
        prev_orga = self.prev_orga.name
        next_orga = self.next_orga.name
        print(self.FORMAT_HEAD.format("", prev_orga, next_orga))
        for reponame in sorted(summary.keys()):
            couple = summary[reponame]
            # in both orgas
            if 'prev' in couple and 'next' in couple:
                a, b, c, d = (couple['prev'].isPrivate, couple['prev'].isArchived,
                              couple['next'].isPrivate, couple['next'].isArchived)
                c = red(c) if a != c else green(c)
                d = red(d) if d else green(d)
                a = green(a)
                needs_archive = not b
                b = green(b) if b else red(b)
                message = self.FORMAT_LINE.format(reponame, a, b, c, d)
                message = green(message) if Fore.RED not in message else red(message)
                print(message)
                if needs_archive:
                    print_orange(f"suggestion for {reponame}:")
                    print_blue(f"gh api repos/{prev_orga}/{reponame} -X PATCH -f archived=true >& /dev/null && echo OK")
            # not migrated yet
            elif 'prev' in couple:
                root = couple['prev'].root_in_my_layout(self.prev_orga)
                if root.exists() and (root / ".nomigrate").exists():
                    print(green(self.FORMAT_LINE.format(reponame, '-i-', '-i-', '   ', '   ')))
                    continue
                a, b = couple['prev'].isPrivate, couple['prev'].isArchived
                a, b = red(a), red(b)
                message = self.FORMAT_LINE.format(reponame, a, b, red(" X "), red(" X "))
                message = green(message) if Fore.RED not in message else red(message)
                print(message)
                prev_folder = Path.home() / "git" / f"{prev_orga}-{reponame}"
                next_folder = Path.home() / "git" / f"{next_orga}-{reponame}"
                if not prev_folder.exists():
                    print(red(f"!! cannot suggest move for {reponame} as {prev_folder} does not exist"))
                elif next_folder.exists():
                    print(red(f"!! cannot suggest move for {reponame} as {next_folder} already exists"))
                else:
                    print_orange(f"suggestion for {reponame}:")
                    if self.recreate:
                        visibility = "--private" if couple['prev'].isPrivate else "--public"
                        desc = couple['prev'].description or ""
                        desc_flag = f" --description {shlex.quote(desc)}" if desc else ""
                        print_blue(f"( mkdir -p {next_folder} &&")
                        print_blue(f"git -C {prev_folder} archive HEAD | tar -x -C {next_folder} &&")
                        print_blue(f"git -C {next_folder} init -b main &&")
                        print_blue(f"git -C {next_folder} add . &&")
                        print_blue(f"git -C {next_folder} commit -m 'initial snapshot from {prev_orga}/{reponame}' &&")
                        print_blue(f"gh repo create {next_orga}/{reponame} {visibility}{desc_flag} --source {next_folder} --remote origin --push &&")
                        print_blue(f"gh api repos/{next_orga}/{reponame}/pages -X POST -f build_type=workflow >& /dev/null &&")
                        cname = self.cname_cache.get(reponame)
                        if not cname:
                            print_blue(f"gh api repos/{prev_orga}/{reponame} -X PATCH -f archived=true >& /dev/null &&")
                            print_blue(f"echo OK )")
                        else:
                            print_blue(f"echo OK )")
                            print_orange(f"  then hand off custom domain {cname} —")
                            print_orange(f"  if {next_orga} hasn't yet verified the parent domain, do it once at")
                            print_orange(f"  https://github.com/organizations/{next_orga}/settings/pages")
                            print_blue(f"( echo '{{\"cname\": null}}' | gh api -X PUT repos/{prev_orga}/{reponame}/pages --input - &&")
                            print_blue(f"gh api -X PUT repos/{next_orga}/{reponame}/pages -f cname={cname} &&")
                            print_blue(f"echo 'waiting for HTTPS cert provisioning (up to 5min)...' &&")
                            print_blue(f"n=0; until gh api -X PUT repos/{next_orga}/{reponame}/pages -F https_enforced=true 2>/dev/null; do n=$((n+1)); [ $n -ge 30 ] && exit 1; sleep 10; done &&")
                            print_blue(f"gh api repos/{prev_orga}/{reponame} -X PATCH -f archived=true >& /dev/null &&")
                            print_blue(f"echo OK )")
                    else:
                        print_blue(f"( gh api repos/{prev_orga}/{reponame}/transfer -f new_owner={next_orga} >& /dev/null &&")
                        print_blue(f"mv {prev_folder} {next_folder} &&")
                        print_blue(f"git -C {next_folder} remote set-url origin {couple['prev'].expected_url(self.next_orga, reponame)} &&")
                        print_blue(f"echo OK )")
            # migrated and no longer in the old orga
            elif 'next' in couple:
                c, d = couple['next'].isPrivate, couple['next'].isArchived
                c = green(c)
                d = red(d) if d else green(d)
                message = self.FORMAT_LINE.format(reponame, green("   "), green("   "), c, d)
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
    parser = ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "orga",
        help="target (new) orga, e.g. ue12-p26 — previous promo is derived as ue12-p25",
    )
    parser.add_argument(
        "repos",
        nargs="*",
        help="limit checks to these specific repo names (default: all)",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="for repos not yet in the new orga, suggest creating a fresh repo "
             "with a single snapshot commit instead of transferring the old repo",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI colors (default: auto, on when stdout is a tty)",
    )
    args = parser.parse_args()

    global USE_COLOR
    USE_COLOR = sys.stdout.isatty() and not args.no_color

    next_organame = args.orga
    m = re.match(r"^(ue\d+)-p(\d+)$", next_organame)
    if not m:
        parser.error(f"orga {next_organame!r} doesn't match <semester>-p<year> (e.g. ue12-p26)")
    semester, year = m.group(1), int(m.group(2))
    if year < 1:
        parser.error(f"can't derive previous promo from {next_organame!r}")
    prev_organame = f"{semester}-p{year - 1:02d}"

    print(f"checking migration {prev_organame} -> {next_organame}")

    prev_orga = Orga(prev_organame)
    next_orga = Orga(next_organame)
    prev_orga.probe()
    print(prev_orga)
    next_orga.probe()
    print(next_orga)

    cname_cache = {}
    if args.recreate:
        next_names = {r.name for r in next_orga.repos}
        target_names = set(args.repos) if args.repos else None
        for r in prev_orga.repos:
            if target_names and r.name not in target_names:
                continue
            if r.name in next_names:
                continue
            cn = get_pages_cname(prev_organame, r.name)
            if cn:
                cname_cache[r.name] = cn
        if cname_cache:
            parent_domains = sorted({cn.split('.', 1)[1] for cn in cname_cache.values() if '.' in cn})
            print()
            for pd in parent_domains:
                print_orange(f"WARNING: the new orga {next_organame} needs to have verified it owns the domain {pd}")
                print_orange(f"this can be done at   https://github.com/organizations/{next_organame}/settings/pages")
            print()

    orga_diff = OrgaDiff(prev_orga, next_orga, recreate=args.recreate, cname_cache=cname_cache)
    orga_diff.summary(*args.repos)
    orga_diff.check_for_leftovers(*args.repos)
    orga_diff.check_origin(*args.repos)


if __name__ == "__main__":
    main()
