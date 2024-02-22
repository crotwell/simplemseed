#!/usr/bin/env python3
#
import array
import json
from simplemseed import MSeed3Header, MSeed3Record
import simplemseed
import struct

output_file = "output.mseed"


def crcAsHex(crc):
    return "0x{:08X}".format(crc)


eh = {
    "bag": {
        "y": {"proc": "raw", "si": "count"},
        "st": {"la": 34.65, "lo": -80.46},
        "ev": {
            "origin": {
                "time": "2024-02-06T11:30:03Z",
                "la": 34.17,
                "lo": -80.70,
                "dp": 1.68,
            },
            "mag": {"val": 1.74, "type": "md"},
        },
    }
}


data = array.array("f", ((i % 99 - 49) for i in range(0, 1000)))
# data = [(i%99-49) for i in range(0,1000)]
header = simplemseed.MSeed3Header()
header.starttime = "2024-01-01T15:13:55.123456Z"
identifier = "FDSN:XX_FAKE__B_H_Z"
header.sampleRatePeriod = 20
ms3record = simplemseed.MSeed3Record(header, identifier, data, extraHeaders=eh)

ms3filename = "test.ms3"
with open(ms3filename, "wb") as of:
    of.write(ms3record.pack())
    print(f"  save: {ms3record.details()} ")
    print(f"    to: {ms3filename} ")
    print(f"   crc: {crcAsHex(ms3record.header.crc)}")

print()
print()
with open(ms3filename, "rb") as infile:
    for readms3record in simplemseed.readMSeed3Records(infile):
        print(f"  extract: {readms3record.details()} ")
        print(f"     from: {ms3filename} ")
        print(f"      crc: {crcAsHex(readms3record.header.crc)}")
        assert (
            readms3record.header.numSamples == ms3record.header.numSamples
        ), f"Num samples: {readms3record.header.numSamples} != {ms3record.header.numSamples}"
