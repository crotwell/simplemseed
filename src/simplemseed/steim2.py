
import struct
from typing import Union
import numpy as np

from .exceptions import (
    CodecException,
    SteimException,
)
from .steimframeblock import SteimFrameBlock
from .steimframeblock import getUint32, getInt32


"""

 Class for decoding or encoding Steim2-compressed data blocks
 to or from an array of integer values.
<p>
Steim compression scheme Copyrighted by Dr. Joseph Steim.</p>
<dl>
<dt>Reference material found in:</dt>
<dd>
Appendix B of SEED Reference Manual, 2nd Ed., pp. 119-125
<i>Federation of Digital Seismic Networks, et al.</i>
February, 1993
</dd>
<dt>Coding concepts gleaned from code written by:</dt>
<dd>Guy Stewart, IRIS, 1991</dd>
<dd>Tom McSweeney, IRIS, 2000</dd>
<dd>Doug Neuhauser, UC Berkeley, 2010</dd>
<dd>Kevin Frechette, ISTI, 2010</dd>
</dl>
 *
   Converted from Java to Python...

@author Philip Crotwell (U South Carolina)
@author Robert Casey (IRIS DMC)
@author Doug Neuhauser (UC Berkeley)
@author Kevin Frechette (ISTI)
@version 9/13/2010
 """


#
#  Decode the indicated number of samples from the provided byte array and
#  return an integer array of the decompressed values.  Being differencing
#  compression, there may be an offset carried over from a previous data
#  record.  This offset value can be placed in <b>bias</b>, otherwise leave
#  the value as 0.
#
#  @param dataBytes input byte array to be decoded
#  @param numSamples the number of samples that can be decoded from array
#  @param littleEndian if True, endian-ness is little
#  @param bias the first difference value will be computed from this value.
#  If set to 0, the method will attempt to use the X(0) constant instead.
#  @returns int array of length <b>numSamples</b>.
#  @throws SteimException - encoded data length is not multiple of 64
#  bytes.


def decodeSteim2(
    dataBytes: bytearray,
    numSamples: int,
    bias: int = 0,
):
    if len(dataBytes) % 64 != 0:
        raise CodecException(
            f"encoded data length is not multiple of 64 bytes ({len(dataBytes)})",
        )

    dt = np.dtype(np.int32)
    samples = np.zeros((numSamples,), dt)

    numFrames = len(dataBytes) // 64
    current = 0
    start = 0
    firstData = 0
    lastValue = 0

    for i in range(numFrames):
        tempSamples = extractSteim2Samples(
            dataBytes, i * 64, False
        )  # returns only differences except for frame 0

        firstData = 0  # d(0) is byte 0 by default

        if i == 0:
            # special case for first frame
            lastValue = bias  # assign our X(-1)

            # x0 and xn are in 1 and 2 spots
            start = tempSamples[1]  # X(0) is byte 1 for frame 0

            # end = tempSamples[2]    # X(n) is byte 2 for frame 0
            firstData = 3  # d(0) is byte 3 for frame 0

            # if bias was zero, then we want the first sample to be X(0) constant
            if bias == 0:
                lastValue = start - tempSamples[3]  # X(-1) = X(0) - d(0)

        for j in range(firstData, len(tempSamples)):
            if current >= numSamples:
                break
            samples[current] = lastValue + tempSamples[j]  # X(n) = X(n-1) + d(n)

            lastValue = samples[current]
            current += 1
    # end for each frame...

    if current != numSamples:
        raise CodecException(
            f"Number of samples decompressed doesn't match number in header: {current} != {numSamples}"
        )

    # ignore last sample check???
    # if (end != samples[numSamples-1]):
    #    raise SteimException("Last sample decompressed doesn't match value x(n) value in Steim2 record: "+samples[numSamples-1]+" != "+end)
    #
    return samples


#
# Extracts differences from the next 64 byte frame of the given compressed
# byte array (starting at offset) and returns those differences in an int
# array.
# An offset of 0 means that we are at the first frame, so include the header
# bytes in the returned int array...else, do not include the header bytes
# in the returned array.
#
# @param dataBytes byte array of compressed data differences
# @param offset index to begin reading compressed bytes for decoding
# @param littleEndian  the endian-ness of the compressed bytes being read
# @returns integer array of difference (and constant) values


