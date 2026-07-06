# Vgrid

ETF 网格量化交易系统。针对银河证券「0.1 元起收 + 万0.5」的超低 ETF 费率设计，做 T+0 类 ETF（先港股类）的网格交易。

## 现状

M1 开发中：核心领域模型 + 网格策略引擎（纯逻辑）。

路线图见 [`docs/roadmap.md`](docs/roadmap.md)。

## 分层

```
src/vgrid/
├── core/        领域模型：订单、成交、持仓、手续费模型、网格配置
├── strategy/    网格引擎（纯逻辑，不碰 I/O）—— 回测和模拟盘共用同一份
├── data/        行情：历史 K 线下载 + 本地缓存（Parquet）          [M2]
├── backtest/    回测器：限价单撮合、绩效统计                        [M2]
├── paper/       模拟盘：实时行情轮询 + 虚拟账户                      [M4]
├── store/       SQLite 持久化（状态 / 订单 / 成交）                 [M2+]
├── report/      绩效报告                                          [M2]
└── cli/         命令行入口                                        [M2]
```

## 开发

```bash
uv sync                       # 装依赖（含 dev）
uv run ruff format .          # 格式化
uv run ruff check .           # 静态检查
uv run mypy                   # 严格类型检查
uv run pytest                 # 单测
```
