#!/usr/bin/env python3
"""逐项检查卫星位置预报工具的输出。

每个检查对应一个可以独立失败的难点，id 必须与 weights.json 一致。
期望值来自 research/claims.json 的独立复核，不要用 solution/ 生成。

本脚本以 root 运行；被测程序一律通过 run_candidate() 以 runner 身份、
干净环境变量、独立进程组运行，超时整组结束。
"""

import json
import math
import os
import secrets
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I 模式下不自动加入脚本目录

from score import record  # noqa: E402

APP = Path("/app")
PYTHON = "/usr/local/bin/python3"
CANDIDATE_USER = os.environ.get("HARBOR_CANDIDATE_USER", "runner")
CANDIDATE_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": f"/home/{CANDIDATE_USER}",
    "LANG": "C.UTF-8",
    "TZ": "UTC",
}
CALL_TIMEOUT_SEC = 120
ENTRY = APP / "orbit_predict.py"


def case_dir():
    """隐藏输入放在随机命名的临时目录，名字不带用例语义；候选只读。"""
    path = Path(tempfile.mkdtemp(prefix="in-"))
    path.chmod(0o755)
    return path


def run_candidate(args, timeout=CALL_TIMEOUT_SEC):
    """以低权限运行候选入口，返回 CompletedProcess；超时结束整个进程组。"""
    as_root = os.getuid() == 0
    proc = subprocess.Popen(
        [PYTHON, *[str(a) for a in args]],
        cwd=str(APP),
        env=CANDIDATE_ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        user=CANDIDATE_USER if as_root else None,
        group=CANDIDATE_USER if as_root else None,
        extra_groups=[] if as_root else None,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        out, err = proc.communicate()
        raise RuntimeError(f"timeout after {timeout}s")
    return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)


def run_predict(sats):
    """把隐藏输入写进随机目录，调用候选入口，按 id 取回结果。"""
    tmp = case_dir()
    case = tmp / f"{secrets.token_hex(4)}.json"
    case.write_text(json.dumps({"satellites": sats}), encoding="utf-8")
    case.chmod(0o644)
    proc = run_candidate([ENTRY, case])
    if proc.returncode != 0:
        raise RuntimeError(f"exit={proc.returncode}, stderr={proc.stderr[-800:]}")
    rows = json.loads(proc.stdout)["satellites"]
    got = {str(r["id"]): r for r in rows}
    missing = [s["id"] for s in sats if s["id"] not in got]
    if missing:
        raise RuntimeError(f"missing ids {missing}")
    return got


# ---- 独立参考实现：二体解析解（不调用 /app 的任何代码）----
# 常数见 research/claims.json：GM 取 IERS Conventions 2010 表 1.1，
# 赤道半径取题面给定的 6378.137 km。
GM = 398600.4418
RE = 6378.137


def ref_shape(hp, ha):
    rp, ra = RE + hp, RE + ha
    return (rp + ra) / 2.0, (ra - rp) / (ra + rp)


def ref_period(a, mu=GM):
    return 2.0 * math.pi * math.sqrt(a ** 3 / mu)


def ref_position(a, e, inc, raan, argp, m0, t, mu=GM):
    n = math.sqrt(mu / a ** 3)
    M = math.fmod(m0 + n * t, 2.0 * math.pi)
    E = M + e * math.sin(M)
    for _ in range(100):
        f = E - e * math.sin(E) - M
        E -= f / (1.0 - e * math.cos(E))
        if abs(f) < 1e-15:
            break
    nu = 2.0 * math.atan2(math.sqrt(1 + e) * math.sin(E / 2), math.sqrt(1 - e) * math.cos(E / 2))
    r = a * (1 - e * math.cos(E))
    u = argp + nu
    cO, sO, ci, si = math.cos(raan), math.sin(raan), math.cos(inc), math.sin(inc)
    cu, su = math.cos(u), math.sin(u)
    return (
        r * (cO * cu - sO * su * ci),
        r * (sO * cu + cO * su * ci),
        r * (su * si),
    )


RNG = secrets.SystemRandom()


def rand_sat(hp_range, dh_range, times=None):
    hp = RNG.uniform(*hp_range)
    sat = {
        "id": "S" + secrets.token_hex(3),
        "perigee_alt_km": round(hp, 3),
        "apogee_alt_km": round(hp + RNG.uniform(*dh_range), 3),
        "inclination_deg": round(RNG.uniform(5, 110), 4),
        "raan_deg": round(RNG.uniform(0, 360), 4),
        "arg_perigee_deg": round(RNG.uniform(0, 360), 4),
        "mean_anomaly_deg": round(RNG.uniform(0, 360), 4),
        "times_s": times if times is not None else [0],
    }
    return sat


