
import simplemseed
import os
import argparse
import asyncio
import re
import sys
from pathlib import Path

def do_parseargs():
    parser = argparse.ArgumentParser(
        description="Find duplicates in miniseed2 files and attempt to sort and deduplicate."
    )
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    parser.add_argument(
        "--replace",
        help="replace original file with dedupped data",
        action="store_true"
    )
    parser.add_argument(
        "-f",
        "--files",
        required=False,
        help="Miniseed file to read",
        nargs='+',
    )
    return parser.parse_args()

def recordsAreSame(prev, curr):
    return prev is not None and \
        prev.header.numSamples == curr.header.numSamples and \
        prev.starttime() == curr.starttime() and \
        prev.codes() == curr.codes()

def dedupAndSortMS2File(msfile, replace=False, verbose=False):
    msdList = []
    in_records = 0
    out_records = 0
    dedup_prefix = "dedup_"
    inPath = Path(msfile)
    outPath = Path(inPath.parent, f"{dedup_prefix}{inPath.name}")
    with inPath.open(mode='rb') as infile:
        for msr in simplemseed.readMiniseed2Records(infile):
            msdList.append(msr)
            in_records += 1
    msdList.sort(key=lambda msr: msr.starttime())
    msdList.sort(key=lambda msr: msr.codes())
    prevmsr = None
    with outPath.open(mode='wb') as outfile:
        for msr in msdList:
            if not recordsAreSame(prevmsr, msr):
                outfile.write(msr.pack())
                prevmsr = msr
                out_records += 1
    if replace:
        outPath.replace(msfile)
    return (outPath, in_records, out_records)

def processOneArg(args, argPath):
    if argPath.is_file():
        msfile = argPath
        outPath, in_records, out_records = dedupAndSortMS2File(msfile, replace=args.replace, verbose=args.verbose)
        if args.verbose and in_records != out_records:
            print(f"from {msfile} read {in_records} write {out_records} to {outPath}")
    if argPath.is_dir():
        for root, dirs, files in os.walk(argPath):
            for msfile in files:
                processOneArg(args, Path(root, msfile))

def main():
    args = do_parseargs()
    print(args.files)
    for argfile in args.files:
        argPath = Path(argfile)
        processOneArg(args, argPath)
    if args.verbose:
        print("Goodbye...")
    sys.exit(0)


if __name__ == "__main__":
    main()
