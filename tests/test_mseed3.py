import pytest
import json
import os
import simplemseed
from datetime import datetime
from pathlib import Path

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
                if rec.header.encoding != 0:
                    # encoding == 0 is Text, with no structure, so cannot decompress
                    data = rec.decompress()
                    assert len(data) > 0, filename
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
                        assert (
                            jsonrec["PublicationVersion"]
                            == rec.header.publicationVersion
                        )
                        assert (
                            jsonrec["SID"] == rec.identifier
                        ), f"sid {jsonrec['SID']}  {rec.identifier}"
                        jsondata = jsonrec["Data"]
                        assert len(jsondata) == len(data)
                        for i in range(len(jsondata)):
                            assert (
                                jsondata[i] == data[i]
                            ), f"{i}  {jsondata[i]} != {data[i]}"

    def test_roundtrip(self):
        values = [3, 1, -1, 2000]
        header = simplemseed.MSeed3Header()
        header.encoding = simplemseed.seedcodec.INTEGER
        header.starttime = "2024-01-02T15:13:55.123456Z"
        header.sampleRatePeriod = -1
        header.numSamples = len(values)
        identifier = "FDSN:XX_FAKE__H_H_Z"
        record = simplemseed.MSeed3Record(header, identifier, values)
        recordBytes = record.pack()
        outRecord = simplemseed.unpackMSeed3Record(recordBytes)
        assert identifier == outRecord.identifier
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
            assert len(decompRec.encodedData.dataBytes) == 4 * rec.header.numSamples

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

    def test_match(self):
        filename = f"{TEST_DIR}/bird_jsc.ms3"
        with open(filename, "rb") as infile:
            p = None
            recList = []
            for rec in simplemseed.readMSeed3Records(infile, match="BIRD_.*_H_H_Z"):
                recList.append(rec)
        assert len(recList) == 13

if __name__ == "__main__":
    TestMSeed3().test_ref_data()
