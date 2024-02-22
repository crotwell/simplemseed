import simplemseed

chanSourceId = "FDSN:CO_JSC_00_H_H_Z"
chanNslc = "CO_JSC_00_HHZ"

sid = simplemseed.FDSNSourceId.parse(chanSourceId)
print(sid)
sid2 = simplemseed.FDSNSourceId.parseNslc(chanNslc, sep="_")
print(sid2)
sid3 = simplemseed.FDSNSourceId.fromNslc("CO", "JSC", "00", "HHZ")
print(sid3)
print(sid == sid2)
print(sid == sid3)

print(sid.stationSourceId())
print(sid.stationSourceId() == sid2.stationSourceId())
print(sid.stationSourceId() == simplemseed.FDSNSourceId.parse("FDSN:CO_JSC"))


print(sid.networkSourceId())
print(sid.networkSourceId() == sid2.networkSourceId())
print(sid.networkSourceId() == simplemseed.FDSNSourceId.parse("FDSN:CO"))

print(simplemseed.FDSNSourceId.createUnknown())
print(simplemseed.FDSNSourceId.createUnknown(100))
print(simplemseed.FDSNSourceId.createUnknown(100, response_lb=.01))
print(simplemseed.FDSNSourceId.createUnknown(1))
print(simplemseed.FDSNSourceId.createUnknown(0.01))

print(simplemseed.bandCodeForRate(100, response_lb=.01))
print(simplemseed.bandCodeDescribe("H"))
print(simplemseed.sourceCodeDescribe("H"))
