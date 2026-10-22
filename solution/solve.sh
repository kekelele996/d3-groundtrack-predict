#!/usr/bin/env bash
set -euo pipefail

# 参考解：逐处修正卫星位置预报工具，再用样例跑一遍入口。
# 留一法实跑：HTB_SKIP=<难点 id> 时跳过该难点的修复，其余照做，
#   harbor run -p ./task -a oracle --ae HTB_SKIP=difficulty_1
# 正式 Oracle 不设这个变量。
SKIP="${HTB_SKIP:-}"
APP=/app
PY=/usr/local/bin/python3

# D1：偏心率是几何量 e = (ra - rp)/(ra + rp)，ra、rp 是到地心的距离；
# 直接拿离地高度相减相除，等于把地球半径丢掉，e 会被放大十几倍。
fix_difficulty_1() {
  "$PY" - <<'PY'
from pathlib import Path
p = Path("/app/orbit/elements.py")
s = p.read_text()
old = """    if apogee_alt + perigee_alt == 0:
        return a, 0.0
    e = (apogee_alt - perigee_alt) / (apogee_alt + perigee_alt)
"""
new = """    e = (ra - rp) / (ra + rp)
"""
assert old in s
p.write_text(s.replace(old, new))
PY
}

# D2：G 的相对不确定度约 2e-5（CODATA 2018），G*M 相乘的精度远不如直接测定的
# 地心引力常数 GM（IERS Conventions 2010 表 1.1：3.986004418e14 m^3/s^2，
# 相对不确定度 2e-9）。周期和平均运动都直接由 GM 决定，必须用标准值。
fix_difficulty_2() {
  "$PY" - <<'PY'
from pathlib import Path
p = Path("/app/orbit/constants.py")
s = p.read_text()
old = """# 地球引力常数，换算到 km^3/s^2（1 m^3 = 1e-9 km^3）
MU = G * M_EARTH / 1e9
"""
new = """# 地心引力常数 GM，IERS Conventions 2010 表 1.1：3.986004418e14 m^3/s^2，
# 换算到 km^3/s^2。不要用 G*M 相乘：G 本身只有约 2e-5 的相对精度。
MU = 398600.4418
"""
assert old in s
p.write_text(s.replace(old, new))
PY
}

# D3：二体问题有解析解。60 s 步长的速度 Verlet 虽然能量不漂，但相位误差
# 随时间累积，三天后位置差几百公里。改为按平均运动推进平近点角、解开普勒方程。
fix_difficulty_3() {
  "$PY" - <<'PY'
from pathlib import Path
p = Path("/app/orbit_predict.py")
s = p.read_text()
old = """    times = [float(t) for t in sat["times_s"]]
    positions = propagate(r0, v0, times)
"""
new = """    times = [float(t) for t in sat["times_s"]]
    angles = [math.radians(float(sat[k])) for k in ("inclination_deg", "raan_deg", "arg_perigee_deg")]
    m0 = math.radians(float(sat["mean_anomaly_deg"]))
    n = 2.0 * math.pi / orbital_period(a)
    positions = [state_vector(a, e, *angles, m0 + n * t)[0] for t in times]
"""
assert old in s
s = s.replace(old, new).replace("from orbit.propagate import propagate\n", "")
p.write_text(s)
PY
}

# D4：地球相对恒星转一圈是一个恒星日（约 86164.1 s），角速度约 7.2921e-5 rad/s；
# 7.2722e-5 是 2π/86400，即按太阳日算，三天少转约 3 度。直接用恒星时公式按时刻求地球朝向。
fix_difficulty_4() {
  "$PY" - <<'PY'
from pathlib import Path
p = Path("/app/orbit_predict.py")
s = p.read_text()
old = "x, y, z = eci_to_ecef(r, theta0 + EARTH_RATE * t)"
new = "x, y, z = eci_to_ecef(r, gmst(jd0 + t / 86400.0))"
assert old in s
s = s.replace(old, new)
s = s.replace('theta0 = gmst(julian_day(*parse_utc(sat["epoch_utc"])))', 'jd0 = julian_day(*parse_utc(sat["epoch_utc"]))')
s = s.replace("from orbit.constants import EARTH_RATE\n", "")
p.write_text(s)
PY
}

# D5：Meeus 的儒略日公式要求 1、2 月当作上一年的 13、14 月，否则这两个月的日期
# 会差 1 到 3 天，恒星时差 1 到 3 度。
fix_difficulty_5() {
  "$PY" - <<'PY'
from pathlib import Path
p = Path("/app/orbit/timescale.py")
s = p.read_text()
old = """    a = year // 100
"""
new = """    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
"""
assert old in s
p.write_text(s.replace(old, new, 1))
PY
}

# D6：大地纬度迭代 tanφ = (z + e²·N·sinφ)/p 里要用第一偏心率的平方 e² = f(2 - f)，
# 不是扁率 f；用 f 时中纬度低轨星下点纬度差约 0.1 度。
fix_difficulty_6() {
  "$PY" - <<'PY'
from pathlib import Path
p = Path("/app/orbit/geodesy.py")
s = p.read_text()
old1 = "    lat = math.atan2(z, p)\n"
new1 = "    e2 = FLATTENING * (2.0 - FLATTENING)\n    lat = math.atan2(z, p)\n"
old2 = "n = R_EARTH / math.sqrt(1.0 - FLATTENING * s * s)"
new2 = "n = R_EARTH / math.sqrt(1.0 - e2 * s * s)"
old3 = "lat = math.atan2(z + FLATTENING * n * s, p)"
new3 = "lat = math.atan2(z + e2 * n * s, p)"
for a, b in ((old1, new1), (old2, new2), (old3, new3)):
    assert a in s, a
    s = s.replace(a, b)
p.write_text(s)
PY
}

for d in difficulty_1 difficulty_2 difficulty_3 difficulty_4 difficulty_5 difficulty_6; do
  if [ "$SKIP" = "$d" ]; then
    echo "留一法：跳过 $d" >&2
    continue
  fi
  "fix_$d"
done

cd "$APP"
"$PY" orbit_predict.py samples/station.json > /dev/null
echo "solve done"
