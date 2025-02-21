import pytest
import json
import numpy
import os
import sys
import simplemseed
from datetime import datetime
from pathlib import Path

import numpy as np

TEST_DIR = Path(__file__).parent

githubUrl = "git clone https://github.com/FDSN/miniSEED3.git"

# ref data from https://github.com/FDSN/miniSEED3
ref_data_dir = f"{TEST_DIR}/miniSEED3/reference-data"
ref_data_list = [
    f"{ref_data_dir}/reference-detectiononly.mseed3",
    f"{ref_data_dir}/reference-sinusoid-FDSN-All.mseed3",
    f"{ref_data_dir}/reference-sinusoid-FDSN-Other.mseed3",
    f"{ref_data_dir}/reference-sinusoid-TQ-TC-ED.mseed3",
    f"{ref_data_dir}/reference-sinusoid-float32.mseed3",
    f"{ref_data_dir}/reference-sinusoid-float64.mseed3",
    f"{ref_data_dir}/reference-sinusoid-int16.mseed3",
    f"{ref_data_dir}/reference-sinusoid-int32.mseed3",
    f"{ref_data_dir}/reference-sinusoid-steim1.mseed3",
    f"{ref_data_dir}/reference-sinusoid-steim2.mseed3",
    f"{ref_data_dir}/reference-text.mseed3",
]


# mseed3 via
# casee_two.ms3
# https://service.iris.edu/fdsnws/dataselect/1/query?net=CO&sta=CASEE&loc=00&cha=HHZ&starttime=2023-06-17T04:53:54.468&endtime=2023-06-17T04:55:00&format=miniseed3&nodata=404
# bird_jsc.ms3
# curl -o 'bird_jsc.ms3' 'https://service.iris.edu/fdsnws/dataselect/1/query?net=CO&sta=BIRD,JSC&cha=HH?&starttime=2024-02-06T11:30:00&endtime=2024-02-06T11:30:30&format=miniseed3&nodata=404'


