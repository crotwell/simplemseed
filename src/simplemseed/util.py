

def isoWZ(time) -> str:
    """
    Convert to ISO8601.
    
    Convert a datetime object to an ISO8601 string, replacing the ending
    timezone with a Z if it is +00:00.
    """
    return time.isoformat().replace("+00:00", "Z")
