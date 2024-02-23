#!/usr/bin/env python3

from simplemseed import MSeed3Header, MSeed3Record, FDSNSourceId, readMSeed3Records

data = [(i % 99 - 49) for i in range(0, 1000)]
header = MSeed3Header()
header.starttime = "2024-01-01T15:13:55.123456Z"
header.sampleRatePeriod = 20
sid = FDSNSourceId.createUnknown(header.sampleRatePeriod)
ms3record = MSeed3Record(header, sid, data)

ms3filename = "test.ms3"
with open(ms3filename, "wb") as of:
    of.write(ms3record.pack())
    print(f"  save: {ms3record.details()} ")
    print(f"    to: {ms3filename} ")
print()
with open(ms3filename, "rb") as infile:
    for readms3record in readMSeed3Records(infile):
        print(f"  extract: {readms3record.details()} ")
        print(f"     from: {ms3filename} ")
