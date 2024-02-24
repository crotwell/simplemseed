import struct
from array import array
import numpy
from collections import namedtuple
from datetime import datetime, timedelta, timezone
import json
import math
import re
import sys
import crc32c
from typing import Union

from .miniseed import MiniseedException
from .seedcodec import (
    canDecompress,
    decompress,
    compress,
    STEIM1,
    STEIM2,
    STEIM3,
    EncodedDataSegment,
    mseed3EncodingFromArrayTypecode,
    mseed3EncodingFromNumpyDT,
)
from .fdsnsourceid import FDSNSourceId


MINISEED_THREE_MIME = "application/vnd.fdsn.mseed3"

# const for unknown data version, 0 */
UNKNOWN_DATA_VERSION = 0

# const for offset to crc in record, 28 */
CRC_OFFSET = 28

# const for size of fixed header part of record, 40 */
FIXED_HEADER_SIZE = 40

# const for fdsn prefix for extra headers, FDSN */
FDSN_PREFIX = "FDSN"

# const for little endian, true */
# LITTLE_ENDIAN = True
ENDIAN = "<"

# const for big endian, false */
# BIG_ENDIAN = False;


BIG_ENDIAN = 1
LITTLE_ENDIAN = 0

HEADER_PACK_FORMAT = "<ccBBIHHBBBBdIIBBHI"


class MSeed3Header:
    recordIndicator: str
    formatVersion: int
    flags: int
    nanosecond: int
    year: int
    dayOfYear: int
    hour: int
    minute: int
    second: int
    encoding: int
    sampleRatePeriod: float
    numSamples: int
    crc: int
    publicationVersion: int
    identifierLength: int
    extraHeadersLength: int
    dataLength: int

    def __init__(self):
        # empty construction
        self.recordIndicator = "MS"
        self.formatVersion = 3
        self.flags = 0
        self.nanosecond = 0
        self.year = 1970
        self.dayOfYear = 1
        self.hour = 0
        self.minute = 0
        self.second = 0
        self.encoding = 3  # 32 bit ints

        self.sampleRatePeriod = 1
        self.numSamples = 0
        self.crc = 0
        self.publicationVersion = UNKNOWN_DATA_VERSION
        self.identifierLength = 0
        self.extraHeadersLength = 0
        self.identifier = ""
        self.extraHeadersStr = ""
        self.dataLength = 0

    def crcAsHex(self):
        return "0x{:08X}".format(self.crc)

    @property
    def sampleRate(self):
        return (
            self.sampleRatePeriod
            if self.sampleRatePeriod >= 0
            else -1.0 / self.sampleRatePeriod
        )

    @property
    def samplePeriod(self):
        return (
            -1 * self.sampleRatePeriod
            if self.sampleRatePeriod < 0
            else 1.0 / self.sampleRatePeriod
        )

    def pack(self):
        header = bytearray(FIXED_HEADER_SIZE)
        OFFSET = 0
        struct.pack_into(
            HEADER_PACK_FORMAT,
            header,
            OFFSET,
            b"M",
            b"S",
            3,
            self.flags,
            self.nanosecond,
            self.year,
            self.dayOfYear,
            self.hour,
            self.minute,
            self.second,
            self.encoding,
            self.sampleRatePeriod,
            self.numSamples,
            self.crc,
            self.publicationVersion,
            self.identifierLength,
            self.extraHeadersLength,
            self.dataLength,
        )
        return header

    def recordSize(self):
        return (
            FIXED_HEADER_SIZE
            + self.identifierLength
            + self.extraHeadersLength
            + self.dataLength
        )

    @property
    def starttime(self):
        st = datetime(
            self.year,
            1,
            1,
            hour=self.hour,
            minute=self.minute,
            second=self.second,
            microsecond=int(self.nanosecond / 1000),
            tzinfo=timezone.utc,
        )
        # start Jan 1, so shift by dayOfYear minus 1
        doyMinusOne = timedelta(days=self.dayOfYear-1)
        return st + doyMinusOne

    @starttime.setter
    def starttime(self, stime):
        dt = None
        if type(stime).__name__ == "datetime":
            dt = stime
        elif type(stime).__name__ == "str":
            fixTZ = stime.replace("Z", "+00:00")
            dt = datetime.fromisoformat(fixTZ)
        else:
            raise MiniseedException(f"unknown type of starttime {type(stime)}")

        # make sure timezone aware
        st = None
        if not dt.tzinfo:
            st = dt.replace(tzinfo=timezone.utc)
        else:
            st = dt.astimezone(timezone.utc)
        tt = st.timetuple()
        self.year = tt.tm_year
        self.dayOfYear = tt.tm_yday
        self.hour = tt.tm_hour
        self.minute = tt.tm_min
        self.second = tt.tm_sec
        self.nanosecond = st.microsecond * 1000

    @property
    def endtime(self):
        return self.starttime + timedelta(
            seconds=self.samplePeriod * (self.numSamples - 1)
        )

    def clone(self):
        ms3header = MSeed3Header()
        ms3header.flags = self.flags
        ms3header.nanosecond = self.nanosecond
        ms3header.year = self.year
        ms3header.dayOfYear = self.dayOfYear
        ms3header.hour = self.hour
        ms3header.minute = self.minute
        ms3header.second = self.second
        ms3header.encoding = self.encoding
        ms3header.sampleRatePeriod = self.sampleRatePeriod
        ms3header.numSamples = self.numSamples
        ms3header.crc = self.crc
        ms3header.publicationVersion = self.publicationVersion
        ms3header.identifierLength = self.identifierLength
        ms3header.extraHeadersLength = self.extraHeadersLength
        ms3header.dataLength = self.dataLength
        return ms3header

    def sanityCheck(self):
        out = True
        out = out and self.year >= 0 and self.year < 3000
        out = out and self.dayOfYear >= 1 and self.dayOfYear <= 366
        out = out and self.hour >= 0 and self.hour < 24
        out = out and self.minute >= 0 and self.minute <= 60
        out = out and self.second >= 0 and self.second <= 60
        return out