def extractSteim2Samples(
    dataBytes: bytearray,
    offset: int,
    littleEndian: bool,
) -> np.ndarray:
    # get nibbles
    nibbles = getUint32(dataBytes, offset, False)  # steim always big endian for nibbles
    currNibble = 0
    dnib = 0
    dt = np.dtype(np.int32)
    temp = np.zeros((106,), dt)  # max 106 = 7 samples * 15 long words + 1 nibble int

    currNum = 0
    diffCount = 0  # number of differences

    bitSize = 0  # bit size

    headerSize = 0  # number of header/unused bits at top

    headNib = (nibbles >> 30) & 0x03
    if headNib != 0:
        raise CodecException(f"nibble bytes must start with 00, but was {headNib:02b}")

    for i in range(16):
        currNibble = (nibbles >> (30 - i * 2)) & 0x03

        # switch (currNibble):
        if currNibble == 0:
            # "0 means header info"
            # only include header info if offset is 0
            if offset == 0:
                temp[currNum] = getInt32(dataBytes, offset + i * 4, False)
                currNum += 1

        elif currNibble == 1:

            endianChar = "<" if littleEndian else ">"
            vals = struct.unpack(
                endianChar + "bbbb", dataBytes[offset + i * 4 : offset + i * 4 + 4]
            )
            # print(f"1 means 4 one byte differences {currNum} {vals}")
            for k in range(4):
                temp[currNum + k] = vals[k]
            currNum += 4

        elif currNibble == 2:
            tempInt = getUint32(dataBytes, offset + i * 4, False)
            dnib = (tempInt >> 30) & 0x03

            # switch (dnib):
            if dnib == 1:
                headerSize = 2
                diffCount = 1
                bitSize = 30
                dnibVals = extractDnibValues(tempInt, headerSize, diffCount, bitSize)
                temp[currNum] = dnibVals[0]
                currNum += diffCount
                # print(f"2,1 means 1 thirty bit difference {dnibVals}")

            elif dnib == 2:
                headerSize = 2
                diffCount = 2
                bitSize = 15
                dnibVals = extractDnibValues(tempInt, headerSize, diffCount, bitSize)
                temp[currNum] = dnibVals[0]
                temp[currNum + 1] = dnibVals[1]
                currNum += diffCount
                # print(f"2,2 means 2 fifteen bit differences {dnibVals}")

            elif dnib == 3:
                headerSize = 2
                diffCount = 3
                bitSize = 10
                dnibVals = extractDnibValues(tempInt, headerSize, diffCount, bitSize)
                temp[currNum] = dnibVals[0]
                temp[currNum + 1] = dnibVals[1]
                temp[currNum + 2] = dnibVals[2]
                currNum += diffCount
                # print(f"2,3 means 3 ten bit differences {tempInt:032b} {dnibVals}")

            else:
                raise CodecException(
                    f"Unknown case currNibble={currNibble} dnib={dnib} for chunk {i} offset {offset}, nibbles: {nibbles}",
                )

        elif currNibble == 3:
            tempInt = getUint32(dataBytes, offset + i * 4, False)
            dnib = (tempInt >> 30) & 0x03
            # for case 3, we are going to use a for-loop formulation that
            # accomplishes the same thing as case 2, just less verbose.
            diffCount = 0  # number of differences
            bitSize = 0  # bit size
            headerSize = 0  # number of header/unused bits at top

            # switch (dnib):
            if dnib == 0:
                # print(f"3,0 means 5 six bit differences: {tempInt:032b}")
                headerSize = 2
                diffCount = 5
                bitSize = 6

            elif dnib == 1:
                # print(f"3,1 means 6 five bit differences")
                headerSize = 2
                diffCount = 6
                bitSize = 5

            elif dnib == 2:
                # print(f"3,2 means 7 four bit differences, with 2 unused bits")
                headerSize = 4
                diffCount = 7
                bitSize = 4

            else:
                raise CodecException(
                    f"Steim2 Unknown case currNibble={currNibble} dnib={dnib} for chunk {i} offset {offset}, nibbles: {nibbles:032b} int:{tempInt:032b}",
                )

            if diffCount > 0:
                for d in range(diffCount):
                    # for-loop formulation
                    val = (tempInt << (headerSize + d * bitSize)) & 0xFFFFFFFF
                    val = val - (1 << 32) if val >= (1 << 31) else val
                    temp[currNum] = val >> ((diffCount - 1) * bitSize + headerSize)
                    currNum += 1

        else:
            raise CodecException(f"Unknown case currNibble={currNibble}")

    return temp[0:currNum]


