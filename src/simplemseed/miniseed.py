import struct
from array import array
from collections import namedtuple
from datetime import datetime, timedelta, timezone
import math
import sys

import numpy

from .exceptions import (
    CodecException,
)
from .seedcodec import (
    decompress,
    encode,
    mseed3EncodingFromArrayTypecode,
    mseed3EncodingFromNumpyDT,
    EncodedDataSegment,
    numpyDTFromMseed3Encoding,
    BIG_ENDIAN,
    LITTLE_ENDIAN,
)

MICRO = 1000000

EMPTY_SEQ = "      ".encode("UTF-8")
ENC_SHORT = 1
ENC_INT = 3


HEADER_SIZE = 48
B1000_SIZE = 8
MAX_INT_PER_512 = (512 - HEADER_SIZE - B1000_SIZE) // 4
MAX_SHORT_PER_512 = (512 - HEADER_SIZE - B1000_SIZE) // 2

BTime = namedtuple("BTime", "year yday hour minute second tenthMilli")
Blockette1000 = namedtuple(
    "Blockette1000", "blocketteNum, nextOffset, encoding, byteorder, recLength"
)
Blockette100 = namedtuple("Blockette100", "blocketteNum, nextOffset, sampleRate")
Blockette1001 = namedtuple(
    "Blockette1001", "blocketteNum, nextOffset, timeQuality, microseconds, frameCount"
)
BlocketteUnknown = namedtuple("BlocketteUnknown", "blocketteNum, nextOffset, rawBytes")


