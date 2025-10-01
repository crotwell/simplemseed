
"""
Simple merging of miniseed 3 records. This assumes the records are
already in time sorted order by channel. It only compares neighboring
records for merging.
"""

import argparse
import sys
from .mseed3 import readMSeed3Records
from .version import VERSION

def do_parseargs():
    """
    Create arg parser and parse args.
    """
    parser = argparse.ArgumentParser(
        description="""
        Simple merging of miniseed 3 records. This assumes the records are
        already in time sorted order by channel. It only compares neighboring
        records for merging.
        """
    )
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    parser.add_argument(
        "--version", help="print version", action="version",
        version=f'%(prog)s, simplemseed version {VERSION}'
    )
    parser.add_argument(
        "--decomp",
        help="apply decompression before merge, required for steim1 & 2",
        action="store_true",
    )
    parser.add_argument(
        "-o", "--outfile", required=True, help="mseed3 file to output merged records"
    )
    parser.add_argument("ms3file", help="mseed3 file to merge records")
    return parser.parse_args()


def main():
    "main function"
    args = do_parseargs()
    with open(args.outfile, "wb") as outms3file:
        with open(args.ms3file, "rb") as inms3file:
            for ms3 in readMSeed3Records(inms3file, merge=True, verbose=args.verbose):
                if args.verbose:
                    print(ms3)
                outms3file.write(ms3.pack())


if __name__ == "__main__":
    sys.exit(main())
