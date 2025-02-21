import pytest
import simplemseed
import math

import numpy as np

class TestSteim2:

    def test_simple_encode_data(self):
        data = [1, 2, -10, 45, -999, 4008] + [47] * 1000
        numSamples = len(data)
        encoded = simplemseed.encodeSteim2(data)
        decoded = simplemseed.decodeSteim2(encoded, numSamples, 0)
        assert len(decoded) == len(data)
        for i in range(len(data)):
            assert decoded[i] == data[i]

    def test_sized_encode_data(self):
        data = [1, 2, -10, 45, -999, 4008] + [
            (int)(499 * math.sin(i)) for i in range(100000)
        ]
        totalNumSamples = len(data)
        idx = 0
        while len(data) > 0:
            frameBlock = simplemseed.encodeSteim2FrameBlock(data, 63)
            assert len(frameBlock.steimFrameList) <= 63
            encoded = frameBlock.pack()
            decoded = simplemseed.decodeSteim2(
                encoded, frameBlock.numSamples, 0
            )
            assert len(decoded) == frameBlock.numSamples
            for i in range(frameBlock.numSamples):
                assert decoded[i] == data[i]
            idx += frameBlock.numSamples
            print(f"packed {frameBlock.numSamples}, idx: {idx} of {totalNumSamples}")
            data = data[frameBlock.numSamples :]
        assert idx == totalNumSamples
