from datetime import datetime, timezone
from zoneinfo import ZoneInfo

EST = ZoneInfo('America/Panama')

def utcnow():
    return datetime.now(timezone.utc)

def estnow():
    return datetime.now(tz=EST)

def clamp[T: int | float](value: T, lower: T, upper: T) -> T:
    return min(max(value, lower), upper)