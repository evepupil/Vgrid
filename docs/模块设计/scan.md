# 模块：scan（参数扫描层）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：穷举策略旋钮组合，每组跑回测，按指标排序找最优。给 M4 模拟盘提供经过验证的参数，
而不是拍脑袋。复用 M2 全部基础设施（`simulate` / `GridConfig.from_dict` / 报告格式化），
只加扫描与排序。

**关键决策**：
1. **网格搜索（笛卡尔积）**：`itertools.product` 穷举 `vary` 字段的候选值，简单可复现、零额外
   依赖。组合数超 5000 抛错，防止误跑爆栈。
2. **复用 `GridConfig.from_dict` 做类型转换**：扫描规格用「字段名 → 值」dict 表达，`Decimal` /
   枚举转换全复用 `GridConfig`，不另写一套。
3. **单区间、样本内**：在用户给的区间上扫，报告标注「样本内最优，实盘未必」，不做 train/test
   切分（后续可加）。
4. **指标可换**：默认夏普，支持 `total_return` / `annualized_return` / `calmar`（年化 ÷ 回撤），
   都按「越大越好」降序。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `space.py` | `ScanSpec(fixed, vary)`：笛卡尔积 `expand` 成 `GridConfig`，组合数上限保护，`from_dict`/`to_dict` |
| `runner.py` | `ScanRow`、`run_scan`（复用 `simulate` 取 metrics）、`rank`（按 metric 降序）、`metric_value`（含 calmar） |
| `markdown.py` | `render_scan_report`：top-N 对比表 + 样本内提示（展示层，无单测） |

## ③ 实现细节

### space.ScanSpec
- `expand()`：`product(*vary.values())` 笛卡尔积，每个组合合并 `fixed` 成 dict，走
  `GridConfig.from_dict` 构造——`vary` 给 `grid_count:[4,6,8]` 或 `spacing_mode:["arithmetic"]`
  都直接展开，类型转换零重复。
- `size` = Π `len(vary[k])`；超过 `_MAX_COMBOS=5000` 抛错。
- `from_dict` / `to_dict`：扫描规格 JSON 往返。

### runner
- `run_scan(configs, bars)`：每个 config 调 `simulate` 取 `metrics`，包成 `ScanRow`。
- `metric_value`：`sharpe` / `total_return` / `annualized_return` 直接取；`calmar = 年化 / 最大回撤`，
  回撤 0（从未亏损）返回极大值排最前。
- `rank(rows, metric)`：按 `metric_value` 降序；metric 不合法抛错（空 rows 也校验）。

### markdown.render_scan_report
- top-N 表，列「扫描字段 + 关键指标」。表头标「⚠️ 样本内最优，实盘未必」。
- 枚举字段显示 `.value`（如 `arithmetic` 而非 `SpacingMode.ARITHMETIC`）。

## ④ 改动历史

- **2026-07-06（M3 首次实现）**：`ScanSpec`（笛卡尔积 + 上限保护）、`run_scan` / `rank` /
  `metric_value`（含 calmar）、扫描报告 Markdown。单测覆盖笛卡尔积展开 / 继承 / 往返 / 超限、
  排序 / calmar / 未知指标。