class TestMSeed3:

    def test_ref_data(self):
        for filename in ref_data_list:
            if not os.path.exists(filename):
                assert False, f"load reference data for {filename} from {githubUrl}"
            with open(filename, "rb") as infile:
                rec_bytes = infile.read()
                rec = simplemseed.mseed3.unpackMSeed3Record(rec_bytes)
                jsonfilename = filename.replace(".mseed3", ".json")
                with open(jsonfilename, "r") as injson:
                    jsonrec = json.load(injson)[0]
                assert jsonrec["FormatVersion"] == rec.header.formatVersion
                assert jsonrec["EncodingFormat"] == rec.header.encoding
                assert (
                    jsonrec["SampleRate"] == rec.header.sampleRate
                ), f"{jsonrec['SampleRate']} != {rec.header.sampleRate}"
                assert jsonrec["SampleCount"] == rec.header.numSamples
                assert (
                    jsonrec["CRC"] == rec.header.crcAsHex()
                ), f"{jsonrec['CRC']} {rec.header.crcAsHex()}"
                assert jsonrec["PublicationVersion"] == rec.header.publicationVersion
                assert (
                    jsonrec["SID"] == rec.identifier
                ), f"sid {jsonrec['SID']}  {rec.identifier}"
                if "ExtraHeaders" in jsonrec:
                    assert jsonrec["ExtraHeaders"] == rec.eh
                if rec.header.encoding != 0:
                    # encoding == 0 is Text, with no structure, so cannot decompress
                    data = rec.decompress()
                    jsondata = jsonrec["Data"]
                    assert len(data) > 0, filename
                    assert len(jsondata) == len(data)
                    for i in range(len(jsondata)):
                        assert (
                            jsondata[i] == data[i]
                        ), f"{i}  {jsondata[i]} != {data[i]}"

    def test_roundtrip_float(self):
        data = numpy.fromfunction(lambda i: (i % 99 - 49), (400,), dtype=numpy.float32)
        header = simplemseed.MSeed3Header()
        header.starttime = "2024-01-02T15:13:55.123456Z"
        header.sampleRatePeriod = -1
        header.numSamples = len(data)
        identifier = simplemseed.FDSNSourceId.createUnknown(header.sampleRate)
        record = simplemseed.MSeed3Record(header, identifier, data)
        recordBytes = record.pack()
        assert record.header.encoding == simplemseed.seedcodec.FLOAT
        outRecord = simplemseed.unpackMSeed3Record(recordBytes)
        assert identifier == outRecord.parseIdentifier()
        decomp_data = outRecord.decompress()
        assert record.details() == outRecord.details()
        assert len(decomp_data) == len(data)
        for i in range(len(decomp_data)):
            assert decomp_data[i] == data[i], f"{i} msi:{decomp_data[i]} != {data[i]} "

    def test_roundtrip_steim1(self):
        values = data = numpy.fromfunction(
            lambda i: (i % 99 - 49), (100,), dtype=numpy.int32
        )
        header = simplemseed.MSeed3Header()
        encodedValues = simplemseed.encodeSteim1(values)
        header.encoding = simplemseed.seedcodec.STEIM1
        header.starttime = "2024-01-02T15:13:55.123456Z"
        header.sampleRatePeriod = -1 # neg is period, so 1 sps
        header.numSamples = len(values)
        identifier = simplemseed.FDSNSourceId.createUnknown(header.sampleRate)
        record = simplemseed.MSeed3Record(header, identifier, encodedValues)
        recordBytes = record.pack()
        outRecord = simplemseed.unpackMSeed3Record(recordBytes)
        assert identifier == outRecord.parseIdentifier()
        assert header.encoding == outRecord.header.encoding
        assert simplemseed.seedcodec.STEIM1 == outRecord.header.encoding
        decomp_data = outRecord.decompress()
        assert record.details() == outRecord.details()
        assert len(decomp_data) == len(values)
        for i in range(len(decomp_data)):
            assert (
                decomp_data[i] == values[i]
            ), f"{i} msi:{decomp_data[i]} != {values[i]} "

    def test_roundtrip_steim2(self):
        values = [3, 1, -1, 2000] + []
        header = simplemseed.MSeed3Header()
        encodedValues = simplemseed.encodeSteim2(values)
        header.encoding = simplemseed.seedcodec.STEIM2
        header.starttime = "2024-01-02T15:13:55.123456Z"
        header.sampleRatePeriod = -1 # neg is period, so 1 sps
        header.numSamples = len(values)
        identifier = simplemseed.FDSNSourceId.createUnknown(header.sampleRate)
        record = simplemseed.MSeed3Record(header, identifier, encodedValues)
        recordBytes = record.pack()
        outRecord = simplemseed.unpackMSeed3Record(recordBytes)
        assert header.encoding == outRecord.header.encoding
        assert simplemseed.seedcodec.STEIM2 == outRecord.header.encoding
        assert identifier == outRecord.parseIdentifier()
        decomp_data = outRecord.decompress()
        assert record.details() == outRecord.details()
        assert len(decomp_data) == len(values)
        for i in range(len(decomp_data)):
            assert (
                decomp_data[i] == values[i]
            ), f"{i} msi:{decomp_data[i]} != {values[i]} "

    def test_decompressRecord(self):
        filename = f"{ref_data_dir}/reference-sinusoid-steim1.mseed3"
        with open(filename, "rb") as infile:
            rec_bytes = infile.read()
            rec = simplemseed.mseed3.unpackMSeed3Record(rec_bytes)
            decompRec = rec.decompressedRecord()
            assert decompRec.header.encoding == simplemseed.seedcodec.INTEGER
            assert rec.header.numSamples == decompRec.header.numSamples
            assert len(decompRec.encodedDataBytes()) == 4 * rec.header.numSamples

    def test_starttime(self):
        header = simplemseed.MSeed3Header()
        start = "2024-01-02T15:13:55.123456Z"
        header.starttime = start
        assert header.year == 2024
        assert header.dayOfYear == 2
        assert header.hour == 15
        assert header.minute == 13
        assert header.second == 55
        assert header.nanosecond == 123456000
        assert simplemseed.isoWZ(header.starttime) == start
        header.samplePeriod = 2
        assert header.samplePeriod == 2
        assert header.sampleRate == 1 / 2

    def test_long_fdsnsourceid(self):
        values = [3, 1, -1, 2000]
        header = simplemseed.MSeed3Header()
        header.encoding = simplemseed.seedcodec.INTEGER
        header.starttime = "2024-01-02T15:13:55.123456Z"
        header.sampleRatePeriod = -1
        header.numSamples = len(values)
        identifier = "FDSN:XX2024_REALFAKE_012345_H_HRQ_Z"
        record = simplemseed.MSeed3Record(header, identifier, values)
        recordBytes = record.pack()
        outRecord = simplemseed.unpackMSeed3Record(recordBytes)
        assert identifier == outRecord.identifier

    def test_merge(self):
        filename = f"{TEST_DIR}/casee_two.ms3"
        with open(filename, "rb") as infile:
            p = None
            recList = []
            for rec in simplemseed.readMSeed3Records(infile):
                recList.append(rec)
                decompRec = rec.decompressedRecord()
                mList = simplemseed.mseed3merge(p, decompRec)
                assert len(mList) == 1
                p = mList[0]
            assert len(recList) == 2
            assert p.header.encoding == simplemseed.seedcodec.INTEGER
            totNumSamp = 0
            for r in recList:
                totNumSamp += r.header.numSamples
            assert p.header.numSamples == totNumSamp
        # now test merge in read
        filename = f"{TEST_DIR}/casee_two.ms3"
        mergeRecList = []
        with open(filename, "rb") as infile:
            for rec in simplemseed.readMSeed3Records(infile, merge=True):
                mergeRecList.append(rec)
        assert len(mergeRecList) == 1
        p = mergeRecList[0]
        assert p.header.encoding == simplemseed.seedcodec.INTEGER
        assert p.header.numSamples == totNumSamp

    def test_match(self):
        filename = f"{TEST_DIR}/bird_jsc.ms3"
        with open(filename, "rb") as infile:
            p = None
            recList = []
            for rec in simplemseed.readMSeed3Records(infile, matchsid="BIRD_.*_H_H_Z"):
                recList.append(rec)
        assert len(recList) == 13

    def test_array_to_encoding(self):
        assert (
            simplemseed.seedcodec.mseed3EncodingFromArrayTypecode("h", 2)
            == simplemseed.seedcodec.SHORT
        )
        assert (
            simplemseed.seedcodec.mseed3EncodingFromArrayTypecode("i", 2)
            == simplemseed.seedcodec.SHORT
        )
        assert (
            simplemseed.seedcodec.mseed3EncodingFromArrayTypecode("l", 2)
            == simplemseed.seedcodec.SHORT
        )
        assert (
            simplemseed.seedcodec.mseed3EncodingFromArrayTypecode("h", 4)
            == simplemseed.seedcodec.INTEGER
        )
        assert (
            simplemseed.seedcodec.mseed3EncodingFromArrayTypecode("i", 4)
            == simplemseed.seedcodec.INTEGER
        )
        assert (
            simplemseed.seedcodec.mseed3EncodingFromArrayTypecode("l", 4)
            == simplemseed.seedcodec.INTEGER
        )

        assert (
            simplemseed.seedcodec.mseed3EncodingFromArrayTypecode("f", 4)
            == simplemseed.seedcodec.FLOAT
        )
        assert (
            simplemseed.seedcodec.mseed3EncodingFromArrayTypecode("f", 8)
            == simplemseed.seedcodec.DOUBLE
        )
        assert (
            simplemseed.seedcodec.mseed3EncodingFromArrayTypecode("d", 8)
            == simplemseed.seedcodec.DOUBLE
        )

    def testCreateFromBigEndian(self):
        data = numpy.array([1, 256, 8755, -16245, 65000, -65000], dtype=numpy.dtype('<i4'))
        bigdata = data.view(data.dtype.newbyteorder('>')).byteswap()
        assert(data.dtype.byteorder == '<'
               or (data.dtype.byteorder == '=' and sys.byteorder == 'little'))
        assert(bigdata.dtype.byteorder == '>')
        for i in range(len(data)):
            assert(data[i] == bigdata[i])

        header = simplemseed.MSeed3Header()
        identifier = simplemseed.FDSNSourceId.createUnknown(header.sampleRate)
        record = simplemseed.MSeed3Record(header, identifier, data)
        recordBytes = record.pack()
        bigrecord = simplemseed.MSeed3Record(header, identifier, bigdata)
        bigrecordBytes = bigrecord.pack()
        outRecord = simplemseed.unpackMSeed3Record(recordBytes)
        assert identifier == outRecord.parseIdentifier()
        decomp_data = outRecord.decompress()

        bigoutRecord = simplemseed.unpackMSeed3Record(bigrecordBytes)
        assert identifier == bigoutRecord.parseIdentifier()
        bigdecomp_data = bigoutRecord.decompress()
        for i in range(len(data)):
            assert data[i] == decomp_data[i]
            assert data[i] == bigdecomp_data[i]

    def testInt64ToSteim(self):
        "int64 numpy array, but values small enough to be int32"
        data = np.array([1, 2, -3, -1], dtype=np.int64)
        header = simplemseed.MSeed3Header()
        header.numSamples = len(data)
        encodedValues = simplemseed.encodeSteim2(data)
        header.encoding = simplemseed.seedcodec.STEIM2
        identifier = simplemseed.FDSNSourceId.createUnknown(header.sampleRate)
        record = simplemseed.MSeed3Record(header, identifier, encodedValues)
        recordBytes = record.pack()
        outRecord = simplemseed.unpackMSeed3Record(recordBytes)
        assert outRecord.header.numSamples == len(data)
        assert outRecord.header.encoding == simplemseed.seedcodec.STEIM2
        decomp_data = outRecord.decompress()
        assert np.array_equal(data.astype(np.int32), decomp_data)




if __name__ == "__main__":
    TestMSeed3().test_ref_data()
