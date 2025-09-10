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
        assert sid.validate()[0] == True
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
        assert sid_nslc.validate()[0] == True
        assert sid_nslc.networkCode == net
        assert sid_nslc.stationCode == sta
        assert sid_nslc.locationCode == loc
        assert sid_nslc.bandCode == band
        assert sid_nslc.sourceCode == s
        assert sid_nslc.subsourceCode == subs
        assert sid == sid_nslc

        sid_dotnslc = simplemseed.FDSNSourceId.parseNslc(chanDotNslc, sep=".")
        assert sid_dotnslc.validate()[0] == True
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
        assert sid_nslcparts.validate()[0] == True
        assert sid_nslcparts.networkCode == net
        assert sid_nslcparts.stationCode == sta
        assert sid_nslcparts.locationCode == loc
        assert sid_nslcparts.bandCode == band
        assert sid_nslcparts.sourceCode == s
        assert sid_nslcparts.subsourceCode == subs
        assert sid == sid_nslcparts

        sid_nslclong = simplemseed.FDSNSourceId.fromNslc(
            net, sta, loc, f"{band}_{s}X_{subs}"
        )
        assert sid_nslclong.validate()[0] == True
        assert sid_nslclong.networkCode == net
        assert sid_nslclong.stationCode == sta
        assert sid_nslclong.locationCode == loc
        assert sid_nslclong.bandCode == band
        assert sid_nslclong.sourceCode == f"{s}X"
        assert sid_nslclong.subsourceCode == subs

        staSidStr = "FDSN:CO_JSC"
        staSid = sid.stationSourceId()
        assert staSid.validate()[0] == True
        assert staSid.networkCode == net
        assert staSid.stationCode == sta
        staSid2 = simplemseed.FDSNSourceId.parse(staSidStr)
        assert staSid == staSid2
        assert str(staSid) == str(staSid2)

        netSid = sid.networkSourceId()
        assert netSid.validate()[0] == True
        netSidStr = "FDSN:CO"
        netSid2 = simplemseed.FDSNSourceId.parse(netSidStr)
        assert netSid2.validate()[0] == True
        assert sid.networkSourceId() == netSid
        assert netSid == netSid2
        assert str(netSid) == str(netSid2)

        unknown = simplemseed.FDSNSourceId.createUnknown()
        assert unknown.validate()[0] == True, unknown.validate()[1]
        assert unknown.networkCode == "XX"
        assert unknown.stationCode == "ABC"
        unknown_100sps = simplemseed.FDSNSourceId.createUnknown(100, sourceCode="H")
        assert unknown_100sps.validate()[0] == True
        assert unknown_100sps.bandCode == "E"
        assert unknown_100sps.sourceCode == "H"
        assert unknown_100sps.subsourceCode == "U"
        unknown_100sps = simplemseed.FDSNSourceId.createUnknown(
            100, response_lb=1 / 120
        )
        assert unknown_100sps.validate()[0] == True
        assert unknown_100sps.bandCode == "H"
        unknown_1sps = simplemseed.FDSNSourceId.createUnknown(1)
        assert unknown_1sps.validate()[0] == True
        assert unknown_1sps.bandCode == "L"
        unknown_100sec = simplemseed.FDSNSourceId.createUnknown(0.01)
        assert unknown_100sec.validate()[0] == True
        assert unknown_100sec.bandCode == "U"
        unknown_netsta = simplemseed.FDSNSourceId.createUnknown(
            100, sourceCode="H", subsourceCode="X", networkCode="CO", stationCode="QWERTY"
        )
        assert unknown_netsta.validate()[0] == True
        assert unknown_netsta.stationCode == "QWERTY"
        assert unknown_netsta.networkCode == "CO"
        assert unknown_netsta.sourceCode == "H"
        assert unknown_netsta.subsourceCode == "X"
        assert unknown_netsta.bandCode == "E"


    def test_long_sid(self):
        net = "XX2025"
        sta = "BIGGYBIG"
        loc = "01234567"
        band = "L"
        s = "RQQ"
        subs = "Z"
        chanSourceId = f"FDSN:{net}_{sta}_{loc}_{band}_{s}_{subs}"
        sid = simplemseed.FDSNSourceId.parse(chanSourceId)
        assert sid.validate()[0] == True
        assert sid.networkCode == net
        assert sid.stationCode == sta
        assert sid.locationCode == loc
        assert sid.bandCode == band
        assert sid.sourceCode == s
        assert sid.subsourceCode == subs

    def test_sid_empty_loc_subs(self):
        net = "XX2025"
        sta = "BIGGYBIG"
        loc = ""
        band = "L"
        s = "RQQ"
        subs = ""
        chanSourceId = f"FDSN:{net}_{sta}_{loc}_{band}_{s}_{subs}"
        sid = simplemseed.FDSNSourceId.parse(chanSourceId)
        assert sid.validate()[0] == True
        assert sid.networkCode == net
        assert sid.stationCode == sta
        assert sid.locationCode == loc
        assert sid.bandCode == band
        assert sid.sourceCode == s
        assert sid.subsourceCode == subs

        sid = simplemseed.FDSNSourceId.fromNslc(net, sta, loc, f"{band}_{s}_{subs}")
        assert sid.validate()[0] == True
        assert sid.networkCode == net
        assert sid.stationCode == sta
        assert sid.locationCode == loc
        assert sid.bandCode == band
        assert sid.sourceCode == s
        assert sid.subsourceCode == subs

    def test_dash_sid(self):
        net = "XX2025"
        sta = "BIGGYBIG"
        loc = "01234567"
        band = "L"
        s = "RQQ"
        subs = "Z"

        netDash = "XX-2025"
        chanSourceId = f"FDSN:{netDash}_{sta}_{loc}_{band}_{s}_{subs}"
        sid = simplemseed.FDSNSourceId.parse(chanSourceId)
        assert sid.validate()[0] == False
        staDash = "BIG-BIG"
        chanSourceId = f"FDSN:{net}_{staDash}_{loc}_{band}_{s}_{subs}"
        sid = simplemseed.FDSNSourceId.parse(chanSourceId)
        assert sid.validate()[0] == True
        locDash = "012-3456"
        chanSourceId = f"FDSN:{net}_{sta}_{locDash}_{band}_{s}_{subs}"
        sid = simplemseed.FDSNSourceId.parse(chanSourceId)
        assert sid.validate()[0] == True
        sDash = "R-Q"
        chanSourceId = f"FDSN:{net}_{sta}_{loc}_{band}_{sDash}_{subs}"
        sid = simplemseed.FDSNSourceId.parse(chanSourceId)
        assert sid.validate()[0] == False
        subsDash = "A-Z"
        chanSourceId = f"FDSN:{net}_{sta}_{loc}_{band}_{s}_{subsDash}"
        sid = simplemseed.FDSNSourceId.parse(chanSourceId)
        assert sid.validate()[0] == False

    def test_temp_net(self):

        net = "FDSN:ABCD2025"
        sid = simplemseed.FDSNSourceId.parse(net)
        assert sid.validate()[0] == True
        assert isinstance(sid,  simplemseed.NetworkSourceId)
        assert sid.isTempNetConvention() == True
        assert sid.isTempNetHistorical() == False
        assert sid.isSeedTempNet() == False
        assert sid.isTemporary() == True
        net = "FDSN:XD1994"
        sid = simplemseed.FDSNSourceId.parse(net)
        assert sid.validate()[0] == True
        assert isinstance(sid,  simplemseed.NetworkSourceId)
        assert sid.isTempNetConvention() == True
        assert sid.isTempNetHistorical() == True
        assert sid.isSeedTempNet() == False
        assert sid.isTemporary() == True
        net = "FDSN:XD"
        sid = simplemseed.FDSNSourceId.parse(net)
        assert sid.validate()[0] == True
        assert isinstance(sid,  simplemseed.NetworkSourceId)
        assert sid.isTempNetConvention() == False
        assert sid.isTempNetHistorical() == False
        assert sid.isSeedTempNet() == True
        assert sid.isTemporary() == True
        net = "FDSN:CO"
        sid = simplemseed.FDSNSourceId.parse(net)
        assert sid.validate()[0] == True
        assert isinstance(sid,  simplemseed.NetworkSourceId)
        assert sid.isTempNetConvention() == False
        assert sid.isTempNetHistorical() == False
        assert sid.isSeedTempNet() == False
        assert sid.isTemporary() == False
        net = "FDSN:XX"
        sid = simplemseed.FDSNSourceId.parse(net)
        assert sid.validate()[0] == True
        assert isinstance(sid,  simplemseed.NetworkSourceId)
        assert sid.isTempNetConvention() == False
        assert sid.isTempNetHistorical() == False
        assert sid.isSeedTempNet() == False
        assert sid.isTemporary() == False

    def test_band_code(self):
        assert simplemseed.bandCodeForRate(None) == 'I'
        assert simplemseed.bandCodeForRate(0) == 'I'
        assert simplemseed.bandCodeForRate(20 ) == 'S'
        assert simplemseed.bandCodeForRate(20, -100) == 'B'
        assert simplemseed.bandCodeForRate(20, 0.5) == 'S'
        assert simplemseed.bandCodeForRate(1.0 ) == 'L'
        assert simplemseed.bandCodeForRate(-10.0 ) == 'V'