class MSeed3Record:
    header: MSeed3Header
    identifier: str
    _eh: Union[str, dict, None]
    encodedData: EncodedDataSegment

    def __init__(
        self,
        header: MSeed3Header,
        identifier: Union[FDSNSourceId, str],
        data,
        extraHeaders: Union[str, dict, None] = None,
    ):
        self.header = header
        self._eh = extraHeaders
        self.identifier = identifier
        if isinstance(data, EncodedDataSegment):
            self.encodedData = data
        elif isinstance(data, bytes) or isinstance(data, bytearray):
            self.encodedData = (
                EncodedDataSegment(header.encoding, data, header.numSamples, True),
            )
        elif isinstance(data, array):
            self.header.encoding = mseed3EncodingFromArrayTypecode(data.typecode)
            self.encodedData = compress(self.header.encoding, data)
        elif isinstance(data, numpy.ndarray):
            self.header.encoding = mseed3EncodingFromNumpyDT(data.dtype)
            if data.dtype.byteorder == ">":
                data = data.newbyteorder("<")
            self.encodedData = compress(self.header.encoding, data)
        else:
            # try to compress with given type?
            self.encodedData = compress(self.header.encoding, data)
        # header encoding from actual data, consistency
        self.header.encoding = self.encodedData.compressionType
        self.header.numSamples = self.encodedData.numSamples

    @property
    def eh(self):
        if self._eh is not None and isinstance(self._eh, str):
            if len(self._eh) > 0:
                self._eh = json.loads(self._eh)
            else:
                self.eh = {}
        return self._eh

    @eh.setter
    def eh(self, ehDict):
        self._eh = ehDict
        if self._eh is not None and isinstance(self._eh, str):
            self.header.extraHeadersLength = len(self._eh.encode("UTF-8"))
        else:
            self.header.extraHeadersLength = None

    @eh.deleter
    def eh(self):
        del self._eh
        self.header.extraHeadersLength = 0

    def decompress(self):
        data = None
        if self.encodedData is not None:
            byteOrder = LITTLE_ENDIAN
            if (
                self.header.encoding == STEIM1
                or self.header.encoding == STEIM2
                or self.header.encoding == STEIM3
            ):
                byteOrder = BIG_ENDIAN
            data = decompress(
                self.header.encoding,
                self.encodedData.dataBytes,
                self.header.numSamples,
                byteOrder == LITTLE_ENDIAN,
            )
        return data

    def decompressedRecord(self):
        """
        Create a new record with decompressed data and the header encoding
        set to one of the primitive types: short, int, float or double
        """
        data = self.decompress()
        header = self.header.clone()
        header.encoding = mseed3EncodingFromNumpyDT(data.dtype)
        return MSeed3Record(header, self.identifier, data, self._eh)

    @property
    def starttime(self):
        return self.header.starttime

    @property
    def endtime(self):
        return self.header.endtime

    def hasExtraHeaders(self):
        if self._eh is None:
            return False
        elif isinstance(self._eh, dict) and len(self._eh) > 0:
            return True
        elif isinstance(self._eh, str) and len(self._eh) > 2:
            return True
        return False

    def clone(self):
        return unpackMiniseedRecord(self.pack())

    def getSize(self):
        """
        Calculates the size of the record. Returns None if any of the
        identifier, extra headers or data lengths are not yet calculated.
        """
        if (
            self.header.identifierLength is not None
            and self.header.extraHeadersLength is not None
            and self.header.dataLength
        ):
            return (
                FIXED_HEADER_SIZE
                + self.header.identifierLength
                + self.header.extraHeadersLength
                + self.header.dataLength
            )
        else:
            return None

    def pack(self):
        """
        Pack the record contents into a bytearray. Header values for the lengths
        are updated, so the record header represents the output bytes after
        packing.
        """
        self.header.crc = 0
        # string to bytes
        if isinstance(self.identifier, FDSNSourceId):
            self.identifier = str(self.identifier)
        identifierBytes = self.identifier.encode("UTF-8")
        self.header.identifierLength = len(identifierBytes)
        if self._eh is None:
            extraHeadersStr = ""
        elif isinstance(self._eh, dict):
            extraHeadersStr = json.dumps(self._eh)
        elif isinstance(self._eh, str):
            extraHeadersStr = self._eh
        else:
            extraHeadersStr = ""
        extraHeadersBytes = extraHeadersStr.encode("UTF-8")
        self.header.extraHeadersLength = len(extraHeadersBytes)
        self.header.dataLength = len(self.encodedData.dataBytes)
        rec_size = (
            FIXED_HEADER_SIZE
            + self.header.identifierLength
            + self.header.extraHeadersLength
            + self.header.dataLength
        )

        recordBytes = bytearray(rec_size)
        recordBytes[0:FIXED_HEADER_SIZE] = self.header.pack()
        offset = FIXED_HEADER_SIZE
        recordBytes[offset : offset + self.header.identifierLength] = identifierBytes
        offset += self.header.identifierLength
        recordBytes[offset : offset + self.header.extraHeadersLength] = (
            extraHeadersBytes
        )
        offset += self.header.extraHeadersLength
        recordBytes[offset : offset + self.header.dataLength] = (
            self.encodedData.dataBytes
        )

        struct.pack_into("<I", recordBytes, CRC_OFFSET, 0)
        crc = crc32c.crc32c(recordBytes)
        struct.pack_into("<I", recordBytes, CRC_OFFSET, crc)
        self.header.crc = crc
        return recordBytes

    def __str__(self):
        return self.summary()

    def summary(self):
        return f"{self.identifier} {isoWZ(self.header.starttime)} {isoWZ(self.header.endtime)} ({self.header.numSamples} pts)"

    def encodingName(self):
        encode_name = f"unknown ({self.header.encoding})"
        if self.header.encoding == 0:
            encode_name = "Text"
        elif self.header.encoding == 1:
            encode_name = "16-bit integer"
        elif self.header.encoding == 3:
            encode_name = "32-bit integer"
        elif self.header.encoding == 4:
            encode_name = "32-bit floats"
        elif self.header.encoding == 5:
            encode_name = "64-bit floats"
        elif self.header.encoding == 11:
            encode_name = "STEIM-2 integer compression"
        elif self.header.encoding == 10:
            encode_name = "STEIM-1 integer compression"
        elif self.header.encoding == 19:
            encode_name = "STEIM-3 integer compression"
        elif self.header.encoding == 100:
            encode_name = "Opaque data"
        return encode_name

    def details(self, showExtraHeaders=True, showData=False):

        encode_name = self.encodingName()

        bitFlagStr = ""
        if self.header.flags & 0x01:
            bitFlagStr = f"""{bitFlagStr}
                             [Bit 0] Calibration signals present"""
        if self.header.flags & 0x02:
            bitFlagStr = f"""{bitFlagStr}
                             [Bit 1] Time tag is questionable"""
        if self.header.flags & 0x04:
            bitFlagStr = f"""{bitFlagStr}
                             [Bit 2] Clock locked"""
        if self.header.flags & 0x08:
            bitFlagStr = f"""{bitFlagStr}
                             [Bit 3] Undefined bit set"""
        if self.header.flags & 0x10:
            bitFlagStr = f"""{bitFlagStr}
                             [Bit 4] Undefined bit set"""
        if self.header.flags & 0x20:
            bitFlagStr = f"""{bitFlagStr}
                             [Bit 5] Undefined bit set"""
        if self.header.flags & 0x40:
            bitFlagStr = f"""{bitFlagStr}
                             [Bit 6] Undefined bit set"""
        if self.header.flags & 0x80:
            bitFlagStr = f"""{bitFlagStr}
                             [Bit 7] Undefined bit set"""
        ehLines = ""
        if showExtraHeaders and self.hasExtraHeaders():
            ehLines = json.dumps(self.eh, indent=2).split("\n")
        indentLines = "\n          ".join(ehLines)
        out = f"""\
          {self.identifier}, version {self.header.publicationVersion}, {self.getSize()} bytes (format: {self.header.formatVersion})
                       start time: {isoWZ(self.starttime)} ({self.header.dayOfYear:03})
                number of samples: {self.header.numSamples}
                 sample rate (Hz): {self.header.sampleRate}
                            flags: [{self.header.flags:>08b}] 8 bits{bitFlagStr}
                              CRC: {self.header.crcAsHex()}
              extra header length: {self.header.extraHeadersLength} bytes
              data payload length: {self.header.dataLength} bytes
                 payload encoding: {encode_name} (val: {self.header.encoding})
                    extra headers: {indentLines}
                    """
        if showData:
            out = out + "data: \n"
            line = ""
            data = self.decompress()
            for i in range(self.header.numSamples):
                line += " {:<8}".format(data[i])
                if i % 10 == 9:
                    line += "\n"
                    out += line
                    line = ""
            if len(line) > 0:
                out += line
        return out