class MiniseedHeader:
    """
    Represents the fixed header section of a miniseed2 record
    """

    def __init__(
        self,
        network,
        station,
        location,
        channel,
        starttime,
        numSamples,
        sampleRate,
        encoding=-1,
        byteorder=BIG_ENDIAN,
        sampRateFactor=0,
        sampRateMult=0,
        actFlag=0,
        ioFlag=0,
        qualFlag=0,
        numBlockettes=0,
        timeCorr=0,
        dataOffset=0,
        blocketteOffset=0,
        sequence_number=0,
        dataquality="D",
    ):
        """
        starttime can be datetime or BTime
        if sampleRate is zero, will be calculated from sampRateFactor and sampRateMult
        """
        self.sequence_number = sequence_number  # SEED record sequence number */
        self.network = network  # Network designation, NULL terminated */
        self.station = station  # Station designation, NULL terminated */
        self.location = location  # Location designation, NULL terminated */
        self.channel = channel  # Channel designation, NULL terminated */
        self.dataquality = dataquality  # Data quality indicator */
        self.setStartTime(starttime)  # Record start time, corrected (first sample) */
        self.sampleRate = sampleRate  # Nominal sample rate (Hz) */
        self.numSamples = numSamples  # Number of samples in record */
        self.encoding = encoding  # Data encoding format */
        self.byteorder = byteorder  # Original/Final byte order of record */
        if self.byteorder == 1:
            self.endianChar = ">"
        else:
            self.endianChar = "<"

        self.sampRateFactor = sampRateFactor
        self.sampRateMult = sampRateMult
        if sampleRate == 0 and not (sampRateFactor == 0 and sampRateMult == 0):
            # calc sampleRate from sampRateFactor and sampRateMult
            if sampRateFactor > 0:
                if sampRateMult > 0:
                    self.sampleRate = 1.0 * sampRateFactor * sampRateMult
                else:
                    self.sampleRate = -1.0 * sampRateFactor / sampRateMult
            else:
                if sampRateMult > 0:
                    self.sampleRate = -1.0 * sampRateMult / sampRateFactor
                else:
                    self.sampleRate = 1.0 / (sampRateFactor * sampRateMult)
        if self.sampleRate == 0 and self.encoding != 0:
            raise MiniseedException(
                f"Sample rate cannot be 0 for encoding {self.encoding}: {self.sampleRate}, {self.sampRateFactor}, {self.sampRateMult}"
            )
        self.sampPeriod = timedelta(
            microseconds=MICRO / self.sampleRate
        )  # Nominal sample period (Sec) */

        self.actFlag = actFlag
        self.ioFlag = ioFlag
        self.qualFlag = qualFlag
        self.numBlockettes = numBlockettes
        self.timeCorr = timeCorr
        self.dataOffset = dataOffset
        self.blocketteOffset = blocketteOffset
        self.recordLengthExp = 9  # default to 512
        self.recordLength = 2**self.recordLengthExp

    def codes(self, sep="."):
        return "{n}{sep}{s}{sep}{l}{sep}{c}".format(
            sep=sep,
            n=self.network.strip(),
            s=self.station.strip(),
            l=self.location.strip(),
            c=self.channel.strip(),
        )

    def pack(self):
        header = bytearray(48)
        net = self.network.ljust(2).encode("UTF-8")
        sta = self.station.ljust(5).encode("UTF-8")
        loc = self.location.ljust(2).encode("UTF-8")
        chan = self.channel.ljust(3).encode("UTF-8")
        struct.pack_into(
            self.endianChar + "6scc5s2s3s2s",
            header,
            0,
            EMPTY_SEQ,
            b"D",
            b" ",
            sta,
            loc,
            chan,
            net,
        )
        self.packBTime(header, self.starttime)
        tempsampRateFactor = self.sampRateFactor
        tempsampRateMult = self.sampRateMult
        if self.sampleRate != 0 and self.sampRateFactor == 0 and self.sampRateMult == 0:
            tempsampRateFactor, tempsampRateMult = self.calcSeedMultipilerFactor()
        struct.pack_into(
            self.endianChar + "Hhh",
            header,
            30,
            self.numSamples,
            tempsampRateFactor,
            tempsampRateMult,
        )
        return header

    def calcSeedMultipilerFactor(self):
        SHORT_MIN_VALUE = -1 * math.pow(2, 15)
        SHORT_MAX_VALUE = math.pow(2, 15) - 1
        factor = 0
        divisor = 0
        if self.sampleRate == 0:
            factor = 0
            divisor = 0
        elif self.sampleRate >= 1:
            # don't get too close to the max for a short, use ceil as neg
            divisor = math.ceil((SHORT_MIN_VALUE + 2) / self.sampleRate)
            # don't get too close to the max for a short
            if divisor < SHORT_MIN_VALUE + 2:
                divisor = SHORT_MIN_VALUE + 2
            factor = round(-1 * self.sampleRate * divisor)
        else:
            # don't get too close to the max for a short, use ceil as neg
            factor = -1 * round(
                math.floor(1.0 * self.sampleRate * (SHORT_MAX_VALUE - 2))
                / self.sampleRate
            )
            # don't get too close to the max for a short
            if factor > SHORT_MAX_VALUE - 2:
                factor = SHORT_MAX_VALUE - 2
            divisor = round(-1 * factor * self.sampleRate)
        return factor, divisor

    def packBTime(self, header, time):
        tt = time.timetuple()
        struct.pack_into(
            self.endianChar + "HHBBBxH",
            header,
            20,
            tt.tm_year,
            tt.tm_yday,
            tt.tm_hour,
            tt.tm_min,
            tt.tm_sec,
            int(time.microsecond / 100),
        )

    def setSampleRate(self, sampleRate):
        self.sampleRate = sampleRate
        self.sampPeriod = timedelta(
            microseconds=MICRO / self.sampleRate
        )  # Nominal sample period (Sec) */

    def setStartTime(self, starttime):
        if type(starttime).__name__ == "str":
            fixTZ = starttime.replace("Z", "+00:00")
            starttime = datetime.fromisoformat(fixTZ)
        if type(starttime).__name__ == "datetime":
            # make sure timezone aware
            if not starttime.tzinfo:
                self.starttime = starttime.replace(tzinfo=timezone.utc)
            else:
                self.starttime = starttime.astimezone(timezone.utc)
            tt = self.starttime.timetuple()
            self.btime = BTime(
                tt.tm_year,
                tt.tm_yday,
                tt.tm_hour,
                tt.tm_min,
                tt.tm_sec,
                int(starttime.microsecond / 100),
            )
        elif type(starttime).__name__ == "BTime":
            self.btime = starttime
            self.starttime = datetime(
                self.btime.year,
                1,
                1,
                hour=self.btime.hour,
                minute=self.btime.minute,
                second=self.btime.second,
                microsecond=100 * self.btime.tenthMilli,
                tzinfo=timezone.utc,
            ) + timedelta(days=self.btime.yday - 1)
        else:
            raise MiniseedException(
                f"unknown type of starttime {type(starttime)}"
            )


