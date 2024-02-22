
import argparse
import os
import sys
import re
from .mseed3 import MSeed3Record, readMSeed3Record

def do_parseargs():
    parser = argparse.ArgumentParser(
        description="Simple conversion of miniseed 2 to 3."
    )
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    parser.add_argument(
        "--eh", help="display extra headers", action="store_true"
    )
    parser.add_argument(
        "--summary", help="one line summary per record", action="store_true"
    )
    parser.add_argument(
        "--data", help="print timeseries data", action="store_true"
    )
    parser.add_argument(
        "--match",
        help="regular expression to match the identifier",
    )
    parser.add_argument(
        'ms3files',
        metavar='ms3file',
        nargs='+',
        help='mseed3 files to print')
    return parser.parse_args()

def do_details():
    args = do_parseargs()
    matchPat = None
    totSamples = 0
    numRecords = 0
    if args.match is not None:
        matchPat = re.compile(args.match)
    for ms3file in args.ms3files:
        with open(ms3file, "rb") as inms3file:
            ms3 = readMSeed3Record(inms3file)
            while ms3 is not None:
                if matchPat is None or matchPat.search(ms3.identifier) is not None:
                    numRecords += 1
                    totSamples += ms3.header.numSamples
                    if args.summary:
                        print(ms3)
                    else:
                        print(ms3.details(showExtraHeaders=args.eh, showData=args.data))
                ms3 = readMSeed3Record(inms3file)
    print(f"total samples: {totSamples} in {numRecords} records")

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