def unpackMSeed3FixedHeader(recordBytes):
    if len(recordBytes) < FIXED_HEADER_SIZE:
        raise MiniseedException(
            "Not enough bytes for header: {:d}".format(len(recordBytes))
        )
    ms3header = MSeed3Header()

    (
        recordIndicatorM,
        recordIndicatorS,
        formatVersion,
        ms3header.flags,
        ms3header.nanosecond,
        ms3header.year,
        ms3header.dayOfYear,
        ms3header.hour,
        ms3header.minute,
        ms3header.second,
        ms3header.encoding,
        ms3header.sampleRatePeriod,
        ms3header.numSamples,
        ms3header.crc,
        ms3header.publicationVersion,
        ms3header.identifierLength,
        ms3header.extraHeadersLength,
        ms3header.dataLength,
    ) = struct.unpack(HEADER_PACK_FORMAT, recordBytes[0:FIXED_HEADER_SIZE])
    if recordIndicatorM != b"M" or recordIndicatorS != b"S":
        raise MiniseedException(
            f"expected record start to be MS but was {recordIndicatorM}{recordIndicatorS}"
        )
    return ms3header


def unpackMSeed3Record(recordBytes, check_crc=True):
    crc = 0
    ms3header = unpackMSeed3FixedHeader(recordBytes)
    if check_crc:
        tempBytes = bytearray(recordBytes[:FIXED_HEADER_SIZE])
        struct.pack_into("<I", tempBytes, CRC_OFFSET, 0)
        crc = crc32c.crc32c(tempBytes)
    offset = FIXED_HEADER_SIZE
    idBytes = recordBytes[offset : offset + ms3header.identifierLength]
    if check_crc:
        crc = crc32c.crc32c(idBytes, crc)
    identifier = idBytes.decode("utf-8")
    offset += ms3header.identifierLength
    ehBytes = recordBytes[offset : offset + ms3header.extraHeadersLength]
    if check_crc:
        crc = crc32c.crc32c(ehBytes, crc)
    extraHeadersStr = ehBytes.decode("utf-8")
    offset += ms3header.extraHeadersLength

    encodedDataBytes = recordBytes[offset : offset + ms3header.dataLength]
    if check_crc:
        crc = crc32c.crc32c(encodedDataBytes, crc)
    offset += ms3header.dataLength
    if check_crc and ms3header.crc != crc:
        raise MiniseedException(f"crc fail:  Calc: {crc}  Header: {ms3header.crc}")
    encodedData = EncodedDataSegment(
        ms3header.encoding, encodedDataBytes, ms3header.numSamples, True
    )
    ms3Rec = MSeed3Record(
        ms3header, identifier, encodedData, extraHeaders=extraHeadersStr
    )
    return ms3Rec


