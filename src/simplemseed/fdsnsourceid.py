"""
Philip Crotwell
University of South Carolina, 2022
http://www.seis.sc.edu
"""

from typing import Union, Optional
import argparse
import json
import re
from importlib import resources as importlib_resources

FDSN_PREFIX = "FDSN:"
"""const for fdsn prefix for extra headers, 'FDSN:'. Note includes colon."""

SEP = "_"
"""const default separator. """

BAND_CODE_JSON = {}
""" Band codes, description, and rates."""

bandcodes_file = importlib_resources.files(__package__) / "bandcode.json"

def loadBandCodes():
    with bandcodes_file.open("rb") as f:
        # load as json array
        bcList = json.load(f)
        # convert to dict by code
        for bc in bcList:
            BAND_CODE_JSON[bc["code"]] = bc
loadBandCodes()

SOURCE_CODE_JSON = {}
""" Source codes and descriptions."""

sourcecodes_file = importlib_resources.files(__package__) / "sourcecode.json"
def loadSourceCodes():
    with sourcecodes_file.open("rb") as f:
        # load as json array
        bcList = json.load(f)
        # convert to dict by code
        for bc in bcList:
            SOURCE_CODE_JSON[bc["code"]] = bc
loadSourceCodes()


class FDSNSourceId:
    """
    A FDSN Source Id, as defined in the
    [specification](http://docs.fdsn.org/projects/source-identifiers/en/v1.0/)
    """

    networkCode: str
    stationCode: str
    locationCode: str
    bandCode: str
    sourceCode: str
    subsourceCode: str

    def __init__(
        self,
        networkCode: str,
        stationCode: str,
        locationCode: str,
        bandCode: str,
        sourceCode: str,
        subsourceCode: str,
    ):
        self.networkCode = networkCode
        self.stationCode = stationCode
        self.locationCode = locationCode
        self.bandCode = bandCode
        self.sourceCode = sourceCode
        self.subsourceCode = subsourceCode

    @staticmethod
    def createUnknown(
        sampRate: Optional[Union[float, int]] = None,
        sourceCode: str = "H",
        response_lb: Optional[Union[float, int]] = None,
        networkCode: str = "XX",
        stationCode: str = "ABC",
        locationCode: str = "",
        subsourceCode: str = "U",
    ) -> "FDSNSourceId":
        """
        Creates a Source Id for non-real data.

        This will have network code XX,
        which is defined to be a "do not use" network. The band code can be
        calculated based on the optional sample rate and response lower bound.
        See bandCodeForRate() for details.
        """
        if len(networkCode) == 0:
            networkCode = "XX"
        if len(stationCode) == 0:
            stationCode = "ABC"
        return FDSNSourceId(
            networkCode,
            stationCode,
            locationCode,
            bandCodeForRate(sampRate, response_lb),
            sourceCode,
            subsourceCode,
        )

    @staticmethod
    def parse(
        sid: str,
    ) -> Union[
        "FDSNSourceId", "NetworkSourceId", "StationSourceId", "LocationSourceId"
    ]:
        """
        Parse a FDSN Source Id string, like FDSN:CO_BIRD_00_H_H_Z into its constituant parts.

        Also will handle parsing abbreviated codes for
        network, FDSN:CO
        station, FDSN:CO_BIRD
        location, FDSN:CO_BIRD_00
        """
        if not sid.startswith(FDSN_PREFIX):
            raise FDSNSourceIdException(f"sourceid must start with {FDSN_PREFIX}: {sid}")

        items = sid[len(FDSN_PREFIX) :].split(SEP)
        if len(items) == 1:
            return NetworkSourceId(items[0])
        if len(items) == 2:
            return StationSourceId(items[0], items[1])
        if len(items) == 3:
            return LocationSourceId(items[0], items[1], items[2])
        if len(items) != 6:
            raise FDSNSourceIdException(
                f"FDSN sourceid must have 6 items for channel, 3 for loc, 2 for station or 1 for network; separated by '{SEP}': {sid}"
            )

        return FDSNSourceId(items[0], items[1], items[2], items[3], items[4], items[5])

    @staticmethod
    def fromNslc(net: str, sta: str, loc: str, channelCode: str) -> "FDSNSourceId":
        """
        Create a FDSN Source Id from an older seed-style nslc, network, station
        location, channel.
        """
        if len(channelCode) == 3:
            band = channelCode[0]
            source = channelCode[1]
            subsource = channelCode[2]
        else:
            b_s_ss = r"(\w)_(\w+)_(\w+)"
            match = re.match(b_s_ss, channelCode)
            if match:
                band = match[1]
                source = match[2]
                subsource = match[3]
            else:
                raise FDSNSourceIdException(
                    f"channel code must be length 3 or have 3 items separated by '{SEP}': {channelCode}"
                )

        return FDSNSourceId(net, sta, loc, band, source, subsource)

    @staticmethod
    def parseNslc(nslc: str, sep=".") -> "FDSNSourceId":
        """
        Create a FDSN Source Id by parsing an older seed-style nslc, network, station
        location, channel, wheret the 4 sections are separated by the given
        separator, which defaults to a dot, '.'.
        """
        items = nslc.split(sep)
        if len(items) < 4:
            raise FDSNSourceIdException(
                f"channel nslc must have 4 items separated by '{sep}': {nslc}"
            )

        return FDSNSourceId.fromNslc(items[0], items[1], items[2], items[3])

    def validate(self) -> (bool, Union[str, None]):
        """
        Validates a source id, primarily for length limitations.

        Returns a tuple of either (True, None) or (False, <reason>)
        """
        (valid, reason) = self.locationSourceId().validate()
        if not valid:
            return (valid, reason)
        # band code allowed to be empty
        if len(self.sourceCode) == 0:
            return (False, "Source code empty")
        # Subsource code allowed to be empty
        return (True, "")

    def locationSourceId(self) -> "LocationSourceId":
        """The location sourceid containing this channel. """
        return LocationSourceId(self.networkCode, self.stationCode, self.locationCode)

    def stationSourceId(self) -> "StationSourceId":
        """The station sourceid containing this channel. """
        return StationSourceId(self.networkCode, self.stationCode)

    def networkSourceId(self) -> "NetworkSourceId":
        """The network sourceid containing this channel. """
        return NetworkSourceId(self.networkCode)

    def shortChannelCode(self) -> str:
        """
        Convert the channel part of the source id into an older seed-style nslc.

        If the source and subsource are single characters, then a 3 char
        channel code will be created, like BHZ. But if any are larger, then
        a longer string with separators will be creates, like B_AA_QW
        """
        if (
            len(self.bandCode) == 1
            and len(self.sourceCode) == 1
            and len(self.subsourceCode) == 1
        ):
            chanCode = f"{self.bandCode}{self.sourceCode}{self.subsourceCode}"
        else:
            chanCode = f"{self.bandCode}{SEP}{self.sourceCode}{SEP}{self.subsourceCode}"
        return chanCode

    def asNslc(self) -> "NslcId":
        """
        Convert the source id into an older seed-style nslc.

        If the source and subsource are single characters, then a 3 char
        channel code will be created, like BHZ. But if any are larger, then
        a longer string with separators will be creates, like B_AA_QW
        """
        chanCode = self.shortChannelCode()
        return NslcId(self.networkCode, self.stationCode, self.locationCode, chanCode)

    def __str__(self) -> str:
        return f"{FDSN_PREFIX}{self.networkCode}{SEP}{self.stationCode}{SEP}{self.locationCode}{SEP}{self.bandCode}{SEP}{self.sourceCode}{SEP}{self.subsourceCode}"

    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, self.__class__):
            return False
        # both FDSNSourceId, so compare as strings is easy
        return str(self) == str(other)