def check_difficulty_1():
    """近地点、远地点高度换算成半长轴和偏心率（地心距口径）。"""
    sats = [
        rand_sat((300, 600), (2, 40)),
        rand_sat((500, 900), (300, 3000)),
        rand_sat((400, 1200), (15000, 30000)),
    ]
    got = run_predict(sats)
    bad = []
    for s in sats:
        a_ref, e_ref = ref_shape(s["perigee_alt_km"], s["apogee_alt_km"])
        g = got[s["id"]]
        a, e = float(g["semi_major_axis_km"]), float(g["eccentricity"])
        # 容差：独立积分路径与解析值差 e<3e-10、a<3e-6 km；高度口径错时 e 偏差 >1e-3
        if abs(a - a_ref) > 1e-3 or abs(e - e_ref) > 1e-7:
            bad.append(f"{s['id']}: a={a} ref={a_ref} e={e} ref={e_ref}")
    return not bad, "; ".join(bad) or "ok"


def check_difficulty_2():
    """周期与地球引力常数取值。"""
    sats = [
        rand_sat((300, 700), (0, 30)),
        rand_sat((700, 1500), (0, 500)),
        rand_sat((800, 2000), (5000, 20000)),
    ]
    got = run_predict(sats)
    bad = []
    for s in sats:
        a_ref, _ = ref_shape(s["perigee_alt_km"], s["apogee_alt_km"])
        t_ref = ref_period(a_ref)
        t = float(got[s["id"]]["period_s"])
        # 相对容差 1e-6：GM 取 GRS80/DE 系列差 <1e-7；用 G*M 相乘偏差 >2.6e-6
        if abs(t - t_ref) / t_ref > 1e-6:
            bad.append(f"{s['id']}: T={t} ref={t_ref} rel={(t - t_ref) / t_ref:.3e}")
    return not bad, "; ".join(bad) or "ok"


def check_difficulty_3():
    """三天内的位置外推精度。

    参考位置按候选自报的半长轴、偏心率和周期反推的引力常数解析计算，
    所以这一项只看外推本身，不受高度换算和常数取值影响。
    """
    horizon = 3 * 86400.0
    sats = []
    for hp_r, dh_r in (((300, 600), (0, 40)), ((300, 800), (2000, 9000))):
        times = sorted(round(RNG.uniform(0, horizon), 3) for _ in range(6))
        sats.append(rand_sat(hp_r, dh_r, [0.0] + times + [horizon]))
    got = run_predict(sats)
    bad = []
    worst = 0.0
    for s in sats:
        g = got[s["id"]]
        a, e, T = float(g["semi_major_axis_km"]), float(g["eccentricity"]), float(g["period_s"])
        if not (a > RE and 0 <= e < 1 and T > 0):
            bad.append(f"{s['id']}: bad elements a={a} e={e} T={T}")
            continue
        mu = 4.0 * math.pi ** 2 * a ** 3 / T ** 2
        pos = g["positions_km"]
        if len(pos) != len(s["times_s"]):
            bad.append(f"{s['id']}: {len(pos)} positions for {len(s['times_s'])} times")
            continue
        ang = [math.radians(s[k]) for k in ("inclination_deg", "raan_deg", "arg_perigee_deg", "mean_anomaly_deg")]
        for t, p in zip(s["times_s"], pos):
            ref = ref_position(a, e, *ang, t, mu=mu)
            d = math.dist([float(x) for x in p], ref)
            worst = max(worst, d)
            # 容差 1 km：解析解误差 <1e-6 km；60 s 步长的二阶格式三天偏差数百 km
            if d > 1.0:
                bad.append(f"{s['id']} t={t}: err={d:.3f} km")
                break
    return not bad, ("; ".join(bad) or "ok") + f"; worst={worst:.6f} km"


CHECKS = [
    ("difficulty_1", check_difficulty_1),
    ("difficulty_2", check_difficulty_2),
    ("difficulty_3", check_difficulty_3),
]


def main():
    for check_id, fn in CHECKS:
        try:
            ok, detail = fn()
        except Exception as exc:  # 单项异常记为失败，不中断后面的检查
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        record(check_id, ok, detail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
