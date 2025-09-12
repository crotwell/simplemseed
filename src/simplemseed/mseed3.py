import struct
from array import array
from datetime import datetime, timedelta, timezone
import json
import re
from typing import Union, Optional

import numpy as np
import crc32c

from .seedcodec import (
    canDecompress,
    decompress,
    encode,
    STEIM1,
    STEIM2,
    STEIM3,
    EncodedDataSegment,
    mseed3EncodingFromArrayTypecode,
    mseed3EncodingFromNumpyDT,
    numpyDTFromMseed3Encoding,
    UnsupportedCompressionType,
    BIG_ENDIAN,
    LITTLE_ENDIAN,
    encodingName,
)
from .fdsnsourceid import FDSNSourceId, FDSN_PREFIX
from .util import isoWZ

MINISEED_THREE_MIME = "application/vnd.fdsn.mseed3"
""" MIME type for miniseed3, 'application/vnd.fdsn.mseed3'. """

MS_RECORD_INDICATOR = "MS"
""" Record header indicator, ASCII 'MS'"""

MS_FORMAT_VERSION_3 = 3
""" Format version, Value of 3"""

UNKNOWN_PUBLICATION_VERSION = 0
"""const for unknown data version, 0 """

CRC_OFFSET = 28
"""const for offset to crc in record, 28"""

FIXED_HEADER_SIZE = 40
"""const for size of fixed header part of record, 40"""

HEADER_PACK_FORMAT = "<ccBBIHHBBBBdIIBBHI"
"""const python struct pack format for fixed header."""


class MSeed3Header:
    """
    Represents the fixed header section of a mseed3 record.

    See the [specification](http://docs.fdsn.org/projects/miniseed3/en/latest/).

    Fixed header is defined as:

    +--------------------+--------------------------+-------+------+------+---------------------+
    |Field               |Description               |Type   |Length|Offset|Content              |
    +====================+==========================+=======+======+======+=====================+
    |1                   |Record header indicator   |CHAR   |2     |0     |ASCII 'MS'           |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |2                   |Format version            |UINT8  |1     |2     |Value of 3           |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |3                   |Flags                     |UINT8  |1     |3     |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |                    |Record start time         |       |      |      |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |4a                  |Nanosecond (0 - 999999999)|UINT32 |4     |4     |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |4b                  |Year (0-65535)            |UINT16 |2     |8     |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |4c                  |Day-of-year  (1 - 366)    |UINT16 |2     |10    |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |4d                  |Hour (0 - 23)             |UINT8  |1     |12    |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |4e                  |Minute (0 - 59)           |UINT8  |1     |13    |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |4f                  |Second (0 - 60)           |UINT8  |1     |14    |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |5                   |Data payload encoding     |UINT8  |1     |15    |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |6                   |Sample rate/period        |FLOAT64|8     |16    |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |7                   |Number of samples         |UINT32 |4     |24    |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |8                   |CRC of the record         |UINT32 |4     |28    |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |9                   |Data publication version  |UINT8  |1     |32    |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |10                  |Length of identifier      |UINT8  |1     |33    |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |11                  |Length of extra headers   |UINT16 |2     |34    |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    |12                  |Length of data payload    |UINT32 |4     |36    |                     |
    +--------------------+--------------------------+-------+------+------+---------------------+
    """

    recordIndicator: str
    """ Record header indicator, 'MS'. """
    formatVersion: int
    """ Format version, 3. """
    flags: int
    """ Flags. """
    nanosecond: int
    """ Start time nanoseconds. """
    year: int
    """ Start time year. """
    dayOfYear: int
    """ Start time day of year. """
    hour: int
    """ Start time hours. """
    minute: int
    """ Start time minutes. """
    second: int
    """ Start time seconds. """
    encoding: int
    """ Data payload encoding."""
    sampleRatePeriod: float
    """ Sample rate/period."""
    numSamples: int
    """ Number of samples."""
    crc: int
    """ CRC of the record."""
    publicationVersion: int
    """ Data publication version."""
    identifierLength: int
    """ Length of identifier."""
    extraHeadersLength: int
    """ Length of extra headers."""
    dataLength: int
    """ Length of data payload."""

    def __init__(self):
        """
        Create a valid but empty fixed header.

        See unpackMSeed3FixedHeader() to parse form bytes.
        """
        self.recordIndicator = MS_RECORD_INDICATOR
        self.formatVersion = MS_FORMAT_VERSION_3
        self.flags = 0
        self.nanosecond = 0
        self.year = 1970
        self.dayOfYear = 1
        self.hour = 0
        self.minute = 0
        self.second = 0
        self.encoding = -1  # autoset from data if possible

        self.sampleRatePeriod = 1
        self.numSamples = 0
        self.crc = 0
        self.publicationVersion = UNKNOWN_PUBLICATION_VERSION
        self.identifierLength = 0
        self.extraHeadersLength = 0
        self.identifier = ""
        self.extraHeadersStr = ""
        self.dataLength = 0

    def crcAsHex(self):
        """ String representation of CRC for record."""
        return f"0x{self.crc:08X}"

    @property
    def sampleRate(self):
        """ Sampling as a rate, number of samples per second."""
        return (
            self.sampleRatePeriod
            if self.sampleRatePeriod >= 0
            else -1.0 / self.sampleRatePeriod
        )

    @sampleRate.setter
    def sampleRate(self, val):
        self.sampleRatePeriod = val

    @property
    def samplePeriod(self):
        """ Sampling as a period, number of seconds between samples."""
        return (
            -1 * self.sampleRatePeriod
            if self.sampleRatePeriod < 0
            else 1.0 / self.sampleRatePeriod
        )

    @samplePeriod.setter
    def samplePeriod(self, val):
        self.sampleRatePeriod = -1 * val

    def pack(self):
        """ Pack into byte array."""
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
        """ Total record size in bytes."""
        return (
            FIXED_HEADER_SIZE
            + self.identifierLength
            + self.extraHeadersLength
            + self.dataLength
        )

    @property
    def starttime(self):
        """ Start time of record, time of first sample. """
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
        doyMinusOne = timedelta(days=self.dayOfYear - 1)
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
            raise Miniseed3Exception(f"unknown type of starttime {type(stime)}")

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
        """ End time of record, time of last sample. """
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
        """ Validation checks. """
        out = True
        out = out and self.year >= 0 and self.year < 3000
        out = out and self.dayOfYear >= 1 and self.dayOfYear <= 366
        out = out and self.hour >= 0 and self.hour < 24
        out = out and self.minute >= 0 and self.minute < 60
        out = out and self.second >= 0 and self.second <= 60
        return out


