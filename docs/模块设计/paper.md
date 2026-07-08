# 模块：paper（模拟盘）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：盘中实时轮询行情，喂给 M1 引擎（**同一份策略逻辑**），触线即虚拟成交；tick + 成交
落 SQLite，支持断点续跑。**模拟盘 = 实时版的回测**，策略代码一行不改。

**关键决策**：
1. **复用 `GridEngine`，一行不改**：实时 tick 喂 `engine.step`，触线即成交。和回测唯一区别是
   数据源（实时 vs 历史）和喂价方式（单一 tick vs OHLC）。
2. **replay 而非快照**：断点续跑时读 DB 历史 tick，replay 重建 engine 状态——engine 纯逻辑
   不加序列化，正确性靠「同样的 tick 序列产生同样的状态」。
3. **纯逻辑与 I/O 分离**：`process_tick`（纯：落库 + 喂 engine）、`run`（I/O 循环）、
   `realtime` provider（I/O）。单测用 `process_tick` 直接驱动，不碰网络。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `realtime.py` | `RealtimeProvider` 协议 + `MootdxRealtimeProvider`（通达信实时 ETF 盘） |
| `session.py` | `in_session`（A 股 9:30–11:30 / 13:00–15:00 工作日）、`next_session_open` |
| `runner.py` | `PaperRunner`：`replay` 重建、`process_tick` 单步、`run` 长驻循环、`snapshot` 状态 |

## ③ 实现细节

- **replay**：`load_ticks` → 若非空，`engine.start(ticks[0])` + 逐个 `step` 重建；空则等首个实时
  tick 在 `process_tick` 里 `start`。
- **process_tick(ts, price)**：`save_tick` → 首个 tick `engine.start`（CENTER 模式含建仓成交，ZERO
  零成交），之后 `engine.step` 产 fills → `save_fill`。是纯逻辑测试入口（不调 provider、不判 session）。
  若注入了 `Notifier`（切10a），fills 非空时把信号推出去（只通知不真下单），推送失败 `except OSError`
  打日志、不中断模拟盘。
- **run()**：`replay` 后长驻循环；盘中 `step_once`（fetch + `process_tick`）+ `sleep(interval)`，
  盘外 sleep 到下一开盘（至多 60s 重判，防时钟漂移）。
- **配置一致性**：`__init__` 校验 DB 已存配置与传入一致，不一致报错（防误用）。
- **实时接口**：走 `data.mootdx_quotes.MootdxQuotes.snapshot([symbol])` 取现价（通达信协议，
  稳定不限 IP）。原东财 `fund_etf_spot_em` 海外常年超时，已换掉（详见 [data 模块](./data.md)）。

## ④ 改动历史

- **2026-07-06（M4a 首次实现）**：realtime provider（akshare + 协议）、session（A 股时段）、
  runner（replay + process_tick + run + snapshot）。单测覆盖首次 start 零成交、tick 驱动买卖
  落库、replay 状态一致、配置不一致报错、时段判断（盘内 / 盘前 / 午休 / 盘后 / 周末）。
- **2026-07-08（实时源换 mootdx）**：东财 `fund_etf_spot_em` 海外常年超时，`AkshareRealtimeProvider`
  换成 `MootdxRealtimeProvider`（走 `data.mootdx_quotes` 通达信实时报价）。协议 `RealtimeProvider`
  不变，`PaperRunner` 一行不改。
- **2026-07-06（M4a 修复）**：`process_tick` 首个 tick 的 start 成交（CENTER 建仓）原被丢弃,
  改成落库；补 CENTER 建仓单测。
- **2026-07-07（切10a 推送）**：`PaperRunner.__init__` 加可选 `notifier: Notifier | None`；
  `process_tick` 出 fills 后推送（切10a 半自动实盘：只通知不真下单），推送失败降级不中断盘。
  详见 [notify 模块](./notify.md)。切10b 的光大 QMT 真实下单在此接口位置替换 Notifier。
