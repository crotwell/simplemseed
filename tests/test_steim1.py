
import pytest
import simplemseed


class TestSteim1:

    def test_ref_data(self):
        data = [1, 2, -10, 45, -999, 4008]
        numSamples = len(data)
        littleEndian=False
        encoded = simplemseed.encodeSteim1(data)
        decoded = simplemseed.decodeSteim1(encoded, numSamples, littleEndian, 0)
        assert len(decoded) == len(data)
        for i in range(len(data)):
            assert decoded[i] == data[i]
