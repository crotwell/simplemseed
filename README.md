# simplemseed


[![PyPI](https://img.shields.io/pypi/v/simplemseed)](https://pypi.org/project/simplemseed/)
[![Documentation Status](https://readthedocs.org/projects/simplemseed/badge/?version=latest)](https://simplemseed.readthedocs.io/en/latest/?badge=latest)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17246121.svg)](https://doi.org/10.5281/zenodo.17246121)


[Miniseed3](http://docs.fdsn.org/projects/miniseed3) (and miniseed2) in pure python.

Read the docs at [readthedocs](https://simplemseed.readthedocs.io/en/latest/)

# Installation

`simplemseed` can be installed in conda environments from [conda-forge](https://conda-forge.org/docs/user/introduction/#how-can-i-install-packages-from-conda-forge) ..

```
$ conda install --channel conda-forge simplemseed
```

.. or from [pypi](https://pypi.org/project/simplemseed/) using `pip`:


```
$ pip install simplemseed
```

# Miniseed3

Write and read mseed3 records like:

```python
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
```

Access uncompressed timeseries data as numpy ndarray with:
```python
dataArray = ms3record.decompress()
```


Also includes compression and decompression
for primitive data arrays and
for Steim1 and Steim2, in pure python.

# Miniseed2:

Read miniseed2 with:
```python
with open(ms2filename, "rb") as inms2:
    for ms2rec in simplemseed.readMiniseed2Records(inms2):
        print(ms2rec.summary())
```
or read and convert to miniseed3:
```python
with open(ms3filename, "wb") as outms3:
    with open(ms2filename, "rb") as inms2:
        for ms2rec in simplemseed.readMiniseed2Records(inms2):
            ms3rec = simplemseed.mseed2to3(ms2rec)
            outms3.write(ms3rec.pack())
```

# Command line tools:


##  Miniseed3 Details

Print details about each miniseed3 record

```
mseed3details casee.mseed3
          FDSN:CO_CASEE_00_H_H_Z, version 4, 285 bytes (format: 3)
                       start time: 2023-06-17T04:53:54.468392Z (168)
                number of samples: 104
                 sample rate (Hz): 100.0
                            flags: [00000000] 8 bits$
                              CRC: 0x4D467F27
              extra header length: 31 bytes
              data payload length: 192 bytes
                 payload encoding: STEIM-2 integer compression (val: 11)
                    extra headers:

Total 104 samples in 1 records
```

## Getting and setting extra header values

```
% mseed3details --get "/FDSN/Time" casee_two.ms3
  {"Quality": 0}
% mseed3details --getall "/FDSN/Time/Quality" casee_two.ms3 --verbose
file: casee_two.ms3
FDSN:CO_CASEE_00_H_H_Z 2023-06-17T04:53:50.008392Z 2023-06-17T04:53:50.178392Z (18 pts)
  0
FDSN:CO_CASEE_00_H_H_Z 2023-06-17T04:53:50.188392Z 2023-06-17T04:53:55.498392Z (532 pts)
  0
% mseed3details --set "/data" '{ "key": "val", "keyb": 3 }' casee_two.ms3
% mseed3details --getall "/data" casee_two.ms3 --verbose
file: casee_two.ms3
FDSN:CO_CASEE_00_H_H_Z 2023-06-17T04:53:50.008392Z 2023-06-17T04:53:50.178392Z (18 pts)
  {"key": "val", "keyb": 3}
FDSN:CO_CASEE_00_H_H_Z 2023-06-17T04:53:50.188392Z 2023-06-17T04:53:55.498392Z (532 pts)
  pointer not found in extra headers
% mseed3details --setall "/data" '{ "key": "else", "keyb": 4 }' casee_two.ms3
% mseed3details --set "/data/keyb" 42 casee_two.ms3
% mseed3details --getall "/data" casee_two.ms3 --verbose
file: casee_two.ms3
FDSN:CO_CASEE_00_H_H_Z 2023-06-17T04:53:50.008392Z 2023-06-17T04:53:50.178392Z (18 pts)
  {"key": "else", "keyb": 42}
FDSN:CO_CASEE_00_H_H_Z 2023-06-17T04:53:50.188392Z 2023-06-17T04:53:55.498392Z (532 pts)
  {"key": "else", "keyb": 4}
```

##  Merge mseed3 records
- merge contiguous, in order, mseed3 records into larger records. Decompression
is needed as steim1 and 2 cannot be merged without decompression, primitive
types are already decompressed.
```
mseed3merge -o merged.ms3 --decomp  bird_jsc.ms3
```

##  Convert miniseed 2 to miniseed3.

Note most blockettes are ignored, other than 100, 1000, 1001

```
mseed2to3 --ms2 casee.ms2 --ms3 casee.ms3
```


## FDSN sourceid

Parse FDSN [sourceids](http://docs.fdsn.org/projects/source-identifiers/en/v1.0/)

Split a FDSN source id:
```
fdsnsourceid FDSN:CO_JSC_00_H_H_Z
      FDSN:CO_JSC_00_H_H_Z
       Net: CO
       Sta: JSC
       Loc: 00
      Band: H - High Broadband, >= 80 to < 250 Hz, response period >= 10 sec
    Source: H - High Gain Seismometer
 Subsource: Z
```   

Describe a band code:
```
fdsnsourceid -b Q
      Band: Q - Q - Greater than 10 days , < 0.000001 Hz
```

Find the correct band code for a sample rate:
```
fdsnsourceid --sps 87
      Rate: 87.0 - H - H - High Broadband , >= 80 to < 250 Hz, response period >= 10 sec
      Rate: 87.0 - E - E - Extremely Short Period, >= 80 to < 250 Hz, response period < 10 sec
```

Describe a source code:
```
fdsnsourceid --source H N
    Source: H - High Gain Seismometer
       Measures displacement/velocity/acceleration along a line defined by the the dip and azimuth.
    Source: N - Accelerometer
       Measures displacement/velocity/acceleration along a line defined by the the dip and azimuth.
```

# Examples

There are more examples in the
[examples](https://github.com/crotwell/simplemseed/tree/main/examples) directory.
