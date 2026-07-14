# 模块：batch（多标的批量回测）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：同一份定投配置，跑一串 ETF，逐只出「定投 vs 同期一次性买入」，横向排名。给「我把
N 只红利 ETF 用同一套定投跑一遍，谁最赚」这类横向比较提供一条命令的产出（终端表 + Markdown
+ 排名图）。纯消费现有回测引擎（`dca.run_dca`），不重写回测逻辑。

**关键决策**：
1. **v1 只做定投 + 一次性买入，不做网格批量**：定投配置（月投多少 / 频率 / 上限）对每只 ETF
   一视同仁，同一份配置跑 N 只完全公平；网格配置带**绝对价格**（上下沿），跨标的套不过去，要
   批量跑得先定「按每只自己区间自动定上下沿」的规则（还牵扯偷看未来），是独立设计题，留后续。
2. **一次 `run_dca` 双份产出**：`run_dca` 的 metrics 里同时有定投指标（XIRR / 收益 / 回撤）和
   同期一次性买入对照（`buy_hold_return`），一只跑一次就出「定投 vs 一次性」两条结果。
3. **纯函数 + 编排分离**：`backtest_one`（吃 BarSeries，无 I/O，单测重点）算单只；`run_batch`
   负责逐只拉行情、调 `backtest_one`、收集排序。某只无数据 / 回测失败标记跳过，不中断整批。
4. **前复权口径**：批量用 `adjust="qfq"`（分红按再投折进价），收益口径与单标的一致。
5. **区间不一致要露出来**：上市晚的标的实际区间短（笔数少），XIRR 跨区间硬比会误导——报表把
   「笔数」列出来、note 点破，不藏这个坑。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `models.py` | `BatchRow`（单只结果，含 `ok`/`reason` 跳过标记）、`BatchResult`（全体 + 区间 + 排序键，`ok_rows`/`failed_rows` 分组）、`SORT_CHOICES`（CLI 合法排序键） |
| `runner.py` | `backtest_one`（纯函数）、`run_batch`（编排 + 排序 + 跳过）、`_sort_rows`（回撤升序、其余降序、无值排最后） |
| `report/batch.py` | `render_batch_summary`（终端）、`render_batch_report`（Markdown 排名表 + 口径 note）。展示层，无单测 |
| `charts/batch_chart.py` | `render_batch_chart`：横向分组条（定投 XIRR vs 一次性买入），按排名从上到下 |

## ③ 实现细节

### runner
- `backtest_one(series, config, *, name)`：空行情 → `BatchRow.failed`；否则 `dataclasses.replace`
  把配置的 symbol 换成这只再 `run_dca`，从 metrics 摘 XIRR / 收益率 / 回撤 / 投入 / 笔数 /
  跳过数 / 手续费 / 一次性买入收益率，装成 `BatchRow`。
- `run_batch(codes, config, ...)`：逐只走 `loader`（默认 `load_bars(qfq)`，测试可注入假实现），
  `(ValueError, KeyError, OSError)` 兜底成跳过行。收完 `_sort_rows` 排序。
- 排序：`max_drawdown` 升序（小的好，无值用哨兵排最后）；`xirr`/两个收益率降序（无值排最后）。
- `on_progress` 回调逐只报进度。

### report / chart
- 报表：定投口径 + 一次性买入并排。note 明确两者口径不同别硬比、区间不一致看笔数、样本内历史。
- 图：每只一行两条（青=定投 XIRR，灰=一次性买入），末端标百分比；KPI 行给上榜数 + 榜首。
  只画有指标的行（跳过的不画）。

### 名称清洗（顺带修的数据源坑）
- mootdx 部分标的名带尾部 `\x00`（空字节），matplotlib 渲染成「缺字方块」（Glyph 0 警告）。
- 在 `data/mootdx_quotes.py` 的 `names()` 源头加 `_clean_name`（滤掉控制字符再 strip），所有
  消费方（batch / income / watchlist）一起受益。

## ④ 改动历史

- **2026-07-14（多标的批量回测首次实现）**：新建 `batch` 模块（models + runner）、`report/batch.py`、
  `charts/batch_chart.py`（图 G 排名条形图）、`vgrid batch` CLI 子命令（`--symbols`/`--config`/
  `--sort`/`--chart`）。顺带修 `mootdx_quotes.names()` 的 `\x00` 脏名（`_clean_name`）。单测覆盖
  `backtest_one`（正常 + 空行情跳过）、`run_batch`（注入 loader 的排序 + 跳过 + 回撤升序）、
  名称清洗、批量图冒烟。端到端在 510880/515180/515080/563020 上跑通。