def readMSeed3Records(fileptr, check_crc=True, matchsid=None, merge=False, verbose=False):
    matchPat = None
    prev = None
    if matchsid is not None:
        matchPat = re.compile(matchsid)
    while True:
        headBytes = fileptr.read(FIXED_HEADER_SIZE)
        if len(headBytes) == 0:
            # no more to read, eof
            break
        ms3header = unpackMSeed3FixedHeader(headBytes)
        crc = 0
        if check_crc:
            crcHeadBytes = bytearray(headBytes)
            struct.pack_into("<I", crcHeadBytes, CRC_OFFSET, 0)
            crc = crc32c.crc32c(crcHeadBytes)
        identifierBytes = fileptr.read(ms3header.identifierLength)
        if check_crc:
            crc = crc32c.crc32c(identifierBytes, crc)
        identifier = identifierBytes.decode("utf-8")
        if matchPat is None or matchPat.search(identifier) is not None:
            # match pass
            ehBytes = fileptr.read(ms3header.extraHeadersLength)
            if check_crc:
                crc = crc32c.crc32c(ehBytes, crc)
            extraHeadersStr = ehBytes.decode("utf-8")
            encodedDataBytes = fileptr.read(ms3header.dataLength)
            if check_crc:
                crc = crc32c.crc32c(encodedDataBytes, crc)
                if ms3header.crc != crc:
                    raise MiniseedException(f"crc fail:  Calc: {crc}  Header: {ms3header.crc}")

            encodedData = EncodedDataSegment(
                ms3header.encoding, encodedDataBytes, ms3header.numSamples, True
            )
            ms3 = MSeed3Record(ms3header, identifier, encodedData, extraHeaders=extraHeadersStr)
            if verbose:
                print(f"MSeed3Record {ms3}")
            if merge and canDecompress(ms3.header.encoding):
                ms3 = ms3.decompressedRecord()
                mlist = mseed3merge(prev, ms3)
                if len(mlist) == 2:
                    prev = mlist[1]
                    yield mlist[0]
                else:
                    prev = mlist[0]
            else:
                yield ms3
        else:
            # failed match, can skip ahead to next record
            if verbose:
                print(f"match fail, {identifier} skip")
            fileptr.seek(ms3header.extraHeadersLength, 1)
            fileptr.seek(ms3header.dataLength, 1)
    if prev is not None:
        yield prev


