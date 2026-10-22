"""二体轨道外推。"""

import math

from .constants import MU

STEP = 60.0  # 积分步长，s


def _accel(r):
    d = math.sqrt(r[0] * r[0] + r[1] * r[1] + r[2] * r[2])
    k = -MU / (d * d * d)
    return [k * r[0], k * r[1], k * r[2]]


def _advance(r, v, dt):
    """速度 Verlet 一步：辛格式，长期外推能量不漂移。"""
    a0 = _accel(r)
    vh = [v[i] + 0.5 * dt * a0[i] for i in range(3)]
    r1 = [r[i] + dt * vh[i] for i in range(3)]
    a1 = _accel(r1)
    v1 = [vh[i] + 0.5 * dt * a1[i] for i in range(3)]
    return r1, v1


def propagate(r0, v0, times):
    """从 t=0 的状态外推到 times（s，非负、升序）各时刻，返回位置列表。"""
    out = []
    t = 0.0
    r, v = list(r0), list(v0)
    for target in times:
        if target < t:
            raise ValueError("times must be ascending and non-negative")
        while target - t > 1e-9:
            dt = min(STEP, target - t)
            r, v = _advance(r, v, dt)
            t += dt
        out.append(list(r))
    return out