class MiniseedRecord:
    """
    Represents a miniseed2 record
    """

    def __init__(self, header, data, encodedData=None, blockettes=None):
        self.header = header
        if blockettes is not None:
            self.blockettes = blockettes
        else:
            self.blockettes = []
        self._data = None
        if data is not None:
            self._internal_set_data(data)
        else:
            self._data = None
        self.encodedData = encodedData

    def _internal_set_data(self, data):
        if isinstance(data, EncodedDataSegment):
            self._data = data.dataBytes
            encoding = data.compressionType
            numSamples = data.numSamples
            byteorder = LITTLE_ENDIAN if data.littleEndian else BIG_ENDIAN
        elif isinstance(data, (bytes, bytearray)):
            # bytes, hopefully header.numSamples and byteorder set correctly
            self._data = data
            encoding = self.header.encoding
            numSamples = self.header.numSamples
            byteorder = self.header.byteorder
        elif isinstance(data, array):
            # array.array primitive
            encoding = mseed3EncodingFromArrayTypecode(data.typecode, data.itemsize)
            numSamples = len(data)
            byteorder = LITTLE_ENDIAN if sys.byteorder == "little" else BIG_ENDIAN
            self._data = data
        elif isinstance(data, numpy.ndarray):
            # numpy array
            encoding = mseed3EncodingFromNumpyDT(data.dtype)
            if data.dtype.byteorder == "<":
                byteorder = LITTLE_ENDIAN
            elif data.dtype.byteorder == ">":
                byteorder = BIG_ENDIAN
            else:
                byteorder = LITTLE_ENDIAN if sys.byteorder == "little" else BIG_ENDIAN
            numSamples = len(data)
            self._data = data
        elif isinstance(data, list):
            # list of numbers, use numpy?
            #
            if self.header.encoding == -1:
                encoding = 4  # default to 32 bit floats?
            else:
                encoding = self.header.encoding
            self._data = numpy.array(data, dtype=numpyDTFromMseed3Encoding(encoding))
            encoding = mseed3EncodingFromNumpyDT(self._data.dtype)
            numSamples = len(self._data)
            byteorder = LITTLE_ENDIAN if sys.byteorder == "little" else BIG_ENDIAN
        else:
            raise MiniseedException(f"unknown data type: {type(data)}")
        # set if header has defaults
        self.header.byteorder = byteorder
        if self.header.encoding == -1:
            self.header.encoding = encoding
        if self.header.numSamples == 0:
            self.header.numSamples = numSamples
        # sanity check with headers
        if self.header.encoding != encoding:
            raise MiniseedException(
                f"Mismatched encoding: {self.header.encoding} != {encoding}"
            )
        if self.header.numSamples != numSamples:
            raise MiniseedException(
                f"Mismatched num samples: {self.header.numSamples} != {numSamples}"
            )

    def decompressed(self):
        if self._data is not None:
            return self._data
        if self.encodedData is not None:
            self._data = decompressEncodedData(
                self.header.encoding,
                self.header.byteorder,
                self.header.numSamples,
                self.encodedData,
            )
        return self._data

    def codes(self, sep="."):
        return self.header.codes(sep=sep)

    def starttime(self):
        return self.header.starttime

    def endtime(self):
        return self.starttime() + self.header.sampPeriod * (self.header.numSamples - 1)

    def next_starttime(self):
        return self.starttime() + self.header.sampPeriod * (self.header.numSamples)

    def clone(self):
        return unpackMiniseedRecord(self.pack())

    def pack(self):
        recordBytes = bytearray(self.header.recordLength)
        recordBytes[0:48] = self.header.pack()

        offset = 48
        struct.pack_into(self.header.endianChar + "H", recordBytes, 46, offset)
        hasB1000 = False
        for b in self.blockettes:
            if b.blocketteNum == 1000:
                hasB1000 = True
                break
        if not hasB1000:
            # make sure we have a b1000 to be valid miniseed
            self.blockettes.insert(0, self.createB1000())
        recordBytes[39] = len(self.blockettes)
        for b in self.blockettes:
            offset = self.packBlockette(recordBytes, offset, b)
        # set offset to data in header
        # if offset < 64:
        #    offset = 64
        struct.pack_into(self.header.endianChar + "H", recordBytes, 44, offset)
        if self.encodedData is not None and self._data is None:
            recordBytes[offset : offset + len(self.encodedData)] = self.encodedData
        else:
            self.packData(recordBytes, offset, self._data)
        return recordBytes

    def packBlockette(self, recordBytes, offset, b):
        if type(b).__name__ == "Blockette100":
            return self.packB100(recordBytes, offset, b)
        if type(b).__name__ == "Blockette1000":
            return self.packB1000(recordBytes, offset, b)
        if type(b).__name__ == "Blockette1001":
            return self.packB1001(recordBytes, offset, b)
        if type(b).__name__ == "BlocketteUnknown":
            return self.packBlocketteUnknown(recordBytes, offset, b)
        raise CodecException(f"Unknown blockette: {type(b).__name__}")

    def packBlocketteUnknown(self, recordBytes, offset, bUnk):
        struct.pack_into(
            self.header.endianChar + "HH",
            recordBytes,
            offset,
            bUnk.blocketteNum,
            bUnk.nextOffset,
        )
        recordBytes[offset + 4 : offset + len(bUnk.rawBytes)] = bUnk.rawBytes[4:]
        return offset + len(bUnk.rawBytes)

    def packB100(self, recordBytes, offset, b):
        struct.pack_into(
            self.header.endianChar + "HHixxxx",
            recordBytes,
            offset,
            b.blocketteNum,
            b.nextOffset,
            b.sampleRate,
        )
        return offset + 8

    def createB100(self):
        return Blockette100(
            1000,
            0,
            self.header.sampleRate,
        )

    def packB1000(self, recordBytes, offset, b):
        struct.pack_into(
            self.header.endianChar + "HHBBBx",
            recordBytes,
            offset,
            b.blocketteNum,
            b.nextOffset,
            self.header.encoding,
            self.header.byteorder,
            self.header.recordLengthExp,
        )
        return offset + 8

    def createB1000(self):
        return Blockette1000(
            1000,
            0,
            self.header.encoding,
            self.header.byteorder,
            self.header.recordLengthExp,
        )

    def packB1001(self, recordBytes, offset, b):
        struct.pack_into(
            self.header.endianChar + "HHBBxB",
            recordBytes,
            offset,
            b.blocketteNum,
            b.nextOffset,
            b.timeQuality,
            b.microseconds,
            b.frameCount,
        )
        return offset + 8

    def createB1001(self):
        microseconds = self.starttime().microsecond % 100
        return Blockette1001(
            1000,
            0,
            0,  # time quality
            microseconds,  # microseconds
            0,  # frame count?
        )

    def packData(self, recordBytes, offset, data):
        dataBytes = encode(
            data, self.header.encoding, self.header.byteorder == LITTLE_ENDIAN
        ).dataBytes
        if len(recordBytes) < offset + len(dataBytes):
            raise MiniseedException(
                f"not enough bytes in record to fit data: byte:{len(recordBytes):d} offset: {offset:d} len(data): {len(data):d}  enc:{self.header.encoding:d}"
            )
        recordBytes[offset : offset + len(dataBytes)] = dataBytes

    def __str__(self):
        return self.summary()

    def summary(self):
        return f"{self.codes()} {self.starttime()} {self.endtime()} ({self.header.numSamples} pts)"


