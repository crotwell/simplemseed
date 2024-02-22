#!/usr/bin/env python3
#
import array
import numpy
import json
from simplemseed import MSeed3Header, MSeed3Record
import simplemseed
import struct


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

header = simplemseed.MSeed3Header()
header.starttime = "2024-01-01T15:13:55.123456Z"
identifier = "FDSN:XX_FAKE__H_H_Z"
header.sampleRatePeriod = 40
data = numpy.fromfunction(
    lambda i: (i % 99 - 49), (86400 * header.sampleRate,), dtype=numpy.float32
)
# header numSamples, encoding set from the input data
ms3record = simplemseed.MSeed3Record(header, identifier, data, extraHeaders=eh)

assert (
    len(data) == ms3record.header.numSamples
), f"Num samples: {len(data)}  {ms3record.header.numSamples}"
decomp = ms3record.decompress()
assert len(decomp) == len(data), f"length not same: {len(decomp)} != {len(data)}"
# for i in range(len(data)):
#    assert decomp[i] == data[i]

ms3filename = "test_ginormous.ms3"

with open(ms3filename, "wb") as of:
    of.write(ms3record.pack())
    print(f"  save: {ms3record.details()} ")
    print(f"    to: {ms3filename} ")
    print(f"   crc: {crcAsHex(ms3record.header.crc)}")

print()
print()
with open(ms3filename, "rb") as infile:
    readms3record = next(simplemseed.readMSeed3Records(infile))
    print(f"  extract: {readms3record.details()} ")
    print(f"     from: {ms3filename} ")
    print(f"      crc: {crcAsHex(readms3record.header.crc)}")
    assert (
        readms3record.header.numSamples == ms3record.header.numSamples
    ), f"Num samples: {readms3record.header.numSamples} != {ms3record.header.numSamples}"

    decomp = readms3record.decompress()
    assert len(decomp) == len(data), f"length not same: {len(decomp)} != {len(data)}"
#    for i in range(len(data)):
#        assert decomp[i] == data[i]
