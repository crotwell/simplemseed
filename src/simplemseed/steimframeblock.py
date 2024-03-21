import struct

import numpy

from typing import Union




def getInt16(dataBytes, offset, littleEndian):
    endianChar = "<" if littleEndian else ">"
    vals = struct.unpack(endianChar + "h", dataBytes[offset : offset + 2])
    return vals[0]


def getInt32(dataBytes, offset, littleEndian):
    endianChar = "<" if littleEndian else ">"
    vals = struct.unpack(endianChar + "l", dataBytes[offset : offset + 4])
    return vals[0]


def getFloat32(dataBytes, offset, littleEndian):
    endianChar = "<" if littleEndian else ">"
    vals = struct.unpack(endianChar + "f", dataBytes[offset : offset + 4])
    return vals[0]

def getUint32(dataBytes, offset, littleEndian):
    endianChar = "<" if littleEndian else ">"
    vals = struct.unpack(endianChar + "I", dataBytes[offset : offset + 4])
    return vals[0]

class SteimFrame:
    """
    This represents a single Steim compression frame.  It stores values
    as an int array and keeps track of it's current position in the frame.
    """

    def __init__(self):
        self.word = numpy.zeros(16, dtype=numpy.dtype(numpy.int32)).newbyteorder(
            ">"
        )  # 16 32-byte words
        self.pos = 0  # word position in frame (pos: 0 = W0, 1 = W1, etc...)

    def isEmpty(self):
        if self.word[0] == 0:
            return true
        else:
            return False

    def pack(self):
        return self.word.tobytes()


class SteimFrameBlock:
    """
    This class acts as a container to hold encoded bytes processed
    by a Steim compression routine, as well as supporting information
    relating to the data processed.
    It also facilitates Steim notation and the formation
    of the data frames.
    This class stores the Steim encoding, but is ignorant of the encoding
    process itself...it's just for self-referencing.

    Converted to Python from Java, edu.iris.dmc.seedcodec
    @author Robert Casey (IRIS DMC)
    @version 12/10/2001
    """

    maxNumFrames: int  # number of frames this object contains
    numSamples: int  # number of samples represented
    steimVersion: int  # Steim version number
    currentFrame: (
        int  # number of current frame being built, start before first (zero) index
    )
    steimFrameList: list[SteimFrame]  # list of frames, added as needed
    currentSteimFrame: SteimFrame  # current frame appending to, may be None if now frame needs to be created

    # *** constructors ***

    def __init__(self, maxNumFrames: int = 0, steimVersion: int = 2):
        """
        Create a new block of Steim frames for a particular version of Steim
        copression.
        Instantiate object with the number of 64-byte frames
        that this block will contain (should connect to data
        record header such that a proper power of 2 boundary is
        formed for the data record) AND the version of Steim
        compression used (1 and 2 currently)
        the number of frames remains static...frames that are
        not filled with data are simply full of Nones.
        @param maxNumFrames the max number of frames in this Steim record, zero for unlimited
        @param steimVersion which version of Steim compression is being used
        (1,2,3).
        """
        self.maxNumFrames = maxNumFrames
        self.steimVersion = steimVersion
        self.numSamples = 0
        self.steimFrameList = []
        self.currentFrame = 0
        self.currentSteimFrame = None

    # *** public methods ***

    def getNumSamples(self):
        """
        Return the number of data samples represented by this frame block
        @return integer value indicating number of samples
        """
        return self.numSamples

    def getSteimVersion(self):
        """
        Return the version of Steim compression used
        @return integer value representing the Steim version (1,2,3)
        """
        return self.steimVersion

    def getSteimFrames(self):
        return self.steimFrameList

    def getEncodedData(self):
        """
        Return the compressed byte representation of the data for inclusion
        in a data record.
        @return byte array containing the encoded, compressed data
        @throws IOException from called method(s)
        """
        # set up a byte array to write int words to
        encodedData = bytearray(self.getNumFrames() * 64)
        # set up interface to the array for writing the ints
        offset = 0
        for frame in self.steimFrameList:
            # for each frame
            encodedData[offset : offset + 64] = frame.pack()
            offset += 64
        return encodedData

    def getNumFrames(self):
        """
        Return the number of frames in this frame block
        @return integer value indicating number of frames
        """
        if self.maxNumFrames == 0:
            return self.steimFrameList.size()

        return self.maxNumFrames

    # *** private and protected methods ***

    def addEncodedWord(
        self, word: Union[numpy.int32, numpy.uint32], samples: int, nibble: int
    ):
        """
        Add a single 32-bit word to current frame.
        @param samples the number of sample differences in the word
        @param nibble a value of 0 to 3 that reflects the W0 encoding
        for this word
        @return boolean indicating true if the block is full (ie: the
        calling app should not add any more to this object)
        """
        if self.currentSteimFrame is None:
            self.currentSteimFrame = SteimFrame()
            self.currentSteimFrame.pos = 1
            self.addEncodingNibble(0)  # first nibble always 00
            self.steimFrameList.append(self.currentSteimFrame)
            self.currentFrame += 1

        pos = self.currentSteimFrame.pos  # word position
        self.currentSteimFrame.word[pos] = word  # add word
        self.addEncodingNibble(nibble)  # add nibble
        self.numSamples += samples
        pos += 1  # increment position in frame
        if pos > 15:  # need next frame?
            self.currentSteimFrame = None
            if (
                self.maxNumFrames > 0 and self.currentFrame >= self.maxNumFrames
            ):  # exceeded frame limit?
                return True  # block is full

        else:
            self.currentSteimFrame.pos = pos  # increment position in frame

        return False  # block is not yet full

    def setXsubN(self, word: numpy.int32):
        """
        Set the reverse integration constant X(N) explicitly to the
        provided word value.
        This method is typically used to reset X(N) should the compressor
        fill the frame block before all samples have been read.
        @param word integer value to be placed in X(N)
        """
        self.steimFrameList[0].word[2] = word
        return

    def addEncodingNibble(self, bitFlag: numpy.uint32):
        """
        * Add encoding nibble to W0.
        * @param bitFlag a value 0 to 3 representing an encoding nibble
        """
        offset = self.currentSteimFrame.pos  # W0 nibble offset - determines Cn in W0
        shift = (15 - offset) * 2  # how much to shift bitFlag
        self.currentSteimFrame.word[0] |= bitFlag << shift
        return

    def pack(self):
        out = bytearray()
        for frame in self.steimFrameList:
            out = out + frame.pack()
        return out