def extractDnibValues(tempInt, headerSize, diffCount, bitSize):
    out = [0] * diffCount
    if diffCount > 0:
        for d in range(diffCount):
            # for-loop formulation
            val = (tempInt << (headerSize + d * bitSize)) & 0xFFFFFFFF
            val = val - (1 << 32) if val >= (1 << 31) else val
            out[d] = val >> ((diffCount - 1) * bitSize + headerSize)
    return out


def encodeSteim2(samples: Union[np.ndarray, list[int]], frames: int = 0, bias: np.int32 = 0):
    """

    Encode the array of integer values into a Steim 2 * compressed byte frame block.
    For miniseed2 you should not create a byte block any greater than 63 64-byte frames.
    <b>frames</b> represents the number of frames to be written.
    This number should be determined from the desired logical record length
    <i>minus</i> the data offset from the record header (modulo 64)
    If <b>samples</b> is exhausted before all frames are filled, the remaining frames
    will be None.
    <b>bias</b> is a value carried over from a previous data record, representing
    X(-1)...set to 0 otherwise
    @param samples the data points represented as signed integers
    @param frames the number of Steim frames to use in the encoding
    @param bias offset for use as a constant for the first difference, otherwise
    set to 0
    @return SteimFrameBlock containing encoded byte array
    @throws SteimException samples array is zero size
    @throws SteimException number of frames is not a positive value
    @throws SteimException cannot encode more than 63 frames
    """
    return encodeSteim2FrameBlock(samples, frames, bias).pack()


def encodeSteim2FrameBlock(
    samples: Union[np.ndarray, list[int]], frames: int = 0, bias: np.int32 = 0
) -> SteimFrameBlock:
    if len(samples) == 0:
        raise SteimException("samples array is zero size")

    if frames < 0:
        raise SteimException("number of frames is  a negative value")

    # check if numpy array
    # check if numpy array
    if isinstance(samples, np.ndarray):
        if len(np.shape(samples)) != 1:
            raise SteimException(f"numpy array not one dimensional: {np.shape(samples)}")
        if np.issubdtype(samples.dtype, np.floating):
            raise SteimException(f"Cannot steim2 compress floating point numpy array: {samples.dtype}")
        if np.issubdtype(samples.dtype, np.integer) and \
                not np.can_cast(samples.dtype, np.int32, casting="safe"):
            if abs(np.max(samples)) > np.iinfo(np.int32).max:
                raise SteimException(f"max value of numpy array, {np.max(samples)} cannot fit into 32 bit integer")
            samples = samples.astype(np.int32)
    if isinstance(samples[0], float):
        raise SteimException(f"Cannot steim2 compress floating point list, first sample is float: {samples[0]}")

    # all encoding will be contained within a frame block
    # Steim encoding 2
    frameBlock = SteimFrameBlock(frames, 2)
    #
    # pass through the list of samples, and pass encoded words
    # to frame block
    # end loop if we run out of samples or the frame block
    # fills up
    # .............................................................
    # first initialize the first frame with integration constant X(0)
    # and reverse integration constant X(N)
    # ...reverse integration constant may need to be changed if
    # the frameBlock fills up.
    frameBlock.addEncodedWord(
        np.int32(samples[0]), 0, 0
    )  # X(0) -- first sample value
    frameBlock.addEncodedWord(
        np.int32(samples[len(samples) - 1]), 0, 0
    )  # X(N) -- last sample value
    #
    # now begin looping over differences
    sampleIndex = 0  # where we are in the sample array
    diff = [0] * 7  # store differences here
    minbits = [0] * 7  # store min # bits required to represent diff here
    points_remaining = 0  # the number of points remaining
    while sampleIndex < len(samples):
        # look at the next (up to seven) differences
        # and assess the number that can be put into
        # the upcoming word
        points_remaining = 0
        for i in range(7):
            if sampleIndex + i < len(samples):
                # as long as there are still samples
                # get next difference  X[i] - X[i-1]
                if sampleIndex + i == 0:
                    # special case for d(0) = x(0) - x(-1).
                    diff[0] = np.int32(samples[0]) - np.int32(bias)
                else:
                    diff[i] = samples[sampleIndex + i] - samples[sampleIndex + i - 1]

                # and increment the counter
                minbits[i] = minBitsNeeded(diff[i])
                points_remaining += 1
            else:
                break  # no more samples, leave for loop
            # end for (0..7)

        # Determine the packing required for the next compressed word in the SteimFrame.
        nbits = bitsForPack(minbits, points_remaining)

        # generate the encoded word and the nibble value
        ndiff = 0  # the number of differences
        bitmask = np.int32(0)
        submask = np.int32(0)
        nibble = 0
        if nbits == 4:
            ndiff = 7
            bitmask = np.int32(0x0000000F)
            submask = np.int32(0x02)
            nibble = 3
        elif nbits == 5:
            ndiff = 6
            bitmask = np.int32(0x0000001F)
            submask = np.int32(0x01)
            nibble = 3
        elif nbits == 6:
            ndiff = 5
            bitmask = np.int32(0x0000003F)
            submask = np.int32(0x00)
            nibble = 3
        elif nbits == 8:
            ndiff = 4
            bitmask = np.int32(0x000000FF)
            submask = np.int32(0)
            nibble = 1
        elif nbits == 10:
            ndiff = 3
            bitmask = np.int32(0x000003FF)
            submask = np.int32(0x03)
            nibble = 2
        elif nbits == 15:
            ndiff = 2
            bitmask = np.int32(0x00007FFF)
            submask = np.int32(0x02)
            nibble = 2
        elif nbits == 30:
            ndiff = 1
            bitmask = np.int32(0x3FFFFFFF)
            submask = np.int32(0x01)
            nibble = 2
        else:
            raise SteimException(
                "Unable to encode " + nbits + " bit difference in Steim2 format"
            )

        word = steimPackWord(diff, nbits, ndiff, bitmask, submask)

        # add the encoded word to the frame block
        if frameBlock.addEncodedWord(word, ndiff, nibble):
            # frame block is full (but the value did get added)
            # so modify reverse integration constant to be the very last value added
            # and break out of loop (read no more samples)
            frameBlock.setXsubN(np.int32(samples[sampleIndex + ndiff - 1]))  # X(N)
            break

        # increment the sampleIndex by the number of differences
        sampleIndex += ndiff
    # end while next sample
    return frameBlock


