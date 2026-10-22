"""卫星位置与星下点预报：读入轨道参数文件，标准输出打印 JSON 预报结果。

用法：python3 /app/orbit_predict.py <输入文件>
"""

import json
import math
import sys

from orbit.constants import EARTH_RATE
from orbit.elements import orbital_period, shape_from_altitudes, state_vector
from orbit.geodesy import ecef_to_geodetic, eci_to_ecef
from orbit.propagate import propagate
from orbit.timescale import gmst, julian_day, parse_utc


def predict(sat):
    a, e = shape_from_altitudes(float(sat["perigee_alt_km"]), float(sat["apogee_alt_km"]))
    r0, v0 = state_vector(
        a,
        e,
        math.radians(float(sat["inclination_deg"])),
        math.radians(float(sat["raan_deg"])),
        math.radians(float(sat["arg_perigee_deg"])),
        math.radians(float(sat["mean_anomaly_deg"])),
    )
    times = [float(t) for t in sat["times_s"]]
    positions = propagate(r0, v0, times)

    theta0 = gmst(julian_day(*parse_utc(sat["epoch_utc"])))
    track = []
    for t, r in zip(times, positions):
        x, y, z = eci_to_ecef(r, theta0 + EARTH_RATE * t)
        lat, lon = ecef_to_geodetic(x, y, z)
        track.append([lat, lon])

    return {
        "id": sat["id"],
        "semi_major_axis_km": a,
        "eccentricity": e,
        "period_s": orbital_period(a),
        "positions_km": positions,
        "ground_track_deg": track,
    }


def main(argv):
    if len(argv) != 2:
        print("usage: python3 orbit_predict.py <input.json>", file=sys.stderr)
        return 2
    with open(argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)
    result = {"satellites": [predict(s) for s in data["satellites"]]}
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
