# 模块：charts（分享图层）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：把已算好的回测结果对象画成一张张「白底专业风」PNG，给知乎 / 研报式分享用。
纯消费现有结果（`BacktestResult` / `LadderView` / `StrategyComparison` / `EtfIncomeResult` /
`ComboResult` / 扫描 `ScanRow`），**不碰回测逻辑、不重算任何数**。图函数只负责排版和上色，
落盘交给 `save_png`。

**关键决策**：
1. **静态 PNG，不做交互**：知乎贴图要的是一张能直接传的图，不是网页。用 matplotlib 出
   160 DPI（retina）白底 PNG，`bbox_inches="tight"` 去白边。
2. **一套样式，六张图共用**：配色 / 中文字体 / 「标题 + 副标题 + KPI 行 + 水印」骨架全收在
   `_style.py`，各图函数只组装自己的 axes。改一次配色六张图一起变。
3. **matplotlib 懒导入**：只有真出图（`--chart`）才 `import matplotlib`。不出图的命令
   （如纯 `backtest`）一行都不碰它，启动不变慢。CLI 侧的 `_save_chart` 也在函数内才导。
4. **图函数返回 `Figure`，落盘分离**：渲染函数只返回 `matplotlib.figure.Figure`，是否存、
   存哪、DPI 多少由调用方 `save_png` 决定。方便测试（Agg 后端跑渲染、断言 PNG 非空）。
5. **展示层不测审美**：按项目规范，配色 / 布局 / 字体这些肉眼可见的东西不写单测；冒烟测
   只保证「合成数据能跑通渲染、产出非空 PNG」和二维校验这类硬逻辑。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `_style.py` | 样式系统：`THEME` 色板、`apply_theme`（rcParams，import 即生效）、`title_block`/`kpi_strip`/`watermark` 骨架、`save_png`、格式化器（`dec_pct`/`dec_cash`/`dec_price`）、日期轴 `date_axis` + `xdates`、自适应百分比轴 `pct_formatter` |
| `backtest_chart.py` | 图A `render_backtest_chart`：净值 + 买入持有 + 买卖点散点 + 回撤填充 |
| `ladder_chart.py` | 图B `render_ladder_chart`：网格档位横线（卖绿/买红/排队灰虚/空闲浅灰）+ 现价线 + 资金上限 + 基准窗口带 |
| `compare_chart.py` | 图C `render_compare_chart`：N 条策略净值叠加 + 端点标注 |
| `income_chart.py` | 图D `render_income_chart`：红利四口径曲线（价/价+现分/价+再投/累计净值） |
| `enhance_chart.py` | 图E `render_enhance_chart`：策略 vs 分红再投增强，中间绿色填充 = 分红贡献 |
| `scan_chart.py` | 图F `render_scan_heatmap`：二维参数扫描热力图（imshow YlGnBu，最优点红星） |

## ③ 实现细节

### _style（样式系统，六张共用）
- `THEME`：白底色板。策略主色深蓝 `#1f6feb`，买入持有灰，涨 / 买绿，跌 / 卖红，分红再投青，
  累计净值灰。
- `apply_theme()`：设全局 rcParams——中文字体（微软雅黑 → SimHei → Noto，`axes.unicode_minus=False`
  防负号变方块）、白底、去顶 / 右边框、浅网格。import 时自动跑一次，幂等。
- 顶部三行固定 y（图坐标）：标题 `0.955` → 副标题 `0.910` → KPI 标签 `0.858` / 值 `0.828`。
  各图 axes 的 top 要压到 `0.78` 以下，给 KPI 和图之间留白（早期这几行 y 挨太近，标题压 KPI，
  调开后修好）。
- `title_block` / `kpi_strip` / `watermark`：用 `fig.text` 画（不用 `suptitle`，好控位置）。
  KPI 是 `[(标签, 值, 颜色)]` 等间距横排，灰小字标签在上、彩色大字值在下，研报样。
