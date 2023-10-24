#! /usr/bin/env python

"""
helpful to reorder included material in a course
see the .example input for how the moves are specified

it will just print the bash commands to
- do the renaming
- alter all files to reflect the change

it will not
- alter the nbhosting index nor the book toc
"""

import sys
import subprocess
from pathlib import Path
from argparse import ArgumentParser

def mylen(iterator):
    return sum(map(lambda x: 1, iterator))

def parse_specfile(filename):
    result = []
    with open(filename) as feed:
        for lineno, line in enumerate(feed, 1):
            line = line.strip()
            # ignore comments
            line = line.split('#')[0]
            if not line:
                print(f"# {filename}:{lineno} - ignoring", file=sys.stderr)
                continue
            a, b = line.split('->')
            a, b = a.strip(), b.strip()
            result.append((a, b))
    return result

# each run prints shell commands, and also
# returns a sed substitute expression
def rename(a, b, ls_files) -> str:
    found = False
    for oldfile in ls_files:
        newfile = oldfile.replace(a, b)
        if newfile == oldfile:
            continue
        found = True
        target_dir = Path(newfile).parent
        if not target_dir.exists():
            print(f"creating dir {target_dir}", file=sys.stderr)
            target_dir.mkdir()
        print(f"git mv {oldfile} {newfile}")
    if found:
         return f"s|{a}|{b}|g"


def main():
    parser = ArgumentParser()
    parser.add_argument("specfile")
    args = parser.parse_args()
    completed = subprocess.run("git ls-files", shell=True, capture_output=True)
    ls_files = completed.stdout.decode()
    ls_files = [x for x in ls_files.split('\n') if x]
    print(f"we have {len(ls_files)} under git", file=sys.stderr)

    print("bash renumber-include-sed.sh")
    sed_expressions = [
        rename(a, b, ls_files) for (a, b) in parse_specfile(args.specfile)]
    # remove None
    sed_expressions = [x for x in sed_expressions if x]
    files_for_bash = ' '.join(f'"{file}"' for file in ls_files)
    expressions_for_bash = ' '.join(f"-e '{x}'" for x in sed_expressions)
    with open('renumber-include-sed.sh', 'w') as writer:
        print(f"gsed -i.rename {expressions_for_bash} {files_for_bash}", file=writer)

main()