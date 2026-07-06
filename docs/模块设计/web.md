# 模块：web（看盘面板）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：本地 FastAPI 看盘面板。读 SQLite（paper 落盘的 tick / fill / config）→ replay engine 算
出持仓 / 盈亏 / 净值曲线 / 回撤 / 夏普 → 原生 HTML 前端每 5 秒轮询展示，净值曲线上标成交点。
**后端只读**，不维护长驻 engine（那是 `paper run` 的事）。

**关键决策**：
1. **每次请求 replay**：不缓存 engine 状态。读全部 tick → replay `GridEngine` → 算状态。tick 量小
   （纯逻辑秒级），WAL 模式下 `paper run` 写、`serve` 读并发不互锁。
2. **复用 backtest 指标**：回撤 / 夏普直接调 `metrics.max_drawdown_of` / `sharpe_of`（为此把这两个
   函数从 metrics 提为 public），`EquityPoint` 也复用，不重写统计。
3. **曲线降采样**：tick 可能几万个，前端 SVG 渲染 + JSON 传输扛不住，等距采样到 300 点；成交点
   按原 tick 索引映射到最近的采样点（bisect）。
4. **零前端依赖**：单 HTML（内嵌 CSS/JS），fetch 轮询，SVG 原生画。不引 React / Vue / 图表库。
5. **夏普按日折算近似**：tick 曲线的夏普年化因子不精确（tick 频率可变），按日线折算，看盘参考用。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `state.py` | `load_state` 纯逻辑：replay engine + 算 snapshot / 曲线 / 指标 / 成交点；降采样 |
| `server.py` | `create_app`：GET `/api/state`（JSON）、GET `/`（HTML）；Decimal / datetime → JSON 友好 |
| `templates/index.html` | 指标卡片 + SVG 净值曲线（成交点标注）+ 成交表格，5 秒轮询 |

## ③ 实现细节

- **load_state**：replay `GridEngine` 逐 tick 算 `EquityPoint`（权益 = `capital_cap + cash_flow +
  持仓×当前价`）；snapshot 取 engine 末态；metrics 用 `max_drawdown_of` / `sharpe_of` + 自算
  `total_return` / `buy_hold`；曲线 `_downsample` 等距采样；fills 按 tick 索引 → `FillMark`
  （`_map_to_sampled` 用 bisect 找不超过的最大采样点位置）。
- **server._to_json**：递归把 `Decimal→str`、`datetime→isoformat`、`Enum→value`，让 `JSONResponse`
  可序列化。
- **index.html**：`fetch /api/state` → render 卡片 + drawChart（SVG 折线 + 成交圆点，买绿卖红 A 股色）
  + drawFills（最近 30 笔）。空库提示「先 paper run」。
- **WAL**：`store.db.connect` 对文件库 `PRAGMA journal_mode=WAL`，`paper run` 写 / `serve` 读并发安全。

## ④ 改动历史

- **2026-07-06（M4b 首次实现）**：state（replay + 降采样 + 指标 + 成交点）、server（FastAPI + JSON
  序列化）、index.html（卡片 + SVG 曲线 + 成交表格）。metrics 的回撤 / 夏普提 public、db 加 WAL。
  单测覆盖 `load_state`（空库 / 基础 / 降采样 / 成交点对齐 / 指标）、TestClient（`/`、`/api/state` 200/404）。
