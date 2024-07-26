
import struct
import numpy as np

from .exceptions import (
    CodecException,
    SteimException,
)
from .steimframeblock import SteimFrameBlock
from .steimframeblock import getUint32, getInt32

#
#  Decode the indicated number of samples from the provided byte array and
#  return an integer array of the decompressed values.  Being differencing
#  compression, there may be an offset carried over from a previous data
#  record.  This offset value can be placed in <b>bias</b>, otherwise leave
#  the value as 0.
#
#  @param dataBytes input bytes to be decoded
#  @param numSamples the number of samples that can be decoded from array
#  <b>b</b>
#  @param littleEndian if True, dataBytes is little-endian (intel byte order) <b>b</b>.
#  @param bias the first difference value will be computed from this value.
#  If set to 0, the method will attempt to use the X(0) constant instead.
#  @returns int array of length <b>numSamples</b>.
#  @throws CodecException - encoded data length is not multiple of 64
#  bytes.

ONE_BYTE = np.uint32(0xFF)
TWO_BYTE = np.uint32(0xFFFF)
TWO_BITS = np.uint32(0x3)

def decodeSteim1(
    dataBytes: bytearray,
    numSamples,
    bias = np.int32(0),
):
    # Decode Steim1 compression format from the provided byte array, which contains numSamples number
    # of samples.  bias represents
    # a previous value which acts as a starting constant for continuing differences integration.  At the
    # very start, bias is set to 0.
    if len(dataBytes) % 64 != 0:
        raise CodecException(
            f"encoded data length is not multiple of 64 bytes ({len(dataBytes)})",
        )

    dt = np.dtype(np.int32)
    samples = np.zeros((numSamples,), dt)
    numFrames = len(dataBytes) // 64
    current = 0
    start = np.int32(0)
    firstData = np.int32(0)
    lastValue = np.int32(0)

    for i in range(numFrames):
        tempSamples = extractSteim1Samples(
            dataBytes, i * 64,
        )  # returns only differences except for frame 0

        firstData = 0  # d(0) is byte 0 by default

        if i == 0:
            # special case for first frame
            lastValue = bias  # assign our X(-1)

            # x0 and xn are in 1 and 2 spots
            start = tempSamples[1]  # X(0) is byte 1 for frame 0

            #  end = tempSamples[2]    # X(n) is byte 2 for frame 0
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
            f"Number of samples decompressed doesn't match number in header: {current} != {numSamples}",
        )

    # ignore last sample check???
    # if (end != samples[numSamples-1]):
    #    raise SteimException("Last sample decompressed doesn't match value x(n) value in Steim1 record: "+samples[numSamples-1]+" != "+end)
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
# @param littleEndian reverse the endian-ness of the compressed bytes being read
# @returns integer array of difference (and constant) values


def extractSteim1Samples(
    dataBytes: bytearray,
    offset: int,
) -> list:
    # get nibbles
    nibbles = getUint32(dataBytes, offset, False)
    currNibble = np.uint32(0)
    temp = []  # 4 samples * 16 longwords, can't be more than 64

    currNum = 0

    for i in range(16):
        # i is the word number of the frame starting at 0
        shiftBits = np.uint32(30 - i * 2)
        a=np.right_shift(np.uint32(nibbles), shiftBits)
        b=np.uint32(np.right_shift(np.uint32(nibbles), shiftBits))
        currNibble = np.bitwise_and(b, TWO_BITS)  # count from top to bottom each nibble in W(0)

        # Rule appears to be:
        # only check for byte-swap on actual value-atoms, so a 32-bit word in of itself
        # is not swapped, but two 16-bit short *values* are or a single
        # 32-bit int *value* is, if the flag is set to True.  8-bit values
        # are naturally not swapped.
        # It would seem that the W(0) word is swap-checked, though, which is confusing...
        # maybe it has to do with the reference to high-order bits for c(0)
        # switch (currNibble):
        if currNibble == 0:
            #  ("0 means header info")
            # only include header info if offset is 0
            if offset == 0:
                temp.append(getInt32(dataBytes, offset + i * 4, False))
                currNum += 1
        elif currNibble == 1:
            #  ("1 means 4 one byte differences")

            temp += struct.unpack(
                ">bbbb", dataBytes[offset + i * 4 : offset + i * 4 + 4]
            )
            currNum += 4

        elif currNibble == 2:
            #  ("2 means 2 two byte differences")

            temp += struct.unpack(
                ">hh", dataBytes[offset + i * 4 : offset + i * 4 + 4]
            )
            currNum += 2

        elif currNibble == 3:
            #  ("3 means 1 four byte difference")
            temp.append(getInt32(dataBytes, offset + i * 4, False))
            currNum += 1

        else:
            raise CodecException(f"unreachable case: {currNibble}")
        #  ("default")

    return np.array(temp, dtype='i4')