class NetworkSourceId:
    """
    An abbreviated source id representing a network, like FDSN:CO
    """

    networkCode: str

    def __init__(self, networkCode: str):
        self.networkCode = networkCode

    def validate(self) -> (bool, Union[str, None]):
        """Validation checks."""
        if len(self.networkCode) == 0:
            return (False, "Network code empty")
        if len(self.networkCode) > 8:
            return (False, f"Network code > 8 chars, len({self.networkCode})>8")
        return (True, "")

    def __str__(self) -> str:
        return f"{FDSN_PREFIX}{self.networkCode}"

    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return str(self) == str(other)


class StationSourceId:
    """
    An abbreviated source id representing a station, like FDSN:CO_BIRD
    """

    networkCode: str
    stationCode: str

    def __init__(self, networkCode: str, stationCode: str):
        self.networkCode = networkCode
        self.stationCode = stationCode

    def validate(self) -> (bool, Union[str, None]):
        """Validation checks."""
        (valid, reason) = self.networkSourceId().validate()
        if not valid:
            return (valid, reason)
        if len(self.stationCode) == 0:
            return (False, "Station code empty")
        if len(self.stationCode) > 8:
            return (False, f"Station code > 8 chars, len({self.stationCode})>8")
        return (True, "")

    def __str__(self) -> str:
        return f"{FDSN_PREFIX}{self.networkCode}{SEP}{self.stationCode}"

    def networkSourceId(self) -> "NetworkSourceId":
        return NetworkSourceId(self.networkCode)

    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return str(self) == str(other)