def unpackMiniseedHeader(recordBytes, endianChar=">"):
    if len(recordBytes) < 48:
        raise MiniseedException(
            f"Not enough bytes for header: {len(recordBytes):d}"
        )
    (
        seq,
        qualityChar,
        _reserved,
        sta,
        loc,
        chan,
        net,
        year,
        yday,
        hour,
        minute,
        sec,
        tenthMilli,
        numSamples,
        sampRateFactor,
        sampRateMult,
        actFlag,
        ioFlag,
        qualFlag,
        numBlockettes,
        timeCorr,
        dataOffset,
        blocketteOffset,
    ) = struct.unpack(endianChar + "6scc5s2s3s2sHHBBBxHHHHBBBBiHH", recordBytes[0:48])
    if endianChar == ">":
        byteorder = BIG_ENDIAN
    else:
        byteorder = LITTLE_ENDIAN
    net = net.decode("utf-8").strip()
    sta = sta.decode("utf-8").strip()
    loc = loc.decode("utf-8").strip()
    chan = chan.decode("utf-8").strip()
    seq = seq.decode("utf-8").strip()
    qualityChar = qualityChar.decode("utf-8").strip()
    starttime = BTime(year, yday, hour, minute, sec, tenthMilli)
    sampleRate = 0  # recalc in constructor
    encoding = -1  # reset on read b1000
    return MiniseedHeader(
        net,
        sta,
        loc,
        chan,
        starttime,
        numSamples,
        sampleRate,
        encoding=encoding,
        byteorder=byteorder,
        sampRateFactor=sampRateFactor,
        sampRateMult=sampRateMult,
        actFlag=actFlag,
        ioFlag=ioFlag,
        qualFlag=qualFlag,
        numBlockettes=numBlockettes,
        timeCorr=timeCorr,
        dataOffset=dataOffset,
        blocketteOffset=blocketteOffset,
        sequence_number=seq,
        dataquality=qualityChar,
    )


