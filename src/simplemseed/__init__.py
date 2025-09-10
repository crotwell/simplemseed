__version__ = "0.5.0-dev"
version = __version__
"Current version"

from .mseed3 import (
    unpackMSeed3Record,
    unpackMSeed3FixedHeader,
    readMSeed3Records,
    MSeed3Header,
    MSeed3Record,
    Miniseed3Exception,
    MS_RECORD_INDICATOR,
    MS_FORMAT_VERSION_3,
    CRC_OFFSET,
    FIXED_HEADER_SIZE,
    UNKNOWN_PUBLICATION_VERSION,
    mseed3merge,
    crcAsHex,
    MINISEED_THREE_MIME,
)

from .miniseed import (
    MiniseedHeader,
    MiniseedRecord,
    unpackMiniseedHeader,
    unpackMiniseedRecord,
    unpackBlockette,
    MiniseedException,
    readMiniseed2Records,
)
from .fdsnsourceid import (
    FDSN_PREFIX,
    SINGLE_STATION_NETCODE,
    TESTDATA_NETCODE,
    FDSNSourceId,
    NetworkSourceId,
    StationSourceId,
    LocationSourceId,
    bandCodeForRate,
    NslcId,
    bandCodeDescribe,
    sourceCodeDescribe,
)
from .seedcodec import (
    encode,
    decompress,
    canDecompress,
    BIG_ENDIAN,
    LITTLE_ENDIAN,
    isPrimitiveCompression,
    EncodedDataSegment,
    STEIM1, STEIM2,
    encodingName,
)
from .exceptions import (
    CodecException,
    UnsupportedCompressionType,
)
from .steim1 import decodeSteim1, encodeSteim1, encodeSteim1FrameBlock
from .steim2 import decodeSteim2, encodeSteim2, encodeSteim2FrameBlock
from .steimframeblock import SteimFrameBlock
from .mseed2to3 import mseed2to3
from .util import isoWZ

__all__ = [
    "MiniseedHeader",
    "MiniseedRecord",
    "MiniseedException",
    "unpackMiniseedHeader",
    "unpackMiniseedRecord",
    "readMiniseed2Records",
    "unpackMSeed3Record",
    "unpackMSeed3FixedHeader",
    "readMSeed3Records",
    "MSeed3Header",
    "MSeed3Record",
    "Miniseed3Exception",
    "CRC_OFFSET",
    "FIXED_HEADER_SIZE",
    "unpackBlockette",
    "FDSN_PREFIX",
    "SINGLE_STATION_NETCODE",
    "TESTDATA_NETCODE",
    "FDSNSourceId",
    "NslcId",
    "NetworkSourceId",
    "StationSourceId",
    "LocationSourceId",
    "bandCodeForRate",
    "bandCodeDescribe",
    "sourceCodeDescribe",
    "canDecompress",
    "encode",
    "decompress",
    "encodingName",
    "CodecException",
    "UnsupportedCompressionType",
    "decodeSteim1",
    "encodeSteim1",
    "encodeSteim1FrameBlock",
    "decodeSteim2",
    "encodeSteim2",
    "encodeSteim2FrameBlock",
    "SteimFrameBlock",
    "mseed2to3",
    "crcAsHex",
    "isoWZ",
    "mseed3merge",
    "BIG_ENDIAN",
    "LITTLE_ENDIAN",
    "isPrimitiveCompression",
    "STEIM1",
    "STEIM2",
    "version"
]
