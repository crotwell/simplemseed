import simplemseed


class TestSourceId:
    def test_sid(self):
        net = "CO"
        sta = "JSC"
        loc = "00"
        band = "L"
        s = "H"
        subs = "Z"

        chanSourceId = f"FDSN:{net}_{sta}_{loc}_{band}_{s}_{subs}"
        chanSourceIdStr = "FDSN:CO_JSC_00_L_H_Z"
        assert chanSourceId == chanSourceIdStr
        chanNslc = "CO_JSC_00_LHZ"
        chanDotNslc = "CO.JSC.00.LHZ"

        sid = simplemseed.FDSNSourceId.parse(chanSourceId)
        assert sid.networkCode == net
        assert sid.stationCode == sta
        assert sid.locationCode == loc
        assert sid.bandCode == band
        assert sid.sourceCode == s
        assert sid.subsourceCode == subs

        nslc = sid.asNslc()
        assert str(nslc) == chanNslc
        assert nslc.networkCode == net
        assert nslc.stationCode == sta
        assert nslc.locationCode == loc
        assert nslc.channelCode == f"{band}{s}{subs}"

        sid_nslc = simplemseed.FDSNSourceId.parseNslc(chanNslc, sep="_")
        assert sid_nslc.networkCode == net
        assert sid_nslc.stationCode == sta
        assert sid_nslc.locationCode == loc
        assert sid_nslc.bandCode == band
        assert sid_nslc.sourceCode == s
        assert sid_nslc.subsourceCode == subs
        assert sid == sid_nslc

        sid_dotnslc = simplemseed.FDSNSourceId.parseNslc(chanDotNslc, sep=".")
        assert sid_dotnslc.networkCode == net
        assert sid_dotnslc.stationCode == sta
        assert sid_dotnslc.locationCode == loc
        assert sid_dotnslc.bandCode == band
        assert sid_dotnslc.sourceCode == s
        assert sid_dotnslc.subsourceCode == subs
        assert sid == sid_dotnslc

        sid_nslcparts = simplemseed.FDSNSourceId.fromNslc(
            net, sta, loc, f"{band}{s}{subs}"
        )
        assert sid_nslcparts.networkCode == net
        assert sid_nslcparts.stationCode == sta
        assert sid_nslcparts.locationCode == loc
        assert sid_nslcparts.bandCode == band
        assert sid_nslcparts.sourceCode == s
        assert sid_nslcparts.subsourceCode == subs
        assert sid == sid_nslcparts

        staSidStr = "FDSN:CO_JSC"
        staSid = sid.stationSourceId()
        assert staSid.networkCode == net
        assert staSid.stationCode == sta
        staSid2 = simplemseed.FDSNSourceId.parse(staSidStr)
        assert staSid == staSid2
        assert str(staSid) == str(staSid2)

        netSid = sid.networkSourceId()
        netSidStr = "FDSN:CO"
        netSid2 = simplemseed.FDSNSourceId.parse(netSidStr)
        assert sid.networkSourceId() == netSid
        assert netSid == netSid2
        assert str(netSid) == str(netSid2)

        unknown = simplemseed.FDSNSourceId.createUnknown()
        assert unknown.networkCode == "XX"
        assert unknown.stationCode == "ABC"
        unknown_100sps = simplemseed.FDSNSourceId.createUnknown(100, sourceCode="H")
        assert unknown_100sps.bandCode == "E"
        assert unknown_100sps.sourceCode == "H"
        assert unknown_100sps.subsourceCode == "U"
        unknown_100sps = simplemseed.FDSNSourceId.createUnknown(
            100, response_lb=1 / 120
        )
        assert unknown_100sps.bandCode == "H"
        unknown_1sps = simplemseed.FDSNSourceId.createUnknown(1)
        assert unknown_1sps.bandCode == "L"
        unknown_100sec = simplemseed.FDSNSourceId.createUnknown(0.01)
        assert unknown_100sec.bandCode == "U"
        unknown_netsta = simplemseed.FDSNSourceId.createUnknown(100,
                                                                sourceCode="H",
                                                                networkCode="CO",
                                                                stationCode="QWERTY")
        assert unknown_netsta.stationCode == "QWERTY"
        assert unknown_netsta.networkCode == "CO"