def minBitsNeeded(diff: int):
    minbits = 0
    if -8 <= diff < 8:
        minbits = 4
    elif  -16 <= diff < 16:
        minbits = 5
    elif -32 <= diff < 32:
        minbits = 6
    elif -128 <= diff < 128:
        minbits = 8
    elif -512 <= diff < 512:
        minbits = 10
    elif -16384 <= diff < 16384:
        minbits = 15
    elif -536870912 <= diff < 536870912:
        minbits = 30
    else:
        minbits = 32
    return minbits


def bitsForPack(minbits: list[int], points_remaining: int):
    if (
        points_remaining >= 7
        and (minbits[0] <= 4)
        and (minbits[1] <= 4)
        and (minbits[2] <= 4)
        and (minbits[3] <= 4)
        and (minbits[4] <= 4)
        and (minbits[5] <= 4)
        and (minbits[6] <= 4)
    ):
        return 4
    if (
        points_remaining >= 6
        and (minbits[0] <= 5)
        and (minbits[1] <= 5)
        and (minbits[2] <= 5)
        and (minbits[3] <= 5)
        and (minbits[4] <= 5)
        and (minbits[5] <= 5)
    ):
        return 5
    if (
        points_remaining >= 5
        and (minbits[0] <= 6)
        and (minbits[1] <= 6)
        and (minbits[2] <= 6)
        and (minbits[3] <= 6)
        and (minbits[4] <= 6)
    ):
        return 6
    if (
        points_remaining >= 4
        and (minbits[0] <= 8)
        and (minbits[1] <= 8)
        and (minbits[2] <= 8)
        and (minbits[3] <= 8)
    ):
        return 8
    if (
        points_remaining >= 3
        and (minbits[0] <= 10)
        and (minbits[1] <= 10)
        and (minbits[2] <= 10)
    ):
        return 10
    if points_remaining >= 2 and (minbits[0] <= 15) and (minbits[1] <= 15):
        return 15
    if points_remaining >= 1 and (minbits[0] <= 30):
        return 30
    return 32


def steimPackWord(diff: list[int], nbits: int, ndiff: int, bitmask: np.int32, submask: np.int32) -> np.int32:
    """
    Pack Steim2 compressed word with optional submask.
    @param diff the differences
    @param nbits the number of bits
    @param ndiff the number of differences
    @param bitmask the bit mask
    @param submask the sub mask or 0 if none
    """
    val = np.int32(0)
    i = 0
    while i < ndiff:
        val = np.bitwise_or(np.left_shift(val, np.int32(nbits)) , np.bitwise_and(np.int32(diff[i]), bitmask))
        i += 1
    if submask != 0:
        val = np.bitwise_or(val, np.left_shift(submask, np.int32(30)))
    return val
