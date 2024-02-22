import simplemseed3

chanSourceId = "FDSN:CO_JSC_00_H_H_Z"
chanNslc = "CO_JSC_00_HHZ"

sid = simplemseed3.FDSNSourceId.parse(chanSourceId)
print(sid)
sid2 = simplemseed3.FDSNSourceId.parseNslc(chanNslc, sep='_')
print(sid2)
sid3 = simplemseed3.FDSNSourceId.fromNslc("CO", "JSC", "00", "HHZ")
print(sid3)
print(sid == sid2)
print(sid == sid3)

print(sid.stationSourceId())
print(sid.stationSourceId() == sid2.stationSourceId())
print(sid.stationSourceId() == simplemseed3.FDSNSourceId.parse("FDSN:CO_JSC"))


print(sid.networkSourceId())
print(sid.networkSourceId() == sid2.networkSourceId())
print(sid.networkSourceId() == simplemseed3.FDSNSourceId.parse("FDSN:CO"))

print(simplemseed3.FDSNSourceId.createUnknown())
print(simplemseed3.FDSNSourceId.createUnknown(100))
print(simplemseed3.FDSNSourceId.createUnknown(1))
print(simplemseed3.FDSNSourceId.createUnknown(.01))
