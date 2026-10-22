"""惯性系位置 -> 地固系 -> WGS84 大地经纬度。"""

import math

from .constants import FLATTENING, R_EARTH


def eci_to_ecef(r, theta):
    """绕 z 轴转过地球自转角 theta（弧度）。"""
    c, s = math.cos(theta), math.sin(theta)
    return [c * r[0] + s * r[1], -s * r[0] + c * r[1], r[2]]


def ecef_to_geodetic(x, y, z):
    """地固系坐标（km）转大地纬度、经度（度），经度在 [-180, 180)。"""
    lon = math.degrees(math.atan2(y, x))
    if lon >= 180.0:
        lon -= 360.0
    p = math.hypot(x, y)
    lat = math.atan2(z, p)
    for _ in range(10):
        s = math.sin(lat)
        n = R_EARTH / math.sqrt(1.0 - FLATTENING * s * s)
        lat = math.atan2(z + FLATTENING * n * s, p)
    return math.degrees(lat), lon