class MSeed3Record:
    """
    Represents a mseed3 record.

    See the [specification](http://docs.fdsn.org/projects/miniseed3/en/latest/).
    """

    header: MSeed3Header
    identifier: Union[FDSNSourceId, str]
    _eh: Union[str, dict, None]
    _data: Optional[Union[np.ndarray, array, list[int], list[float]]]

    def __init__(
        self,
        header: MSeed3Header,
        identifier: Union[FDSNSourceId, str],
        data: Union[np.ndarray, bytes, bytearray, array, list[int], list[float]],
        extraHeaders: Union[str, dict, None] = None,
    ):
        self.header = header
        self.identifier = identifier
        self._eh = extraHeaders
        self._internal_set_data(data)

    def _internal_set_data(self, data):
        """
        Set data based on type.

        Checks and sets header values for encoding and numSamples.
        """
        if data is None:
            self._data = None
            encoding = 0
            numSamples = 0
        elif isinstance(data, EncodedDataSegment):
            self._data = data.dataBytes
            encoding = data.compressionType
            numSamples = data.numSamples
        elif isinstance(data, (bytes, bytearray)):
            # bytes, hopefully header.numSamples set correctly
            self._data = data
            encoding = self.header.encoding
            numSamples = self.header.numSamples
        elif isinstance(data, array):
            # array.array primitive
            encoding = mseed3EncodingFromArrayTypecode(data.typecode, data.itemsize)
            numSamples = len(data)
            self._data = data
        elif isinstance(data, np.ndarray):
            # numpy array
            if len(np.shape(data)) != 1:
                raise Miniseed3Exception(f"numpy array not one dimensional: {np.shape(data)}")
            # special case for int64
            if np.issubdtype(data.dtype, np.integer) and \
                    not np.can_cast(data.dtype, np.int32, casting="safe"):
                if abs(np.max(data)) > np.iinfo(np.int32).max:
                    raise Miniseed3Exception(f"max value of numpy array, {np.max(data)} cannot fit into 32 bit integer")
                data = data.astype(np.int32)

            encoding = mseed3EncodingFromNumpyDT(data.dtype)
            numSamples = len(data)
            self._data = data
        elif isinstance(data, list):
            # list of numbers, use numpy?
            #
            if self.header.encoding == -1:
                encoding = 4  # default to 32 bit floats?
            else:
                encoding = self.header.encoding
            self._data = np.array(data, dtype=numpyDTFromMseed3Encoding(encoding))
            encoding = mseed3EncodingFromNumpyDT(self._data.dtype)
            numSamples = len(self._data)
        else:
            raise Miniseed3Exception(f"unknown data type: {type(data)}")
        # set if header has defaults
        if self.header.encoding == -1:
            self.header.encoding = encoding
        if self.header.numSamples == 0:
            self.header.numSamples = numSamples
        # sanity check with headers
        if self.header.encoding != encoding:
            raise Miniseed3Exception(
                f"Mismatched encoding: {self.header.encoding} != {encoding}"
            )
        if self.header.numSamples != numSamples:
            raise Miniseed3Exception(
                f"Mismatched num samples: {self.header.numSamples} != {numSamples}"
            )

    @property
    def eh(self):
        """ Extra headers, from json."""
        if self._eh is not None and isinstance(self._eh, str):
            if len(self._eh) > 0:
                self._eh = json.loads(self._eh)
            else:
                self._eh = {}
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

    def parseIdentifier(self) -> FDSNSourceId:
        """
        Parse identifier as an FDSNSOurceId.

        Identifier must start with 'FDSN:' to be parsed.
        """
        if isinstance(self.identifier, FDSNSourceId):
            return self.identifier
        # assume string
        if self.identifier.startswith(FDSN_PREFIX):
            return FDSNSourceId.parse(self.identifier)
        raise Miniseed3Exception("Unable to parse identifier as FDSN SourceId")

    def decompress(self) -> np.ndarray:
        """ Decompress data to an numpy ndarray."""
        data = None
        if self._data is None:
            raise UnsupportedCompressionType("data is missing in record")

        if isinstance(self._data, np.ndarray):
            # already decompressed
            data = self._data
        elif isinstance(self._data, array):
            # already decompressed
            data = np.array(self._data)
        elif isinstance(self._data, (bytes, bytearray)):
            # try to decompress bytes-like
            byteOrder = LITTLE_ENDIAN
            if (
                self.header.encoding in ( STEIM1, STEIM2, STEIM3)
            ):
                byteOrder = BIG_ENDIAN
            data = decompress(
                self.header.encoding,
                self._data,
                self.header.numSamples,
                byteOrder == LITTLE_ENDIAN,
            )
        else:
            raise UnsupportedCompressionType(
                f"encoding {self.header.encoding} not supported"
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
        """ Start time of record, time of first sample."""
        return self.header.starttime

    @property
    def endtime(self):
        """  End time of record, time of last sample."""
        return self.header.endtime

    def hasExtraHeaders(self):
        """ True if record contains extra headers, ie json is not empty."""
        if self._eh is None:
            return False
        if isinstance(self._eh, dict) and len(self._eh) > 0:
            return True
        if isinstance(self._eh, str) and len(self._eh) > 2:
            return True
        return False

    def clone(self):
        return unpackMSeed3Record(self.pack())

    def getSize(self):
        """
        Calculates the size of the record.

        Returns None if any of the
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
        return None

    def encodedDataBytes(self):
        """ Encodes data into bytes."""
        if isinstance(self._data, (bytearray, bytes)):
            return self._data
        return encode(self._data, self.header.encoding, littleEndian = True).dataBytes

    def pack(self):
        """
        Pack the record contents into a bytearray.

        Header values for the lengths and CRC
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
        if self._data is None:
            dataBytes = bytes(0)
        elif isinstance(self._data, (bytearray, bytes)):
            # already byte-like, so just use
            dataBytes = self._data
        else:
            encData = encode(self._data, self.header.encoding, littleEndian=True)
            if encData.compressionType != self.header.encoding:
                raise Miniseed3Exception(
                    f"Header encoding {self.header.encoding} not same as data {encData.compressionType}"
                )
            dataBytes = encData.dataBytes

        self.header.dataLength = len(dataBytes)
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
        recordBytes[offset : offset + self.header.dataLength] = dataBytes

        struct.pack_into("<I", recordBytes, CRC_OFFSET, 0)
        crc = crc32c.crc32c(recordBytes)
        struct.pack_into("<I", recordBytes, CRC_OFFSET, crc)
        self.header.crc = crc
        return recordBytes

    def __str__(self):
        return self.summary()

    def summary(self):
        """ One line summary of the record."""
        return f"{self.identifier} {isoWZ(self.header.starttime)} {isoWZ(self.header.endtime)} ({self.header.numSamples} pts)"

    def encodingName(self):
        """ Name of encoding, for display."""
        return encodingName(self.header.encoding)

    def details(self, showExtraHeaders=True, showData=False):
        """ More detailed description of record."""
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
                line += f" {data[i]:<8}"
                if i % 10 == 9:
                    line += "\n"
                    out += line
                    line = ""
            if len(line) > 0:
                out += line
        return out


def unpackMSeed3FixedHeader(recordBytes):
    """
    Unpacks a fixed header from bytes.

    Returns a MSeed3Header object.
    """
    if len(recordBytes) < FIXED_HEADER_SIZE:
        raise Miniseed3Exception(
            f"Not enough bytes for header: {len(recordBytes)}"
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
        raise Miniseed3Exception(
            f"expected record start to be MS but was {recordIndicatorM}{recordIndicatorS}"
        )
    if formatVersion != MS_FORMAT_VERSION_3:
        raise Miniseed3Exception(
            f"expected format version to be ${MS_FORMAT_VERSION_3} but was {formatVersion}"
        )
    return ms3header


def unpackMSeed3Record(recordBytes, check_crc=True):
    """
    Unpack a miniseed3 record from bytes, optionally verifying the CRC.

    Returns a MSeed3Record object.
    """
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
        raise Miniseed3Exception(f"crc fail:  Calc: {crc}  Header: {ms3header.crc}")
    ms3Rec = MSeed3Record(
        ms3header, identifier, encodedDataBytes, extraHeaders=extraHeadersStr
    )
    return ms3Rec


def readMSeed3Records(
    fileptr, check_crc=True, matchsid=None, merge=False, verbose=False
):
    """
    Generator to read miniseed3 records from a file-like object.

    Optionally filter on matchsid regular expression.
    Also optionally merge contiguous records.

    Example:
    .. code-block:: python

        for msr in simplemseed.readMSeed3Records(infile):
            # do something...
            pass
    """
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
                    raise Miniseed3Exception(
                        f"crc fail:  Calc: {crc}  Header: {ms3header.crc}"
                    )

            ms3 = MSeed3Record(
                ms3header, identifier, encodedDataBytes, extraHeaders=extraHeadersStr
            )
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
    """
    Check if two miniseed3 records are mergable.

    This requires same identifier, sample rate, data encoding and publication
    version, and that the record times are adjacent.
    """
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
    Merges two MSeed3Records if possible.

    Returned list will have either
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
        encodedDataBytes = bytearray()
        encodedDataBytes.extend(ms3a.encodedDataBytes())
        encodedDataBytes.extend(ms3b.encodedDataBytes())
        if ms3a.hasExtraHeaders():
            eh = json.loads(json.dumps(ms3a.eh))
        else:
            eh = None
        merged = MSeed3Record(header, ms3a.identifier, encodedDataBytes, eh)
        out = [merged]
    return out


def crcAsHex(crc):
    """ CRC as printable string."""
    return f"0x{crc:08X}"


class Miniseed3Exception(Exception):
    """ Exception in parsing a miniseed3 record from bytes-like."""
    pass