class LocationSourceId:
    """
    An abbreviated source id representing a station-location,
    like `FDSN:CO_BIRD_00`

    Note if the location segment in zero length, the code will end with
    the underscore like `FDSN:IU_ANMO_`
    """

    networkCode: str
    stationCode: str
    locationCode: str

    def __init__(self, networkCode: str, stationCode: str, locationCode: str):
        self.networkCode = networkCode
        self.stationCode = stationCode
        self.locationCode = locationCode

    def validate(self) -> (bool, Union[str, None]):
        """Validation checks."""
        (valid, reason) = self.stationSourceId().validate()
        if not valid:
            return (valid, reason)
        if self.locationCode == "--":
            return (False, "Location code cannot be '--'")
        if len(self.locationCode) > 8:
            return (False, f"Location code > 8 chars, len({self.locationCode})>8")
        return (True, "")

    def stationSourceId(self) -> "StationSourceId":
        return StationSourceId(self.networkCode, self.stationCode)

    def networkSourceId(self) -> "NetworkSourceId":
        return NetworkSourceId(self.networkCode)

    def __str__(self) -> str:
        return f"{FDSN_PREFIX}{self.networkCode}{SEP}{self.stationCode}{SEP}{self.locationCode}"

    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return str(self) == str(other)


def bandCodeForRate(
    sampRatePeriod: Optional[Union[float, int]] = None,
    response_lb: Optional[Union[float, int]] = None,
) -> str:
    """
    Calculates the band code for the given sample rate/period.

    Optionally taking into
    account the lower bound of the response, response_lb, to distinguish
    broadband from short period in the higher sample rates, where
    0.1 hertz is the boundary.

    If sampRatePeriod is negative, then interpreted as a period instead of a rate.
    So 0.1 and -10 both mean one sample every 10 seconds. Similar for response_lb.

    See http://docs.fdsn.org/projects/source-identifiers/en/v1.0/channel-codes.html#band-code
    """
    if sampRatePeriod is None or sampRatePeriod == 0:
        return "I"

    sampRate = sampRatePeriod if sampRatePeriod > 0 else -1.0/sampRatePeriod
    respHz = response_lb if response_lb is None or response_lb >= 0 else -1.0/response_lb

    if sampRate >= 5000:
        return "J"
    if 1000 <= sampRate < 5000:
        if respHz is not None and respHz < 0.1:
            return "F"
        return "G"
    if 250 <= sampRate < 1000:
        if respHz is not None and respHz < 0.1:
            return "C"
        return "D"
    if 80 <= sampRate < 250:
        if respHz is not None and respHz < 0.1:
            return "H"
        return "E"
    if 10 <= sampRate < 80:
        if respHz is not None and respHz < 0.1:
            return "B"
        return "S"
    if 1 < sampRate < 10:
        return "M"
    if 0.5 < sampRate < 1.5:
        # spec not clear about how far from 1 is L
        return "L"
    if 0.1 <= sampRate < 1:
        return "V"
    if 0.01 <= sampRate < 0.1:
        return "U"
    if 0.001 <= sampRate < 0.01:
        return "W"
    if 0.0001 <= sampRate < 0.001:
        return "R"
    if 0.00001 <= sampRate < 0.0001:
        return "P"
    if 0.000001 <= sampRate < 0.00001:
        return "T"
    if sampRate < 0.000001:
        return "Q"
    raise FDSNSourceIdException(
        f"Unable to calc band code for rate: {sampRatePeriod}, low corner: {response_lb}"
    )


