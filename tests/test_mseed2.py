import os
import pytest
import simplemseed
from datetime import datetime
from pathlib import Path

TEST_DIR = Path(__file__).parent


# mseed2 via
# https://service.iris.edu/fdsnws/dataselect/1/query?net=CO&sta=CASEE&loc=00&cha=HHZ&starttime=2023-06-17T04:53:54.468&endtime=2023-06-17T04:55:00&format=miniseed&nodata=404
#


class TestMseed2:
    def test_read(self):
        with open(TEST_DIR / "casee.mseed2", "rb") as f:
            rec_bytes = f.read()
            assert len(rec_bytes) == 512
            rec = simplemseed.miniseed.unpackMiniseedRecord(rec_bytes)
            assert rec.codes() == "CO.CASEE.00.HHZ"
            assert rec.starttime() == datetime.fromisoformat(
                "2023-06-17T04:53:54.468648+00:00"
            )
            data = rec.decompressed()

            msi_data = [89, 67, 53, 71, 86, 89,
                97, 96, 81, 90, 94, 73,
                73, 79, 87, 100, 91, 107,
               105, 102, 112, 93, 106, 101,
                92, 100, 84, 99, 97, 108,
               151, 130, 114, 124, 116, 116,
               102, 108, 130, 121, 127, 131,
               129, 134, 109, 112, 123, 121,
               139, 132, 153, 157, 128, 140,
               129, 140, 150, 138, 158, 141,
               132, 137, 131, 149, 159, 156,
               142, 140, 158, 154, 149, 141,
               135, 152, 152, 157, 168, 162,
               158, 151, 144, 148, 137, 133,
               147, 150, 155, 139, 134, 154,
               149, 156, 152, 137, 142, 145,
               147, 142, 138, 143, 136, 140,
               143, 137]
            # vals from msi -d -n 1 casee.mseed2
            assert data[0] == 89
            assert data[1] == 67
            assert data[2] == 53
            assert data[3] == 71
            assert data[4] == 86
            assert data[5] == 89
            assert len(data) == len(
                msi_data
            ), f"d:{len(data)} should be orig:{len(msi_data)}"
            for i in range(len(msi_data)):
                assert msi_data[i] == data[i]


if __name__ == "__main__":
    TestMseed2().test_read()
