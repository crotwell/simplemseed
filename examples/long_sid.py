#!/usr/bin/env python3

from simplemseed import MSeed3Header, MSeed3Record, FDSNSourceId, readMSeed3Records



values = [3, 1, -1, 2000]
header = MSeed3Header()
header.starttime = "2024-01-02T15:13:55.123456Z"
header.sampleRatePeriod = -1
header.numSamples = len(values)
identifier = "FDSN:XX2024_REALFAKE_01234567_H_HRQ_Z"
ms3record = MSeed3Record(header, identifier, values)

ms3filename = "long_sid.ms3"
with open(ms3filename, "wb") as of:
    of.write(ms3record.pack())
    print(f"  save: {ms3record.details()} ")
    print(f"    to: {ms3filename} ")
