"""时间换算：UTC 字符串 -> 儒略日 -> 格林尼治平恒星时。UT1 按 UTC 处理。"""

import math
import re

J2000 = 2451545.0  # 2000-01-01 12:00 的儒略日

_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$")


def parse_utc(text):
    m = _ISO.match(text)
    if not m:
        raise ValueError(f"bad UTC timestamp: {text!r}")
    return tuple(int(g) for g in m.groups())


def julian_day(year, month, day, hour=0, minute=0, second=0):
    """格里历日期转儒略日（Meeus, Astronomical Algorithms 第 7 章）。"""
    a = year // 100
    b = 2 - a + a // 4
    jd0 = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5
    return jd0 + (hour + minute / 60.0 + second / 3600.0) / 24.0


def gmst(jd):
    """格林尼治平恒星时，弧度，[0, 2π)。IAU 1982 模型的 Meeus 形式。"""
    d = jd - J2000
    t = d / 36525.0
    deg = 280.46061837 + 360.98564736629 * d + 0.000387933 * t * t - t ** 3 / 38710000.0
    return math.radians(deg % 360.0)
