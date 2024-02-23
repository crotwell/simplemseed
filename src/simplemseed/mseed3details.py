import argparse
from datetime import datetime
import json
import os
import sys
import tempfile
import re
from jsonpointer import resolve_pointer, set_pointer, JsonPointer, JsonPointerException
from .mseed3 import MSeed3Record, readMSeed3Records


def do_parseargs():
    parser = argparse.ArgumentParser(
        description="Simple conversion of miniseed 2 to 3."
    )
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    parser.add_argument("--eh", help="display extra headers", action="store_true")
    parser.add_argument(
        "--summary", help="one line summary per record", action="store_true"
    )
    parser.add_argument("--data", help="print timeseries data", action="store_true")
    parser.add_argument(
        "--match",
        help="regular expression to match the identifier",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType('w', encoding='UTF-8'),
        help="""output to file. For get, the output will be json, but for
        getall it will be jsonl, with a separate json object on each line.
        If a record does not have extra headers, a blank line will be output.
        """,
    )
    ehgroup = parser.add_mutually_exclusive_group()
    ehgroup.add_argument(
        "--get",
        help="get eh from first matched record",
    )
    ehgroup.add_argument(
        "--getall",
        help="get eh from all matched records",
    )
    ehgroup.add_argument(
        "--set",
        nargs=2,
        help="set eh for first matched record",
    )
    ehgroup.add_argument(
        "--setall",
        nargs=2,
        help="set eh for all matched records",
    )
    ehgroup.add_argument(
        "--fset",
        nargs=2,
        help="set eh from file for first matched record",
    )
    ehgroup.add_argument(
        "--fsetall",
        nargs=2,
        help="set eh from file for all matched records",
    )
    parser.add_argument(
        "ms3files", metavar="ms3file", nargs="+", help="mseed3 files to print"
    )
    return parser.parse_args()

def do_get_eh(getptr, ms3files, matchsid=None, getall=False, outfile=None, verbose=False):
    looking = True
    pointer = JsonPointer(getptr)
    for ms3file in ms3files:
        if verbose:
            print(f"file: {ms3file}")
        with open(ms3file, "rb") as inms3file:
            for ms3 in readMSeed3Records(inms3file, matchsid=matchsid):
                if looking or getall:
                    looking = False
                    # only get in first record
                    if verbose:
                         print(ms3.summary())
                    try:
                        ehptr = pointer.resolve(ms3.eh)
                        ehStr = json.dumps(ehptr)
                        if outfile is None or outfile == sys.stdout:
                            print(f"  {ehStr}")
                        else:
                            outfile.write(f"{ehStr}\n")
                    except JsonPointerException:
                        if outfile is None or outfile == sys.stdout:
                            print("  pointer not found in extra headers")
                        else:
                            outfile.write("\n")
        if not looking and not getall:
            break

def do_set_eh(setptr, setval, ms3files, matchsid=None, setall=False, verbose=False):
    looking = True
    setjson = json.loads(setval)
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%S.%f")
    # empty or "/" mean replace all extra headers
    usePointer = len(setptr) > 1
    for ms3file in ms3files:
        tmpfile = f"{ms3file}_tmp{now}"
        with open(tmpfile, "wb") as fp:
            with open(ms3file, "rb") as inms3file:
                for ms3 in readMSeed3Records(inms3file, matchsid=matchsid):
                    if looking or setall:
                        looking = False
                        # only set in first record
                        if usePointer:
                            ehptr = set_pointer(ms3.eh, setptr, setjson)
                        else:
                            # replace all
                            ms3eh = setjson
                            ehptr = setjson
                        if verbose:
                            print(ms3.summary())
                            print(f"  {json.dumps(ehptr)}")
                    fp.write(ms3.pack())
            fp.close()
            os.rename(tmpfile, ms3file)
        if not looking and not setall:
            break

def do_details():
    args = do_parseargs()
    totSamples = 0
    numRecords = 0
    if args.outfile is not None:
        outfile = args.outfile
    else:
        outfile = sys.stdout
    if args.get is not None:
        do_get_eh(args.get, args.ms3files, matchsid=args.match, outfile=outfile, verbose=args.verbose)
    elif args.getall is not None:
        do_get_eh(args.getall, args.ms3files, matchsid=args.match, getall=True, outfile=outfile, verbose=args.verbose)
    elif args.set is not None:
        do_set_eh(args.set[0], args.set[1], args.ms3files, matchsid=args.match, verbose=args.verbose)
    elif args.setall is not None:
        do_set_eh(args.setall[0], args.setall[1], args.ms3files, matchsid=args.match, setall=True, verbose=args.verbose)
    elif args.fset is not None:
        with open(args.fset[1], "r") as injson:
            jsoneh = injson.read()
        do_set_eh(args.fset[0], jsoneh, args.ms3files, matchsid=args.match, verbose=args.verbose)
    elif args.fsetall is not None:
        with open(args.fsetall[1], "r") as injson:
            jsoneh = injson.read()
        do_set_eh(args.fsetall[0], jsoneh, args.ms3files, matchsid=args.match, setall=True, verbose=args.verbose)
    else:
        for ms3file in args.ms3files:
            with open(ms3file, "rb") as inms3file:
                for ms3 in readMSeed3Records(inms3file, matchsid=args.match):
                    numRecords += 1
                    totSamples += ms3.header.numSamples
                    if args.summary:
                        print(ms3.summary())
                    else:
                        print(ms3.details(showExtraHeaders=args.eh, showData=args.data))
        print(f"Total {totSamples} samples in {numRecords} records")


def main():
    try:
        do_details()
        sys.stdout.flush()
    except BrokenPipeError:
        # Python flushes standard streams on exit; redirect remaining output
        # to devnull to avoid another BrokenPipeError at shutdown
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)  # Python exits with error code 1 on EPIPE


if __name__ == "__main__":
    main()
