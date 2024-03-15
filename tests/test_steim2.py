import pytest
import simplemseed


class TestSteim2:

    def test_ref_data(self):
        data = [1, 2, -10, 45, -999, 4008]+ [47]*1000
        numSamples = len(data)
        littleEndian = False
        encoded = simplemseed.encodeSteim2(data)
        decoded = simplemseed.decodeSteim2(encoded, numSamples, littleEndian, 0)
        assert len(decoded) == len(data)
        for i in range(len(data)):
            assert decoded[i] == data[i]
