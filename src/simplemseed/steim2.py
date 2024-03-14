from .steimframeblock import SteimFrameBlock


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


def encodeSteim2(samples: list[int], frames: int = 0, bias: int = 0):
    """

    Encode the array of integer values into a Steim 2 * compressed byte frame block.
    For miniseed2 you should not create a byte block any greater than 63 64-byte frames.
    <b>frames</b> represents the number of frames to be written.
    This number should be determined from the desired logical record length
    <i>minus</i> the data offset from the record header (modulo 64)
    If <b>samples</b> is exhausted before all frames are filled, the remaining frames
    will be nulls.
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
    samples: list[int], frames: int = 0, bias: int = 0
) -> SteimFrameBlock:
    if len(samples) == 0:
        raise SteimException("samples array is zero size")

    if frames < 0:
        raise SteimException("number of frames is  a negative value")

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
    frameBlock.addEncodedWord(samples[0], 0, 0)  # X(0) -- first sample value
    frameBlock.addEncodedWord(
        samples[len(samples) - 1], 0, 0
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
                    diff[0] = samples[0] - bias
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
        bitmask = 0
        submask = 0
        nibble = 0
        if nbits == 4:
            ndiff = 7
            bitmask = 0x0000000F
            submask = 0x02
            nibble = 3
        elif nbits == 5:
            ndiff = 6
            bitmask = 0x0000001F
            submask = 0x01
            nibble = 3
        elif nbits == 6:
            ndiff = 5
            bitmask = 0x0000003F
            submask = 0x00
            nibble = 3
        elif nbits == 8:
            ndiff = 4
            bitmask = 0x000000FF
            submask = 0
            nibble = 1
        elif nbits == 10:
            ndiff = 3
            bitmask = 0x000003FF
            submask = 0x03
            nibble = 2
        elif nbits == 15:
            ndiff = 2
            bitmask = 0x00007FFF
            submask = 0x02
            nibble = 2
        elif nbits == 30:
            ndiff = 1
            bitmask = 0x3FFFFFFF
            submask = 0x01
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
            frameBlock.setXsubN(samples[sampleIndex + ndiff - 1])  # X(N)
            break

        # increment the sampleIndex by the number of differences
        sampleIndex += ndiff
    # end while next sample
    return frameBlock


def minBitsNeeded(diff: int):
    minbits = 0
    if diff >= -8 and diff < 8:
        minbits = 4
    elif diff >= -16 and diff < 16:
        minbits = 5
    elif diff >= -32 and diff < 32:
        minbits = 6
    elif diff >= -128 and diff < 128:
        minbits = 8
    elif diff >= -512 and diff < 512:
        minbits = 10
    elif diff >= -16384 and diff < 16384:
        minbits = 15
    elif diff >= -536870912 and diff < 536870912:
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


def steimPackWord(diff: list[int], nbits: int, ndiff: int, bitmask: int, submask: int):
    """
    Pack Steim2 compressed word with optional submask.
    @param diff the differences
    @param nbits the number of bits
    @param ndiff the number of differences
    @param bitmask the bit mask
    @param submask the sub mask or 0 if none
    """
    val = 0
    i = 0
    while i < ndiff:
        val = (val << nbits) | (diff[i] & bitmask)
        i += 1
    if submask != 0:
        val |= submask << 30
    return val