def areCompatible(ms3a: MSeed3Record, ms3b: MSeed3Record, timeTolFactor=0.5) -> bool:
    out = True
    out = out and ms3a.identifier == ms3b.identifier
    out = out and ms3b.header.sampleRatePeriod == ms3b.header.sampleRatePeriod
    out = out and ms3a.header.encoding == ms3b.header.encoding
    out = out and ms3a.header.publicationVersion == ms3b.header.publicationVersion
    out = out and ms3a.endtime < ms3b.starttime
    if out:
        predNextStart = ms3a.starttime + timedelta(
            seconds=ms3a.header.samplePeriod * ms3a.header.numSamples
        )
        out = (
            out
            and (ms3b.starttime - predNextStart).total_seconds()
            < ms3a.header.samplePeriod * timeTolFactor
        )
    return out


def mseed3merge(ms3a: MSeed3Record, ms3b: MSeed3Record) -> list[MSeed3Record]:
    """
    Merges two MSeed3Records if possible. Returned list will have either
    both original records if merge is not possible, or a single new
    record if merge was.
    Note extra headers are taken from the first record and any headers in the
    second record are ignored. Merging of dict structures just seems to hard
    to be done automatically, without understanding the meaning of the items.
    """
    out = [ms3a, ms3b]
    if ms3a is None and ms3b is not None:
        out = [ms3b]
    elif ms3a is not None and ms3b is None:
        out = [ms3a]
    elif ms3a is None and ms3b is None:
        # maybe should raise instead???
        out = [None]
    elif ms3a.header.encoding == 0 or ms3a.header.encoding > 5:
        # only primitve encoding currently are mergable
        pass
    elif areCompatible(ms3a, ms3b):
        header = ms3a.header.clone()
        header.numSamples += ms3b.header.numSamples
        dataBytes = bytearray()
        dataBytes.extend(ms3a.encodedData.dataBytes)
        dataBytes.extend(ms3b.encodedData.dataBytes)
        encodedData = EncodedDataSegment(
            ms3a.encodedData.compressionType,
            dataBytes,
            header.numSamples,
            ms3a.encodedData.littleEndian,
        )
        if ms3a.hasExtraHeaders():
            eh = json.loads(json.dumps(ms3a.eh))
        else:
            eh = None
        merged = MSeed3Record(header, ms3a.identifier, encodedData, eh)
        out = [merged]
    return out


def crcAsHex(crc):
    return "0x{:08X}".format(crc)


def isoWZ(time) -> str:
    return time.isoformat().replace("+00:00", "Z")
