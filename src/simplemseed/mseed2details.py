import argparse
import os
import sys
from .miniseed import readMiniseed2Records
from .version import VERSION


def do_parseargs():
    parser = argparse.ArgumentParser(
        description="Simple details of miniseed 2."
    )
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    parser.add_argument(
        "--version", help="print version", action="version",
        version=f'%(prog)s, simplemseed version {VERSION}'
    )
    parser.add_argument(
        "--summary", help="one line summary per record", action="store_true"
    )
    parser.add_argument("--data", help="print timeseries data", action="store_true")
    parser.add_argument(
        "--match",
        help="regular expression to match the identifier",
    )
    parser.add_argument(
        "ms2files", metavar="ms2file", nargs="+", help="mseed2 files to print"
    )
    return parser.parse_args()


def do_details():
    args = do_parseargs()
    totSamples = 0
    numRecords = 0

    for ms2file in args.ms2files:
        with open(ms2file, "rb") as inms2file:
            for ms2 in readMiniseed2Records(inms2file, matchsid=args.match):
                numRecords += 1
                totSamples += ms2.header.numSamples
                if args.summary:
                    print(ms2.summary())
                else:
                    print(ms2.details(showData=args.data))

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
    sys.exit(main())
