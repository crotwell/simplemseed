# Philip Crotwell
# University of South Carolina, 2019
# https://www.seis.sc.edu
# /
# converted from Steim2.java in seedCodec
# https:#github.com/crotwell/seedcodec/
# constants for compression types


import array
import struct
from typing import Union

import numpy

from .exceptions import CodecException, UnsupportedCompressionType
from .steim1 import decodeSteim1
from .steim2 import decodeSteim2


# ascii
ASCII: int = 0

# 16 bit integer, or java short
SHORT: int = 1

# 24 bit integer
INT24: int = 2

# 32 bit integer, or java int
INTEGER: int = 3

# ieee float
FLOAT: int = 4

# ieee double
DOUBLE: int = 5

# Steim1 compression
STEIM1: int = 10

# Steim2 compression
STEIM2: int = 11

# Steim2 compression, not implemented
STEIM3: int = 19

# CDSN 16 bit gain ranged
CDSN: int = 16

# (A)SRO
SRO: int = 30

# DWWSSN 16 bit
DWWSSN: int = 32



def isFloatCompression(compressionType: int) -> bool:
    """
    True if the compression is not representable by integers, so not
    compressable via the standard compression types.
    """
    if compressionType in (FLOAT, DOUBLE):
        return True
    return False


class EncodedDataSegment:
    """
    A holder for compressed data independent of the file format.
    """

    compressionType: int
    dataBytes: Union[bytes, bytearray]
    numSamples: int
    littleEndian: bool

    def __init__(
        self,
        compressionType,
        dataBytes: Union[bytes, bytearray],
        numSamples,
        littleEndian: bool,
    ):
        self.compressionType = compressionType
        self.dataBytes = dataBytes
        self.numSamples = numSamples
        self.littleEndian = littleEndian

    def isFloatCompression(self) -> bool:
        return isFloatCompression(self.compressionType)

    def decode(self):
        return decompress(
            self.compressionType,
            self.dataBytes,
            self.numSamples,
            self.littleEndian,
        )


def canDecompress(encoding: int) -> bool:
    """
    True if the given encoding can be decompressed by this library.
    """
    return encoding in (SHORT, INTEGER, FLOAT, DOUBLE, STEIM1, STEIM2)


def arrayTypecodeFromMSeed(encoding: int) -> str:
    """
    Get the typecode for a python array.array from the mseed encoding type.
    """
    if encoding == SHORT:
        return "h"
    if encoding == INTEGER:
        return "l"
    if encoding == FLOAT:
        return "f"
    if encoding == DOUBLE:
        return "d"
    raise UnsupportedCompressionType(f"type {encoding} not mapable to python array")


def mseed3EncodingFromArrayTypecode(typecode: str, itemsize: int) -> int:
    """
    Get the mseed3 encoding type for a python array.arry typecode and itemsize.
    """
    if typecode in ("h", "i", "l"):
        if itemsize == 2:
            return SHORT
        if itemsize == 4:
            return INTEGER
    elif typecode in ("f", "d"):
        if itemsize == 4:
            return FLOAT
        if itemsize == 8:
            return DOUBLE
    raise UnsupportedCompressionType(
        f"typecode {typecode} of size {itemsize} not mapable to mseed encoding, only h,i,l,f,d and 2,4,8"
    )


def mseed3EncodingFromNumpyDT(dt: numpy.dtype) -> int:
    """
    Get the mseed3 encoding for a numpy dtype code
    """
    if dt.type is numpy.int16:
        return SHORT
    if dt.type is numpy.int32:
        return INTEGER
    if dt.type is numpy.float32:
        return FLOAT
    if dt.type is numpy.float64:
        return DOUBLE
    raise UnsupportedCompressionType(
        f"numpy type {dt.type} not mapable to mseed encoding"
    )


def numpyDTFromMseed3Encoding(encoding: int):
    """
    Get a numpy dtype for a mseed3 encoding
    """
    if encoding == SHORT:
        return numpy.int16
    if encoding == INTEGER:
        return numpy.int32
    if encoding == FLOAT:
        return numpy.float32
    if encoding == DOUBLE:
        return numpy.float64
    raise UnsupportedCompressionType(
        f"mseed encoding {encoding} not mapable to numpy type"
    )


