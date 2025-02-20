

def isoWZ(time) -> str:
    return time.isoformat().replace("+00:00", "Z")
