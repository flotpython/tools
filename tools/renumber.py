#! /usr/bin/env python

import sys
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
                print(f"{filename}:{lineno} - ignoring", file=sys.stderr)
                continue
            a, b = line.split('->')
            a, b = a.strip(), b.strip()
            result.append((a, b))
    return result

def rename(a, b, notebooks):
    pattern = f"{a}-*-nb*"
    original = lambda: Path(notebooks).glob(pattern)
    if (n := mylen(original())) != 1:
        print(f"cannot rename {a} into {b}, found {n} candidates")
    filea = next(original())
    fileb = Path(str(filea).replace(a, b))
    stema, stemb = filea.stem, fileb.stem
    #print(stema, stemb)
    print(f"git mv {filea} {fileb}")
    print(f"sed -i -e s/{stema}/{stemb}/ .nbhosting/nbhosting.yaml")

def main():
    parser = ArgumentParser()
    parser.add_argument("-n", "--notebooks", default='notebooks')
    parser.add_argument("specfile")
    args = parser.parse_args()

    for (a, b) in parse_specfile(args.specfile):
        rename(a, b, args.notebooks)
    print(f"make -C {args.notebooks} toc")

main()