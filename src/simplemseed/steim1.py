from .steimframeblock import SteimFrameBlock


def encodeSteim1(
    samples: list[int], frames: int = 0, bias: int = 0, offset: int = 0
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
    samples: list[int], frames: int = 0, bias: int = 0, offset: int = 0
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
    frameBlock.addEncodedWord(samples[offset], 0, 0)  # X(0) -- first sample value
    frameBlock.addEncodedWord(
        samples[len(samples) - 1], 0, 0
    )  # X(N) -- last sample value
    #
    # now begin looping over differences
    sampleIndex = offset  # where we are in the sample array
    diff = [0, 0, 0, 0]  # store differences here
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
                    diff[0] = samples[offset] - bias
                else:
                    diff[i] = samples[sampleIndex + i] - samples[sampleIndex + i - 1]

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
            elif maxSize * diffCount > 4:
                diffCount -= 1
                if diffCount == 3:
                    diffCount -= 1
                break

        # end for (0..3)

        # generate the encoded word and the nibble value
        nibble = 0
        word = 0
        if diffCount == 1:
            word = diff[0]
            nibble = 3  # size 4 = 11
        elif diffCount == 2:
            word = (diff[0] & 0xFFFF) << 16  # clip to 16 bits, then shift
            word |= diff[1] & 0xFFFF
            nibble = 2  # size 2 = 10
        else:  # diffCount == 4
            word = (diff[0] & 0xFF) << 24  # clip to 8 bits, then shift
            word |= (diff[1] & 0xFF) << 16
            word |= (diff[2] & 0xFF) << 8
            word |= diff[3] & 0xFF
            nibble = 1  # size 1 = 01

        # add the encoded word to the frame block
        if frameBlock.addEncodedWord(word, diffCount, nibble):
            # frame block is full (but the value did get added)
            # so modify reverse integration constant to be the very last value added
            # and break out of loop (read no more samples)
            frameBlock.setXsubN(samples[sampleIndex + diffCount - 1])  # X(N)
            break

        # increment the sampleIndex by the diffCount
        sampleIndex += diffCount
    # end while next sample

    return frameBlock