def encode(data, encoding=None, littleEndian=True):
    """
    Encode the given numpy.ndarray or array.array into bytes.

    Note that currently no actual compression is done, the resulting
    bytes will occupy the same space, just converted for output.
    If encoding is not given, the encoding will be guessed from the array type.
    If endian is given, defaults to little endian.
    """
    if isinstance(data, (bytearray, bytes)):
        # already byte-like, so ???
        raise UnsupportedCompressionType("Unable to encode data, already bytes-like")
    if encoding is None or encoding < 0:
        # try to guess a primitive encoding
        if isinstance(data, numpy.ndarray):
            encoding = mseed3EncodingFromNumpyDT(data.dtype)
        elif isinstance(data, array.array):
            encoding = mseed3EncodingFromArrayTypecode(data.typecode, data.itemsize)
        else:
            raise UnsupportedCompressionType(
                "Unable to guess encoding for data, encoding is " + encoding
            )
    try:
        compCode = arrayTypecodeFromMSeed(encoding)
    except UnsupportedCompressionType as exc:
        if encoding == STEIM1:
            raise UnsupportedCompressionType(f'see encodeSteim1() for encoding STEIM1 ({STEIM1}) ') from exc
        if encoding == STEIM2:
            raise UnsupportedCompressionType(f'see encodeSteim2() for encoding STEIM2 ({STEIM2}) ') from exc
        raise UnsupportedCompressionType(f'type {encoding} not supported for encoding') from exc

    endianChar = "<" if littleEndian else ">"
    dataBytes = struct.pack(f"{endianChar}{len(data)}{compCode}", *data)
    return EncodedDataSegment(encoding, dataBytes, len(data), littleEndian)


def decompress(
    compressionType: int,
    dataBytes: bytearray,
    numSamples: int,
    littleEndian: bool,
) -> numpy.ndarray:
    """
    Decompress the samples from the provided bytes and
    return an array of the decompressed values.
    Only 16 bit short, 32 bit int, 32 bit float and 64 bit double
    along with Steim1 and Steim2 are supported.

    @param compressionType compression format as defined in SEED blockette 1000
    @param dataBytes input bytes to be decoded
    @param numSamples the number of samples that can be decoded from array
    <b>b</b>
    @param littleEndian if True, dataBytes is little-endian (intel byte order) <b>b</b>.
    @returns array of length <b>numSamples</b>.
    @throws CodecException fail to decompress.
    @throws UnsupportedCompressionType unsupported compression type
    """

    # in case of record with no data points, ex detection blockette, which often have compression type
    # set to 0, which messes up the decompresser even though it doesn't matter since there is no data.
    if numSamples == 0:
        dt = numpy.dtype(numpy.int32)
        dt = dt.newbyteorder("<")
        return numpy.asarray([], dt)

    # switch (compressionType):
    if compressionType in (SHORT, DWWSSN):
        # 16 bit values
        if len(dataBytes) < 2 * numSamples:
            raise CodecException(
                f"Not enough bytes for {numSamples} 16 bit data points, only {len(dataBytes)} bytes.",
            )
        dt = numpy.dtype(numpy.int16)
        if littleEndian:
            dt = dt.newbyteorder("<")
        else:
            dt = dt.newbyteorder(">")
        out = numpy.frombuffer(dataBytes, dtype=dt, count=numSamples)

    elif compressionType == INTEGER:
        # 32 bit integers
        if len(dataBytes) < 4 * numSamples:
            raise CodecException(
                f"Not enough bytes for {numSamples} 32 bit data points, only {len(dataBytes)} bytes.",
            )

        dt = numpy.dtype(numpy.int32)
        if littleEndian:
            dt = dt.newbyteorder("<")
        else:
            dt = dt.newbyteorder(">")
        out = numpy.frombuffer(dataBytes, dtype=dt, count=numSamples)
    elif compressionType == FLOAT:
        # 32 bit floats
        if len(dataBytes) < 4 * numSamples:
            raise CodecException(
                f"Not enough bytes for {numSamples} 32 bit data points, only {len(dataBytes)} bytes.",
            )

        dt = numpy.dtype(numpy.float32)
        if littleEndian:
            dt = dt.newbyteorder("<")
        else:
            dt = dt.newbyteorder(">")
        out = numpy.frombuffer(dataBytes, dtype=dt, count=numSamples)

    elif compressionType == DOUBLE:
        # 64 bit doubles
        if len(dataBytes) < 8 * numSamples:
            raise CodecException(
                f"Not enough bytes for {numSamples} 64 bit data points, only {len(dataBytes)} bytes.",
            )

        dt = numpy.dtype(numpy.float64)
        if littleEndian:
            dt = dt.newbyteorder("<")
        else:
            dt = dt.newbyteorder(">")
        out = numpy.frombuffer(dataBytes, dtype=dt, count=numSamples)

    elif compressionType == STEIM1:
        # steim 1
        out = decodeSteim1(dataBytes, numSamples, 0)

    elif compressionType == STEIM2:
        # steim 2
        out = decodeSteim2(dataBytes, numSamples, 0)

    else:
        # unknown format????
        raise UnsupportedCompressionType(
            f"Type {compressionType} is not supported at this time, numsamples: {numSamples}.",
        )

    # end of switch ()
    return out


def getFloat64(dataBytes, offset, littleEndian):
    endianChar = "<" if littleEndian else ">"
    vals = struct.unpack(endianChar + "d", dataBytes[offset : offset + 8])
    return vals[0]
