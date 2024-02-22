from .seedcodec import EncodedDataSegment
from .mseed3 import MSeed3Record, MSeed3Header, UNKNOWN_DATA_VERSION
from .miniseed import MiniseedRecord, MiniseedException, readMiniseed2Records
from .fdsnsourceid import FDSNSourceId

import argparse
import json


def mseed2to3(ms2: MiniseedRecord) -> MSeed3Record:
    """
    Very simple conversion of a Miniseed version 2 record to miniseed verion 3.
    Most values in blockettes, other than 100, 1000, 1001 are ignored.
    """
    ms3Header = MSeed3Header()

    ms2H = ms2.header
    ms3Header.flags = (
        (ms2H.actFlag & 1) * 2 + (ms2H.ioFlag & 64) * 4 + (ms2H.qualFlag & 16) * 8
    )
    ms3Header.publicationVersion = 0

    ms3Header.year = ms2H.btime.year
    ms3Header.dayOfYear = ms2H.btime.yday
    ms3Header.hour = ms2H.btime.hour
    ms3Header.minute = ms2H.btime.minute
    ms3Header.second = ms2H.btime.second
    ms3Header.nanosecond = ms2H.btime.tenthMilli * 100000
    # maybe can do better from factor and multiplier?
    ms3Header.sampleRatePeriod = (
        ms2.header.sampleRate
        if ms2.header.sampleRate >= 1
        else (-1.0 / ms2.header.sampleRate)
    )
    ms3Header.numSamples = ms2H.numSamples
    ms3Header.recordCRC = 0

    b1000 = None
    for b in ms2.blockettes:
        if b.blocketteNum == 1000:
            b1000 = b
    if b1000 is None:
        raise MiniseedException("Missing blockette 1000")

    ms3Header.encoding = b1000.encoding
    ms3Header.publicationVersion = UNKNOWN_DATA_VERSION
    if ms2.encodedData is not None:
        ms3Header.dataLength = len(ms2.encodedData)
        dataBytes = ms2.encodedData
        data = EncodedDataSegment(
            ms3Header.encoding, dataBytes, ms3Header.numSamples, b1000.byteorder
        )
    else:
        data = ms2.decompressed()
    identifier = FDSNSourceId.fromNslc(
        ms2H.network, ms2H.station, ms2H.location, ms2H.channel
    )

    ms3Extras = {}
    fdsnExtras = {}
    if ms2H.dataquality != 0 and ms2H.dataquality != "D":
        fdsnExtras["DataQuality"] = ms2H.dataquality
        ms3Extras["FDSN"] = fdsnExtras
    nanos = 0
    for b in ms2.blockettes:
        if b.blocketteNum == 100:
            ms3Header.sampleRatePeriod = b.sampleRate
        elif b.blocketteNum == 1001 and b.timeQuality != 0:
            if "Time" not in fdsnExtras:
                fdsnExtras["Time"] = {}
            fdsnExtras["Time"]["Quality"] = b.timeQuality
            nanos = 1000 * b.microseconds

    if ms2H.btime.second == 60:
        if "Time" not in fdsnExtras:
            fdsnExtras["Time"] = {}
        fdsnExtras["Time"]["LeapSecond"] = 1

    ms3Header.nanosecond += nanos
    if ms3Header.nanosecond < 0:
        ms3Header.second -= 1
        ms3Header.nanosecond += 1000000000
        if ms3Header.second < 0:
            # might be wrong for leap seconds
            ms3Header.second += 60
            ms3Header.minute -= 1
            if ms3Header.minute < 0:
                ms3Header.minute += 60
                ms3Header.hour -= 1
                if ms3Header.hour < 0:
                    ms3Header.hour += 24
                    ms3Header.dayOfYear = -1
                    if ms3Header.dayOfYear < 0:
                        # wrong for leap years
                        ms3Header.year -= 1
                        ms3Header.dayOfYear += 365 if ms3Header.year % 4 != 0 else 366
    if len(fdsnExtras) > 0:
        ms3Extras["FDSN"] = fdsnExtras
    if len(ms3Extras) == 0:
        ms3Extras = None
    else:
        ms3Extras = json.dumps(ms3Extras)
        ms3Header.extraHeadersLength = len(ms3Extras.encode("UTF-8"))
    ms3 = MSeed3Record(ms3Header, str(identifier), data, ms3Extras)

    return ms3


def do_parseargs():
    parser = argparse.ArgumentParser(
        description="Simple conversion of miniseed 2 to 3."
    )
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    parser.add_argument(
        "-2",
        "--ms2",
        required=True,
        help="miniseed2 file",
        type=argparse.FileType("rb"),
    )
    parser.add_argument(
        "-3",
        "--ms3",
        required=True,
        help="mseed3 file",
        type=argparse.FileType("wb"),
    )
    return parser.parse_args()


def main():
    import sys

    args = do_parseargs()
    bytesWritten = 0
    with args.ms2 as inms2:
        with args.ms3 as outms3:
            for ms2rec in readMiniseed2Records(inms2):
                ms3rec = mseed2to3(ms2rec)
                outBytes = ms3rec.pack()
                bytesWritten += len(outBytes)
                outms3.write(outBytes)
                if args.verbose:
                    print(f"   {ms3rec}")
    if args.verbose:
        print(f"wrote {bytesWritten} bytes")
