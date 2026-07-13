# etf-write · 项目能力索引

写之前扫一眼，优先复用现成能力。

## 数据源

### 日线 K 线（场内 ETF）

```python
from datetime import date
from vgrid.core.enums import Frame
from vgrid.data.loader import load_bars

bars = load_bars("510880", date(2017, 1, 1), date(2026, 7, 12), Frame.DAILY, adjust="qfq").bars
# adjust: "qfq"=前复权(含分红再投，算总收益用) / ""=不复权(算纯价格变动、股息率分母用)
# Bar 字段: ts / open / high / low / close / volume
```

- 源：腾讯日线（Frame.DAILY）。分钟线走 mootdx（不支持日线）。
- 场内 ETF（51xxxx 沪 / 15xxxx 深）有 K 线。**场外基金（519xxx 等）只有净值、没 K 线**，dca 引擎不适用，要走净值口径单独写。
- 前复权当前价 = 真实交易价，算股息率直接用 qfq 末日 close 作分母。

### 分红明细

```python
from vgrid.income.dividends import fetch_dividends

# ⚠️ 必须设 NO_PROXY，否则东财连接被 reset（10054）
# bash: NO_PROXY="eastmoney.com,push2his.eastmoney.com" python ...
divs = fetch_dividends("510880")  # list[DividendEvent]: register_date/ex_date/pay_date/per_share
```

### 净值（场外基金 / 校验）

```python
from vgrid.income.nav import fetch_navs
navs = fetch_navs("510880", start, end)  # list[NavPoint]: day/unit_nav/acc_nav
```

## 回测能力

### 定投 vs 全仓

```python
from decimal import Decimal
from vgrid.dca.config import DcaConfig, Frequency
from vgrid.dca.engine import run_dca

config = DcaConfig(
    symbol="510880", frequency=Frequency.MONTHLY,
    base_amount=Decimal("2000"), cash_cap=Decimal("50000"), day_of_month=15,
)
result = run_dca(config, bars)
# result.metrics 含: xirr / buy_hold_return(全仓对照) / max_drawdown / invested_amount / n_buys
```

### 红利四口径（价格 / 价+现分 / 价+再投 / 累计净值）

```python
from vgrid.income.report import build_etf_result
result = build_etf_result(code, name, bars, dividends, navs, expenses, initial_cash, lot_size, fee)
# 含 price_curve / cash_dividend_curve / reinvest_curve / acc_nav_curve + metrics
```

### 分红再投增强（任意策略 + 分红叠加）

```python
from vgrid.income.combo import dca_dividend_combo, grid_dividend_combo
```

### 常用计算（自己写小函数，参考前面几轮的实现）

- **年度收益**：按年聚合 close，年末 / 上年末 − 1。
- **滑动窗口胜率**：每个起点持有 N 年总收益（qfq），统计正收益比例 + 平均年化。
- **收益分解**：不复权价格变动 + 期间每股分红 ÷ 起点价 + 前复权总收益（含再投复利，故 > 前两者之和）。
- **TTM 股息率**：近 12 月每股分红 ÷ 当前价。

## 生图

统一用 `vgrid.charts._style` 样式系统，别自己配 matplotlib rcParams。

```python
import matplotlib.pyplot as plt
from vgrid.charts._style import THEME, title_block, kpi_strip, watermark, save_png, dec_pct

fig = plt.figure(figsize=(11, 5.8))
ax = fig.add_axes((0.07, 0.13, 0.90, 0.63))  # top ≤ 0.78，给标题/KPI 留位
# ... 画图 ...
title_block(fig, "标题", "副标题（小灰）")
kpi_strip(fig, [("标签", "值", THEME["strategy"]), ...])  # 4-6 项
watermark(fig)
save_png(fig, "images/xxx.png")  # 160 DPI，自动建目录
```

现成图函数（吃结果对象）：`render_backtest_chart` / `render_compare_chart` / `render_income_chart` / `render_enhance_chart` / `render_ladder_chart` / `render_scan_heatmap`。

新图（项目没有的）基于 _style 自己组装 axes，配色用 THEME；需要区分成长/进攻色可局部补 `GROWTH = "#E07B39"`（不污染 THEME）。

## 已知坑

1. **东财分红走代理会 ConnectionReset 10054**：`fetch_dividends` 前设 `NO_PROXY="eastmoney.com,push2his.eastmoney.com"`。价格数据（腾讯）不受影响。
2. **腾讯老数据（2016 年前）偶尔 502**：起点尽量用 2017+；非要老数据就重试或 `refresh=True`。
3. **前复权当前价 = 真实价**：算股息率用 qfq 末日 close 作分母，不用拉不复权。
4. **场外基金（519xxx）无 K 线**：`run_dca` 等 K 线引擎不适用，走净值口径单独写。
5. **临时脚本跑完即删**：`_xxx.py` 临时文件跑完 `rm`，不进 git。
6. **标的代码先核实**：519 段有断号（如 519307 查无此基），场外基金代码易记错，先拉数据确认存在再写。