def unpackBlockette(recordBytes, offset, endianChar, dataOffset):
    blocketteNum, nextOffset = struct.unpack(
        endianChar + "HH", recordBytes[offset : offset + 4]
    )
    endOffset = nextOffset
    if nextOffset == 0:
        # in case of last blockette, might need to use all until dataOffset
        endOffset = dataOffset
    bnum = int(blocketteNum)
    #    print ("Blockette Number in unpackBlockette:", blocketteNum," ",bnum)
    if bnum == 1000:
        return unpackBlockette1000(recordBytes, offset, endianChar)
    if bnum == 100:
        return unpackBlockette100(recordBytes, offset, endianChar)
    if bnum == 1001:
        return unpackBlockette1001(recordBytes, offset, endianChar)
    return BlocketteUnknown(blocketteNum, nextOffset, recordBytes[offset:endOffset])


def unpackBlockette100(recordBytes, offset, endianChar):
    """named Tuple of blocketteNum, nextOffset, sample rate"""
    blocketteNum, nextOffset, sampRate = struct.unpack(
        endianChar + "HHixxxx", recordBytes[offset : offset + 12]
    )
    return Blockette100(blocketteNum, nextOffset, sampRate)


def unpackBlockette1000(recordBytes, offset, endianChar):
    """named Tuple of blocketteNum, nextOffset, encoding, byteorder, recLength"""

    blocketteNum, nextOffset, encoding, byteorder, recLength = struct.unpack(
        endianChar + "HHBBBx", recordBytes[offset : offset + 8]
    )
    return Blockette1000(blocketteNum, nextOffset, encoding, byteorder, recLength)


def unpackBlockette1001(recordBytes, offset, endianChar):
    """named Tuple of blocketteNum, nextOffset, time quality, microseconds, frame count"""
    blocketteNum, nextOffset, timeQual, microseconds, frameCount = struct.unpack(
        endianChar + "HHBBxB", recordBytes[offset : offset + 8]
    )
    return Blockette1001(blocketteNum, nextOffset, timeQual, microseconds, frameCount)


def unpackFixedHeaderGuessByteOrder(recordBytes):
    byteorder = BIG_ENDIAN
    endianChar = ">"
    # 0x0708 = 1800 and 0x0807 = 2055
    if (
        recordBytes[20] == 7
        or recordBytes[20] == 8
        and not (recordBytes[21] == 7 or recordBytes[21] == 8)
    ):
        # print("big endian {:d} {:d}".format(recordBytes[20], recordBytes[21]))
        byteorder = BIG_ENDIAN
        endianChar = ">"
    elif (recordBytes[21] == 7 or recordBytes[21] == 8) and not (
        recordBytes[20] == 7 or recordBytes[20] == 8
    ):
        # print("little endian {:d} {:d}".format(recordBytes[20], recordBytes[21]))
        byteorder = LITTLE_ENDIAN
        endianChar = "<"
    else:
        raise MiniseedException(
            f"unable to determine byte order from year bytes: {recordBytes[21]:d} {recordBytes[22]:d}"
        )
    header = unpackMiniseedHeader(recordBytes, endianChar)
    header.byteorder = byteorder  # in case no b1000
    return header