def encodeSteim1(
    samples: list[int], frames: int = 0, bias: np.int32 = 0, offset: int = 0
) -> bytearray:
    """
    Encode the array of integer values into a Steim 1 * compressed byte frame block.
    For miniseed2 you should not create a byte block any greater than 63 64-byte frames.
    maxFrames=0 implies unlimited number of frames, usually for miniseed3.
    <b>maxFrames</b> represents the number of frames to be written.
    This number should be determined from the desired logical record length
    <i>minus</i> the data offset from the record header (modulo 64)
    If <b>samples</b> is exhausted before all frames are filled, the remaining frames
    will be Nones.
    <b>bias</b> is a value carried over from a previous data record, representing
    X(-1)...set to 0 otherwise
    @param samples the data points represented as signed integers
    @param frames the number of Steim frames to use in the encoding
    @param bias offset for use as a constant for the first difference, otherwise
    set to 0
    @return SteimFrameBlock containing encoded byte array
    @throws SteimException samples array is zero size
    @throws SteimException number of frames is a negative value
    """
    return encodeSteim1FrameBlock(samples, frames, bias, offset).pack()


def encodeSteim1FrameBlock(
    samples: list[int], frames: int = 0, bias: np.int32 = 0, offset: int = 0
) -> SteimFrameBlock:

    if len(samples) == 0:
        raise SteimException("samples array is zero size")

    if frames < 0:
        raise SteimException("number of frames is a negative value")

    if offset < 0:
        raise SteimException("Offset cannot be negatuve: " + offset)

    if offset >= len(samples):
        raise SteimException(
            "Offset bigger than samples array: " + offset + " >= " + len(samples)
        )

    # check if numpy array
    if isinstance(samples, np.ndarray) and np.issubdtype(samples.dtype, np.floating):
        raise SteimException(f"Cannot steim1 compress floating point numpy array: {samples.dtype}");
    elif isinstance(samples[0], float):
        raise SteimException(f"Cannot steim1 compress floating point list, first sample is float: {samples[0]}");

    # all encoding will be contained within a frame block
    # Steim encoding 1
    frameBlock = SteimFrameBlock(frames, 1)
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
        np.int32(samples[offset]), 0, 0
    )  # X(0) -- first sample value
    frameBlock.addEncodedWord(
        np.int32(samples[len(samples) - 1]), 0, 0
    )  # X(N) -- last sample value
    #
    # now begin looping over differences
    sampleIndex = offset  # where we are in the sample array
    diff = np.array([0, 0, 0, 0], dtype="i4")  # store differences here
    diffCount = 0  # how many sample diffs we put into current word
    maxSize = 0  # the maximum diff value size encountered
    curSize = 0  # size of diff value currently looked at
    while sampleIndex < len(samples):
        # look at the next (up to four) differences
        # and assess the number that can be put into
        # the upcoming word
        diffCount = 0
        maxSize = 0
        for i in range(4):
            if sampleIndex + i < len(samples):
                # as long as there are still samples
                # get next difference  X[i] - X[i-1]
                if sampleIndex == offset and i == 0:
                    # special case for d(0) = x(0) - x(-1).
                    diff[0] = np.int32(samples[offset]) - np.int32(bias)
                else:
                    diff[i] = np.int32(
                        samples[sampleIndex + i] - samples[sampleIndex + i - 1]
                    )

                # and increment the counter
                diffCount += 1
            else:
                break  # no more samples, leave for loop
            # curSize indicates how many bytes the number would fill
            if diff[i] <= 127 and diff[i] >= -128:
                curSize = 1
            elif diff[i] <= 32767 and diff[i] >= -32768:
                curSize = 2
            else:
                curSize = 4
            # get the maximum size
            if curSize > maxSize:
                maxSize = curSize
            # now we multiply the maximum size encountered so far
            # by the number of differences examined so far
            # if the number is less than 4, we move on to the next diff
            # if the number is equal to 4, then we stop with the
            # current count
            # if the number is greater than 4, then back off one count
            # and if the count is 3 (cannot end with a 3 byte count),
            # then back off one count again
            # (the whole idea is we are looking for the proper fit)
            if maxSize * diffCount == 4:
                break
            if maxSize * diffCount > 4:
                diffCount -= 1
                if diffCount == 3:
                    diffCount -= 1
                break

        # end for (0..3)

        # generate the encoded word and the nibble value
        nibble = 0
        word = np.uint32(0)
        if diffCount == 1:
            word = diff[0]
            nibble = 3  # size 4 = 11
        elif diffCount == 2:
            word = np.bitwise_and(diff[0], TWO_BYTE) << 16  # clip to 16 bits, then shift
            word |= np.bitwise_and(diff[1], TWO_BYTE)
            nibble = 2  # size 2 = 10
        else:  # diffCount == 4
            word = np.bitwise_and(diff[0], ONE_BYTE) << 24  # clip to 8 bits, then shift
            word |= np.bitwise_and(diff[1], ONE_BYTE) << 16
            word |= np.bitwise_and(diff[2], ONE_BYTE) << 8
            word |= np.bitwise_and(diff[3], ONE_BYTE)
            nibble = 1  # size 1 = 01

        # add the encoded word to the frame block
        if frameBlock.addEncodedWord(word, diffCount, nibble):
            # frame block is full (but the value did get added)
            # so modify reverse integration constant to be the very last value added
            # and break out of loop (read no more samples)
            frameBlock.setXsubN(
                np.int32(samples[sampleIndex + diffCount - 1])
            )  # X(N)
            break

        # increment the sampleIndex by the diffCount
        sampleIndex += diffCount
    # end while next sample

    return frameBlock
