import pytest
import simplemseed
import math


class TestSteim1:

    def test_simple_encode_data(self):
        data = [1, 2, -10, 45, -999, 4008]+[129]*1000
        numSamples = len(data)
        littleEndian = False
        encoded = simplemseed.encodeSteim1(data)
        decoded = simplemseed.decodeSteim1(encoded, numSamples, littleEndian, 0)
        assert len(decoded) == len(data)
        for i in range(len(data)):
            assert decoded[i] == data[i]


    def test_sized_encode_data(self):
        data = [1, 2, -10, 45, -999, 4008]+ [(int)(499*math.sin(i)) for i in range(100000)]
        totalNumSamples = len(data)
        littleEndian = False
        idx = 0
        while len(data) > 0:
            frameBlock = simplemseed.encodeSteim1FrameBlock(data, 63)
            assert len(frameBlock.steimFrameList)<= 63
            encoded = frameBlock.pack()
            assert len(encoded) == len(frameBlock.steimFrameList)*64
            decoded = simplemseed.decodeSteim1(encoded, frameBlock.numSamples, littleEndian, 0)
            assert len(decoded) == frameBlock.numSamples
            for i in range(frameBlock.numSamples):
                assert decoded[i] == data[i]
            idx += frameBlock.numSamples
            print(f"packed {frameBlock.numSamples}, idx: {idx} of {totalNumSamples}")
            data = data[frameBlock.numSamples:]
        assert idx == totalNumSamples
