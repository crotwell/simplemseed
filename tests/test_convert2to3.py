import os
import pytest
import simplemseed
from datetime import datetime
from pathlib import Path

TEST_DIR = Path(__file__).parent


# mseed2 via
# https://service.iris.edu/fdsnws/dataselect/1/query?net=CO&sta=CASEE&loc=00&cha=HHZ&starttime=2023-06-17T04:53:54.468&endtime=2023-06-17T04:55:00&format=miniseed&nodata=404
#


class TestMseed2to3:
    def test_read(self):
        with open(TEST_DIR / "casee.mseed2", "rb") as f:
            rec_bytes = f.read()
            assert len(rec_bytes) == 512
            ms2 = simplemseed.miniseed.unpackMiniseedRecord(rec_bytes)
            ms3 = simplemseed.mseed2to3(ms2)
            print(ms3.details())
            assert len(ms2.decompressed()) == len(ms3.decompress())
