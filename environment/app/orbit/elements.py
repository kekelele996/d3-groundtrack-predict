"""轨道根数换算：高度 -> 半长轴/偏心率，根数 -> 惯性系位置速度。"""

import math

from .constants import MU, R_EARTH


def shape_from_altitudes(perigee_alt, apogee_alt):
    """近地点、远地点高度（km）换算成半长轴（km）和偏心率。"""
    if apogee_alt < perigee_alt:
        raise ValueError("apogee altitude below perigee altitude")
    rp = R_EARTH + perigee_alt
    ra = R_EARTH + apogee_alt
    a = (rp + ra) / 2.0
    if apogee_alt + perigee_alt == 0:
        return a, 0.0
    e = (apogee_alt - perigee_alt) / (apogee_alt + perigee_alt)
    return a, e


def orbital_period(a):
    """开普勒第三定律，a 为 km，返回秒。"""
    return 2.0 * math.pi * math.sqrt(a ** 3 / MU)


def solve_kepler(M, e, tol=1e-14, max_iter=60):
    """解开普勒方程 M = E - e sin E，牛顿迭代。"""
    M = math.fmod(M, 2.0 * math.pi)
    E = M if e < 0.8 else math.pi
    for _ in range(max_iter):
        d = (E - e * math.sin(E) - M) / (1.0 - e * math.cos(E))
        E -= d
        if abs(d) < tol:
            break
    return E


def state_vector(a, e, inc, raan, argp, mean_anom):
    """经典根数（角度为弧度）转地心惯性系位置（km）与速度（km/s）。"""
    E = solve_kepler(mean_anom, e)
    cE, sE = math.cos(E), math.sin(E)
    b = math.sqrt(1.0 - e * e)
    n = math.sqrt(MU / a ** 3)
    denom = 1.0 - e * cE
    # 近焦点坐标系
    xp, yp = a * (cE - e), a * b * sE
    vxp, vyp = -a * n * sE / denom, a * n * b * cE / denom

    cO, sO = math.cos(raan), math.sin(raan)
    ci, si = math.cos(inc), math.sin(inc)
    cw, sw = math.cos(argp), math.sin(argp)
    rot = (
        (cO * cw - sO * sw * ci, -cO * sw - sO * cw * ci),
        (sO * cw + cO * sw * ci, -sO * sw + cO * cw * ci),
        (sw * si, cw * si),
    )
    r = [row[0] * xp + row[1] * yp for row in rot]
    v = [row[0] * vxp + row[1] * vyp for row in rot]
    return r, v
