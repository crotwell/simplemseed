import simplemseed

chanSourceId = "FDSN:CO_JSC_00_H_H_Z"
chanNslc = "CO_JSC_00_HHZ"

# parse a SID
sid = simplemseed.FDSNSourceId.parse(chanSourceId)
print(sid)
# parse old style net_sta_loc_chan
sid2 = simplemseed.FDSNSourceId.parseNslc(chanNslc, sep="_")
print(sid2)
# form from net, sta, loc, chan
sid3 = simplemseed.FDSNSourceId.fromNslc("CO", "JSC", "00", "HHZ")
print(sid3)
# all should be equivalent
print(sid == sid2)
print(sid == sid3)

# just net, station part
print(sid.stationSourceId())
print(sid.stationSourceId() == sid2.stationSourceId())
print(sid.stationSourceId() == simplemseed.FDSNSourceId.parse("FDSN:CO_JSC"))

# just network part
print(sid.networkSourceId())
print(sid.networkSourceId() == sid2.networkSourceId())
print(sid.networkSourceId() == simplemseed.FDSNSourceId.parse("FDSN:CO"))

# create other subsources (orientations)
loc_sid = sid.locationSourceId()
bhn_sid = loc_sid.createFDSNSourceId(sid.bandCode, sid.sourceCode, "N")
bhe_sid = loc_sid.createFDSNSourceId(sid.bandCode, sid.sourceCode, "E")
print(f"BHZ chan: {sid}")
print(f"BHN chan: {bhn_sid}")
print(f"BHE chan: {bhe_sid}")
print()

# create some "fake" channels based on sample rate
print(simplemseed.FDSNSourceId.createUnknown())
print(simplemseed.FDSNSourceId.createUnknown(100))
print(simplemseed.FDSNSourceId.createUnknown(100, response_lb=.01))
print(simplemseed.FDSNSourceId.createUnknown(1))
print(simplemseed.FDSNSourceId.createUnknown(0.01))

# calculate correct band code for a sample rate
print(simplemseed.bandCodeForRate(100, response_lb=.01))
# describe a band code
print(simplemseed.bandCodeDescribe("H"))
# describe a source code
print(simplemseed.sourceCodeDescribe("H"))
