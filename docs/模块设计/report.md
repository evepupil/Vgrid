# 模块：report（绩效报告层）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：把 `BacktestResult` 渲染成人能读的报告——完整 Markdown（落盘）+ 终端精简摘要
（跑完即打印）。**纯展示层**，按项目规范不写单测；只读 `result` / `config`，无副作用、
不落盘（落盘由 CLI 负责）。

**关键决策**：
1. **渲染与落盘分离**：本层只产出文本字符串，写文件交给 CLI，方便复用。
2. **数值格式统一**：百分比 / 小数 / 金额走 `_format` 三个工具，全 `Decimal`，不在展示层
   引入 float。
3. **买入持有对照列在指标表**：一眼看出网格相对被动持有的超额。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `_format.py` | `pct` / `dec` / `cash`：百分比、定长小数、对齐到分 |
| `markdown.py` | `render_report(result, config)`：策略参数 + 指标 + 买入持有 + 手续费 + 成交明细 |
| `terminal.py` | `render_summary(result, config)`：几行核心指标，跑完即打印 |

## ③ 实现细节

- `render_report`：标准 Markdown 表格。指标表把「买入持有」列在旁边对照；成交明细默认列
  前 20 笔，超出标「共 N 笔」。
- `render_summary`：单屏 5 行——总收益 / 买入持有、年化 / 回撤、夏普 / 胜率、末权益 / 买卖
  笔数、手续费。中文标签 + 数字右对齐。
- `pct(ratio, digits)`：`(ratio×100).quantize(10^-digits) + "%"`；`dec` 同理；`cash` 复用
  `core.money.quantize_cash`。

## ④ 改动历史

- **2026-07-06（M2 首次实现）**：Markdown 报告（参数 / 指标 / 买入持有对照 / 手续费 /
  成交明细）+ 终端摘要 + 数值格式工具。展示层，按规范不写单测。
