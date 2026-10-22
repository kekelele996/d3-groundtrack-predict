# d3-groundtrack-predict

D.3 物理模拟：修正卫星位置与星下点预报工具中的轨道要素换算、地心引力常数、轨道外推、地球自转角、儒略日和大地纬度计算。

- 入口：`environment/app/orbit_predict.py`
- 评分：`tests/test.sh` 以隐藏随机输入调用入口，按 `tests/weights.json` 加权
- 参考解：`solution/solve.sh`，说明见 `solution/NOTES.md`

task.toml 资源取规范推荐值（cpus 1、memory 2048 MB、agent 3600 s、verifier 300 s、build 900 s）。
