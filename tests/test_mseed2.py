import numpy
import os
import array
import math
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

    def test_create(self):
        data = numpy.fromfunction(lambda i: (i % 99 - 49), (100,), dtype=numpy.int16)
        network = "XX"
        station = "TEST"
        location = "00"
        channel = f"HNZ"
        starttime = "2024-01-01T15:13:55.123400Z"
        numsamples = len(data)
        sampleRate = 200
        shortData = array.array("h")  # shorts
        for i in range(numsamples):
            shortData.append(data[i])
        msh = simplemseed.MiniseedHeader(
            network, station, location, channel, starttime, numsamples, sampleRate
        )
        msr = simplemseed.MiniseedRecord(msh, shortData)
        recordBytes = msr.pack()
        outmsr = simplemseed.unpackMiniseedRecord(recordBytes)
        assert msr.codes() == outmsr.codes()
        assert msr.starttime() == outmsr.starttime()
        outdata = outmsr.decompressed()
        print(outdata[0:10])
        assert len(outdata) == len(data)
        assert len(outdata) == msr.header.numSamples
        for i in range(len(data)):
            assert data[i] == outdata[i]

    def test_create_float(self):
        data = numpy.fromfunction(
            lambda i: (i % 99 - 49.2), (100,), dtype=numpy.float32
        )
        network = "XX"
        station = "TEST"
        location = "00"
        channel = f"HNZ"
        starttime = "2024-01-01T15:13:55.123400Z"
        numsamples = len(data)
        sampleRate = 200

        msh = simplemseed.MiniseedHeader(
            network, station, location, channel, starttime, numsamples, sampleRate
        )
        msr = simplemseed.MiniseedRecord(msh, data)
        assert msr.header.byteorder == simplemseed.miniseed.LITTLE_ENDIAN
        recordBytes = msr.pack()
        assert msr.header.encoding == simplemseed.seedcodec.FLOAT
        assert msr.header.byteorder == simplemseed.miniseed.LITTLE_ENDIAN
        outmsr = simplemseed.unpackMiniseedRecord(recordBytes)
        assert outmsr.header.byteorder == msr.header.byteorder
        assert msr.codes() == outmsr.codes()
        assert msr.starttime() == outmsr.starttime()
        outdata = outmsr.decompressed()
        assert len(outdata) == len(data)
        assert len(outdata) == msr.header.numSamples
        for i in range(len(data)):
            assert data[i] == outdata[i]

    def test_create_double(self):
        data = numpy.fromfunction(lambda i: (i % 99 - 49.2), (50,), dtype=numpy.float64)
        network = "XX"
        station = "TEST"
        location = "00"
        channel = f"HNZ"
        starttime = "2024-01-01T15:13:55.123400Z"
        numsamples = len(data)
        sampleRate = 200

        msh = simplemseed.MiniseedHeader(
            network, station, location, channel, starttime, numsamples, sampleRate
        )
        msr = simplemseed.MiniseedRecord(msh, data)
        assert msr.header.byteorder == simplemseed.miniseed.LITTLE_ENDIAN
        recordBytes = msr.pack()
        assert msr.header.encoding == simplemseed.seedcodec.DOUBLE
        assert msr.header.byteorder == simplemseed.miniseed.LITTLE_ENDIAN
        outmsr = simplemseed.unpackMiniseedRecord(recordBytes)
        assert outmsr.header.byteorder == msr.header.byteorder
        assert msr.codes() == outmsr.codes()
        assert msr.starttime() == outmsr.starttime()
        outdata = outmsr.decompressed()
        assert len(outdata) == len(data)
        assert len(outdata) == msr.header.numSamples
        for i in range(len(data)):
            assert data[i] == outdata[i]


if __name__ == "__main__":
    TestMseed2().test_read()
