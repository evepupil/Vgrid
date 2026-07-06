# Vgrid

ETF 网格量化交易系统。针对银河证券「0.1 元起收 + 万0.5」的超低 ETF 费率设计，做 T+0 类 ETF（先港股类）的网格交易。

## 现状

M1–M3 + M4a 已完成：领域模型 + 网格引擎 + 行情下载（akshare）+ 回测器 + 参数扫描 + 绩效报告
+ CLI + 模拟盘（实时轮询 + 虚拟账户 + SQLite 持久化）。能对任意 A 股 / 港股类 ETF 跑回测、
扫参数、盘中跑虚拟账户并断点续跑。Web 面板（M4b）/ 消息推送（M4c）待续。

路线图见 [`docs/roadmap.md`](docs/roadmap.md)。

## 分层

```
src/vgrid/
├── core/        领域模型：订单、成交、持仓、手续费模型、网格配置
├── strategy/    网格引擎（纯逻辑，不碰 I/O）—— 回测和模拟盘共用同一份
├── data/        行情：akshare 历史下载 + Parquet 缓存
├── backtest/    回测器：限价单撮合 + 绩效统计（复用 strategy 引擎）
├── scan/        参数扫描：网格搜索 + 按 metric 排序
├── paper/       模拟盘：实时轮询 + 虚拟账户 + replay
├── store/       SQLite 持久化（tick / fill / config）
├── report/      绩效报告（Markdown + 终端摘要）
└── cli/         命令行入口（fetch / backtest / scan）
```

## 开发

```bash
uv sync                       # 装依赖（含 dev）；无 uv 改用 pip install -e ".[dev]"
uv run ruff format .          # 格式化
uv run ruff check .           # 静态检查
uv run mypy                   # 严格类型检查
uv run pytest                 # 单测
```

## 用法

```bash
vgrid fetch    --symbol 159920 --start 2024-01-01 --end 2025-01-01 --frame 1d   # 取数并缓存
vgrid backtest --symbol 159920 --start 2024-01-01 --end 2025-01-01 --frame 1d \ # 回测出报告
               --config examples/159920.json
vgrid scan     --symbol 159920 --start 2024-01-01 --end 2025-01-01 --frame 1d \ # 参数扫描找最优
               --spec examples/scan_159920.json --metric sharpe --top 10
vgrid paper run    --symbol 159920 --config examples/159920.json --interval 15  # 启动模拟盘（盘中轮询）
vgrid paper status                                                          # 查模拟盘状态
```