def bandCodeInfo(bandCode: str):
    """
    Type, rate and response lower bound describing the band code.

    {'type': 'Very Long Period', 'rate': '>= 0.1 to < 1', 'response_lb': ''}

    See http://docs.fdsn.org/projects/source-identifiers/en/v1.0/channel-codes.html#band-code
    """
    return BAND_CODE_JSON[bandCode]


def bandCodeDescribe(
    bandCode: str,
) -> str:
    """
    Describe the band code.

    See http://docs.fdsn.org/projects/source-identifiers/en/v1.0/channel-codes.html#band-code
    """
    bc = bandCodeInfo(bandCode)
    bandD = f"{bc['type']}, {bc['rate']} Hz"
    if len(bc["response_lb"]) > 0:
        bandD += f", response period {bc['response_lb']}"
    return bandD


def sourceCodeInfo(sourceCode: str):
    """
    Type, describing the source code.

    { "code": "H", "type": "High Gain Seismometer" }

    See http://docs.fdsn.org/projects/source-identifiers/en/v1.0/channel-codes.html
    """
    return SOURCE_CODE_JSON[sourceCode]


def sourceCodeDescribe(
    sourceCode: str,
) -> str:
    """
    Describe the source code.

    See http://docs.fdsn.org/projects/source-identifiers/en/v1.0/channel-codes.html
    """
    bc = sourceCodeInfo(sourceCode)
    bandD = f"{bc['type']}"
    return bandD


class NslcId:
    """
    Older style NSLC SEED Id. Consists of 2 char network,
    5 char station, 2 char location and 3 char channel.
    """
    networkCode: str
    stationCode: str
    locationCode: str
    channelCode: str

    def __init__(self, net: str, sta: str, loc: str, chan: str):
        self.networkCode = net
        self.stationCode = sta
        self.locationCode = loc
        self.channelCode = chan

    def __str__(self) -> str:
        return f"{self.networkCode}_{self.stationCode}_{self.locationCode}_{self.channelCode}"

    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return str(self) == str(other)


class FDSNSourceIdException(Exception):
    pass


def do_parseargs():
    parser = argparse.ArgumentParser(description="Parsing of FDSN Sourceids.")
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    parser.add_argument(
        "-b", "--band", nargs="+", required=False, help="describe band code"
    )
    parser.add_argument(
        "-s", "--source", nargs="+", required=False, help="describe source code"
    )
    parser.add_argument(
        "--sps", required=False, type=float, help="band code for sample rate"
    )
    parser.add_argument("sid", nargs="*", help="source id to print")
    return parser.parse_args()


def main():
    args = do_parseargs()
    if args.sps:
        bbc = bandCodeForRate(args.sps, 0.01)
        spc = bandCodeForRate(args.sps, 10)
        print(f"      Rate: {args.sps} - {bbc} - {bandCodeDescribe(bbc)}")
        if bbc != spc:
            print(f"      Rate: {args.sps} - {spc} - {bandCodeDescribe(spc)}")

    if args.band is not None:
        for bands in args.band:
            # in case no space between arg chars
            for bandCode in bands:
                print(f"      Band: {bandCode} - {bandCodeDescribe(bandCode)}")

    if args.source is not None:
        for sourceCode in args.source:
            print(f"    Source: {sourceCode} - {sourceCodeDescribe(sourceCode)}")
            print(f"       {SOURCE_CODE_JSON[sourceCode]['desc']}")

    for a in args.sid:
        sid = FDSNSourceId.parse(a)
        print(f"      {sid}")
        print(f"       Net: {sid.networkCode}")
        print(f"       Sta: {sid.stationCode}")
        print(f"       Loc: {sid.locationCode}")
        print(f"      Band: {sid.bandCode} - {bandCodeDescribe(sid.bandCode)}")
        print(f"    Source: {sid.sourceCode} - {sourceCodeDescribe(sid.sourceCode)}")
        print(f" Subsource: {sid.subsourceCode}")


if __name__ == "__main__":
    main()
