# 卫星位置预报工具

地面站排天线跟踪计划时，用 `/app/orbit_predict.py` 根据卫星的轨道参数推算未来三天的位置。最近拿它和雷达实测对了一次，问题不少：预报几个小时后位置就偏出去几十公里，三天后差到上千公里；椭圆轨道的卫星，近地点高度和实测对不上；工具报出来的轨道周期，也比测轨组给的值长了零点几秒。

请修好这个工具，让它在下面的口径下给出可信的结果。

## 输入

`python3 /app/orbit_predict.py <输入文件>`，输入是 JSON：

```json
{
  "satellites": [
    {
      "id": "STATION-A",
      "perigee_alt_km": 413.0,
      "apogee_alt_km": 421.0,
      "inclination_deg": 51.64,
      "raan_deg": 247.46,
      "arg_perigee_deg": 130.54,
      "mean_anomaly_deg": 325.03,
      "times_s": [0, 5400, 86400]
    }
  ]
}
```

- `perigee_alt_km`、`apogee_alt_km`：近地点、远地点高度，单位 km，从半径 6378.137 km 的地球球面量起。
- `inclination_deg`、`raan_deg`、`arg_perigee_deg`、`mean_anomaly_deg`：轨道倾角、升交点赤经、近地点幅角、历元时刻的平近点角，单位度。
- `times_s`：要预报的时刻，相对历元的秒数，非负、升序，最长到 259200 s（3 天）。

样例在 `/app/samples/station.json`。

## 输出

标准输出打印一个 JSON，每颗卫星一条，顺序与输入一致：

```json
{
  "satellites": [
    {
      "id": "STATION-A",
      "semi_major_axis_km": 0.0,
      "eccentricity": 0.0,
      "period_s": 0.0,
      "positions_km": [[0.0, 0.0, 0.0]]
    }
  ]
}
```

- `semi_major_axis_km`、`eccentricity`、`period_s`：半长轴（km）、偏心率、轨道周期（s）。
- `positions_km`：与 `times_s` 一一对应的地心惯性系位置 `[x, y, z]`，单位 km。
- 数值按双精度原样输出，不要四舍五入。

## 口径与精度

- 只考虑地球中心引力（二体问题），不加摄动、大气阻力和地球自转。
- 地心引力常数按 IERS Conventions 2010 取值。
- 半长轴、偏心率按几何关系精确换算；周期的相对误差不超过 1×10⁻⁶。
- 3 天内每个时刻的位置误差不超过 1 km。
- 只用 Python 标准库，不访问网络；同一份输入重复运行，结果必须一致。
- 保留命令行入口和输入输出格式，其他代码可以随意改。