def unpackMiniseedRecord(recordBytes):
    header = unpackFixedHeaderGuessByteOrder(recordBytes)
    endianChar = "<" if header.byteorder == LITTLE_ENDIAN else ">"

    blockettes = []
    if header.numBlockettes > 0:
        nextBOffset = header.blocketteOffset
        # print("Next Byte Offset",nextBOffset)
        while nextBOffset > 0:
            try:
                b = unpackBlockette(
                    recordBytes, nextBOffset, endianChar, header.dataOffset
                )
                blockettes.append(b)
                if type(b).__name__ == "Blockette1000":
                    header.encoding = b.encoding
                    header.byteorder = b.byteorder
                elif type(b).__name__ == "Blockette100":
                    header.setSampleRate(b.sampleRate)
                elif type(b).__name__ == "Blockette1001":
                    header.setStartTime(
                        header.starttime + timedelta(microseconds=b.microseconds)
                    )
                nextBOffset = b.nextOffset
            except struct.error as e:
                print(
                    f"Unable to unpack blockette, fail codes: {header.codes()} start: {header.starttime} {e}"
                )
                raise

    encodedData = recordBytes[header.dataOffset :]
    if header.encoding in (ENC_SHORT, ENC_INT):
        data = decompressEncodedData(
            header.encoding, header.byteorder, header.numSamples, encodedData
        )
    else:
        data = None
    return MiniseedRecord(header, data, encodedData=encodedData, blockettes=blockettes)


def decompressEncodedData(encoding, byteorder, numSamples, recordBytes):
    return decompress(encoding, recordBytes, numSamples, byteorder == LITTLE_ENDIAN)


class MiniseedException(Exception):
    pass


def readMiniseed2Records(fileptr):
    headBytes = fileptr.read(HEADER_SIZE)
    while len(headBytes) >= HEADER_SIZE:
        header = unpackFixedHeaderGuessByteOrder(headBytes)
        endianChar = "<" if header.byteorder == LITTLE_ENDIAN else ">"

        # assume all blocketts between fixed header and start of data
        blocketteBytes = fileptr.read(header.dataOffset - HEADER_SIZE)
        blockettes = []
        if header.numBlockettes > 0:
            nextBOffset = header.blocketteOffset
            while nextBOffset > 0:
                try:
                    b = unpackBlockette(
                        blocketteBytes,
                        nextBOffset - HEADER_SIZE,
                        endianChar,
                        header.dataOffset,
                    )
                    blockettes.append(b)
                    if type(b).__name__ == "Blockette1000":
                        header.encoding = b.encoding
                        header.byteorder = b.byteorder
                    elif type(b).__name__ == "Blockette100":
                        header.setSampleRate(b.sampleRate)
                    elif type(b).__name__ == "Blockette1001":
                        header.setStartTime(
                            header.starttime + timedelta(microseconds=b.microseconds)
                        )
                    nextBOffset = b.nextOffset
                except struct.error as e:
                    print(
                        f"Unable to unpack blockette, fail codes: {header.codes()} start: {header.starttime} {e}"
                    )
                    raise
        recordBytesSize = 512
        for b in blockettes:
            if b.blocketteNum == 1000:
                if b.recLength < 8 or b.recLength > 12:
                    raise MiniseedException(
                        f"record length {b.recLength} from B1000 is not valid, 8-12 for 512 to 4096"
                    )
                recordBytesSize = 2**b.recLength
        encodedDataBytes = fileptr.read(recordBytesSize - header.dataOffset)
        yield MiniseedRecord(
            header, data=None, encodedData=encodedDataBytes, blockettes=blockettes
        )
        headBytes = fileptr.read(HEADER_SIZE)
