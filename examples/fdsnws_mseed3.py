#!/usr/bin/env python3

# may need to
# pip install requests

from simplemseed import readMSeed3Records, mseed3merge
import requests
import io

# Example of loading miniseed3 directly from FDSN data select web service,
# and optionally decompressing and merging so that there is one array of
# 32 bit ints per contiguous segment

url = "https://service.iris.edu/fdsnws/dataselect/1/query?net=CO&sta=CASEE&loc=00&cha=HHZ&starttime=2024-02-06T11:30:00&endtime=2024-02-06T11:31:00&format=miniseed3&nodata=404"
r = requests.get(url, stream=True)
ms3List = []
merge = True
if r.status_code == requests.codes.ok:
    databytes = io.BytesIO(r.content)
    prev = None
    for ms3 in readMSeed3Records(databytes):
        if merge:
            ms3 = ms3.decompressedRecord()
            mergelist = mseed3merge(prev, ms3)
            if len(mergelist) == 2:
                ms3List.append(mergelist[0])
                prev = mergelist[1]
            else:
                prev = mergelist[0]
        else:
            ms3List.append(ms3)
    if prev is not None:
        ms3List.append(prev)
    for ms3 in ms3List:
        print(f"{ms3.summary()} {ms3.encodingName()}")
