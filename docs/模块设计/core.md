# 模块：core（领域模型层）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：定义整个系统的领域语言——订单、成交、持仓、手续费、网格配置。纯数据 +
纯计算，**不做任何 I/O**（不碰网络、文件、数据库）。上层（strategy / backtest /
执行层）都依赖它，它不依赖任何人。

**关键决策**：
1. **金额 / 价格一律用 `Decimal`**，杜绝浮点误差。份额是 `int`，且必须是一手
   （100 份）的整数倍。钱的事不能用 float 凑合。
2. **数据模型全部 frozen（不可变）**，在纯逻辑里安全传递，不怕被谁偷偷改。
3. **手续费按银河规则精确建模**：`max(0.1 元, 成交额 × 万0.5)`，单列成模型，
   方便回测统计费用、也方便以后换券商换费率。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `enums.py` | `Side`、`OrderKind`、`SpacingMode`、`BaseBuildMode`、`Frame`（K 线周期：日线/分钟线） |
| `bar.py` | `Bar`（一根 K 线）、`BarSeries`（一串 K 线，含时间单调递增与 OHLC 合法性校验） |
| `money.py` | `Decimal` 量化工具：价格对齐 tick、金额对齐分、预算算整手份额 |
| `fees.py` | `FeeModel` 手续费模型 |
| `models.py` | `OrderIntent`（订单意图）、`Fill`（成交）、`Lot`（持仓单元）、`Position`（持仓快照） |
| `config.py` | `GridConfig` 网格策略全部参数 + 校验 + 序列化（`to_dict`/`from_dict`） |

## ③ 实现细节

### 手续费（fees.py）
- `compute(notional)`：`佣金 = 成交额 × rate`，对齐到分（四舍五入），再和 `min_fee`
  取大。默认 `rate=0.00005`（万0.5）、`min_fee=0.1`。
- `min_efficient_notional = min_fee / rate = 2000`：单笔成交额低于它，实际费率就被
  保底费拉高。所以每格金额建议 ≥ 2000。

### 份额计算（money.py）
- `shares_for_amount(amount, price)`：`floor(amount/price)` 再向下取整到 `lot_size`
  的整数倍。买不满一手返回 0。
- `LOT_SIZE=100`、`PRICE_TICK=0.001`、`CENT=0.01`。

### 数据模型（models.py）
- `OrderIntent`：引擎产出的「想下的单」，含 `side / price / shares / level_index /
  kind`。引擎只决策，怎么下由执行层实现——解耦的关键。
- `Fill`：一笔成交，含 `fee` 和 `cash_delta`（对现金的净影响：买为负、卖为正，已含费）。
- `Lot`：一个持仓单元——在某条网格线买入、等着在上一格卖出的一份货。`cost` = 成交额
  + 买入手续费。
- `Position`：持仓快照（总份额 + 总成本），供报告用。

### 配置（config.py）
- `GridConfig` 集中所有策略旋钮（含追踪 / 放大 / 重建等参数），是 M3 参数扫描要调的
  对象。`__post_init__` 做完整合法性校验，非法直接抛 `ValueError`。
- `is_amount_fee_efficient`：每格金额是否达到费率临界（≥2000）。
- `to_dict` / `from_dict`：可 JSON 化的序列化往返。`Decimal` 一律转 `str` 保精度，`fee`
  展开成 `{rate, min_fee}`。`from_dict` 必填字段必须给、可选字段缺省走默认值，供 CLI
  的 `--config cfg.json` 用。

### K 线（bar.py）
- `Bar`：一根 K 线（`ts/open/high/low/close/volume`，全 `Decimal`）。`__post_init__` 校验
  四价为正、`high` 不低于 O/C/L、`low` 不高于 O/C/H（一字板 `high==low` 合法）。
- `BarSeries`：一标的某周期下从早到晚排好的 K 线串，校验时间严格递增。空序列合法
  （数据还没下），有数据就必须有序；支持 `len/iter/[]`，回测器直接迭代。
- 行情是领域原语，和 Order/Fill 同级；外部数据源（akshare 的 DataFrame）转 `Bar` 的
  工作交给 `data` 层，core 不绑定数据源格式。

## ④ 改动历史

- **2026-07-06（M1 首次实现）**：建立全部领域模型、手续费模型、配置与校验、金额工具。
  配套单测覆盖手续费临界、份额取整、配置校验。
- **2026-07-06（M2 配套）**：新增统一 K 线模型 `Bar`/`BarSeries`（OHLC + 时间校验），
  供回测与行情层共用；`GridConfig` 加 `to_dict`/`from_dict` 序列化供 CLI 配置文件；
  `enums.py` 加 `Frame`（日线/分钟线）。