- `save_png`：建目录 → `savefig(dpi=160, bbox_inches="tight", facecolor=白)` → `plt.close`（防 fig 泄漏）。
- 格式化器：`dec_pct`→`+12.34%`、`dec_cash`→`¥12,345`、`dec_price`→`¥1.053`。`dec_price` 必须
  round 到 3 位——原始价是 `Decimal`，不格式化会印出 `¥1.0531437807540776` 一长串。
- 日期轴 `date_axis`：`AutoDateLocator` + `ConciseDateFormatter`，按跨度自动选粒度、去重相邻标签
  （早期 `%Y-%m` 硬格式会出一堆重复月份）。`xdates` 把 `datetime` 序列转 `np.ndarray(dtype=object)`，
  绕开 matplotlib stub 对 `list[datetime]` 的类型报错。
- `pct_formatter(values)`：按 y 值跨度选小数位——跨度 < 8% 用 1 位，否则 0 位。防相邻刻度取整后
  重复（如 0.5% 被 `.0f` 抹成 0%）。

### 各图函数
- 都遵一套：吃结果对象 → 建 `fig` → 组装 axes（画线 / 散点 / 填充）→ `title_block` + `kpi_strip`
  + `watermark` → 返回 `Figure`。空数据抛 `ValueError`。
- **图A**：GridSpec 两行（净值 3 : 回撤 1）。上格策略净值 + 买入持有两线 + 买（绿 ^）卖（红 v）
  散点；下格回撤填充。y 轴用 `pct_formatter`。
- **图B**：档位画成横线，`dec_price` 印所有价。现价黑粗线，标签抬到线上方一点（`+ 价格跨度*0.018`）
  别压线上。基准窗口浅蓝带，放大区（窗口下沿以下）更浅带。右下图例按实际出现的档位类型给。
- **图C**：N 条净值叠加，`_color_for` 按策略名映射颜色，端点标注收益率。
- **图D**：四口径曲线，全在起点归零。`_xy` 把 `SeriesPoint.day` 转 `datetime` 再 `xdates`。
- **图E**：策略（灰虚线）vs 增强（蓝实线），两线之间增强 ≥ 策略处填亮绿——绿色面积就是分红的
  累积贡献。
- **图F**：`render_scan_heatmap` 要求扫描规格恰好 2 个 `vary` 维度（`_N_DIMS=2`，否则抛错），
  imshow YlGnBu 热力，最优点打红星。

### CLI 接线（`cli/app.py`）
- `_save_chart(render, out_dir, name)`：跑渲染 thunk、`save_png` 落 `out_dir/name.png`、打印路径。
  matplotlib 在这里才懒导入。
- 各命令加 `--chart` 开关（`backtest` / `compare` / `income compare` / `income enhance` / `scan`），
  图落到 `--out`（默认 `reports/`）。`income compare` 另有 `--chart-top`（默认前 3 只各出一张）。
- `scan --chart` 只在 `vary` 恰好 2 维时出图（`_SCAN_CHART_DIMS=2`），别的维度数打一行提示跳过，
  不报错。

## ④ 改动历史

- **2026-07-13（分享图层首次实现）**：新建 `charts` 模块——`_style` 样式系统 + 六张图函数
  （回测主图 / 网格阶梯 / 三方对比 / 红利四口径 / 红利增强 / 扫描热力图）。加 `matplotlib>=3.8`
  依赖。CLI 五个命令接 `--chart` 开关（含 `scan` 的二维守卫、`income compare` 的 `--chart-top`）。
  视觉自查修掉四个渲染 bug：顶部标题 / KPI 重叠、日期轴标签重复、百分比刻度取整重复、原始
  `Decimal` 价格未格式化。冒烟测覆盖六张图渲染产非空 PNG + `_save_chart` 落盘胶水 + 扫描非二维
  抛错。
