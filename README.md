# Vgrid

ETF 网格量化交易系统。针对银河证券「0.1 元起收 + 万0.5」的超低 ETF 费率设计，主战场是 T+0 类 ETF（先港股类）——网格策略在高波动、可日内反复买卖的标的上才吃得开。从取数、回测、参数扫描，到模拟盘、网页控制台、再到半自动实盘推送，端到端打通。

## 几条守住的原则

- **回测 / 模拟盘 / 实盘共用同一份网格引擎**——阶梯结构、成交口径完全一致，回测里验证的东西，盘中不会走样。
- **已实现套利利润与持仓浮动盈亏永远分开**，不合并成一个含糊的「总收益」。
- **金额、价格一律走 Decimal**，杜绝浮点误差；前后端都开严格类型（mypy strict / TS strict）。
- **模拟盘绝不触发真实下单**，只按成交价计得失；真实下单走单独的执行通道。

## 功能

**引擎 + 回测**

- 网格回测：限价单撮合、绩效统计、回撤序列、买入持有对照、期末阶梯快照、过拟合提示
- 参数扫描：网格参数笛卡尔积 + 按夏普 / 总收益 / 年化 / 卡玛比排序（含「躺平配置」防刷分）
- 量化定投（DCA）：固定金额 / 加码 / 偏离加码三档，XIRR 真实年化
- 策略对比：网格 vs 定投 vs 买入持有，同区间同起始现金
- 红利 ETF 对比：批量四口径收益（价格 / 价+现金分红 / 价+分红再投 / 累计净值）
- 红利增强：单只 ETF「策略 + 分红再投」对照，量化分红到底加了多少

**交易 + 看盘**

- 模拟盘：mootdx 实时轮询 + 虚拟账户 + SQLite 持久化，Ctrl+C 停、重启 replay 续跑
- 网页控制台（七屏）：仪表盘 / 组合总览 / 回测 / 策略对比 / 红利（对比+增强）/ 策略库 / 关注
- 网格阶梯可视化：结构化阶梯（卖单 / 买单 / 排队 / 放大区）+ 现价线 + 资金上限线
- 风控推演：资金占用兜底 + 下跌 / 破下沿 / 最大占用三档黑天鹅推演
- 双模式：`live` / `sim` 镜像账户，实例 / 持仓 / 盈亏按 mode 目录隔离，关注列表跨 mode 共享
- 到价推送：server酱 / pushplus，网格触发推微信人工跟单（半自动实盘）

## 技术栈

**后端** — Python 3.13 · FastAPI + uvicorn · mootdx + 腾讯 fqkline + akshare + 东财（多数据源）· Parquet 缓存 · SQLite 持久化 · Decimal 金额
门禁：ruff（格式化 + 含 ANN 的静态检查）· mypy strict · pytest

**前端** — React 19 · TypeScript（strict）· Vite · TanStack Query + Table · react-hook-form · Radix UI（无头组件）· uPlot
门禁：tsc + oxlint + vite build

## 目录结构

```
src/vgrid/
├── core/       领域模型：订单 / 成交 / 持仓 / 手续费 / 网格配置
├── strategy/   网格引擎（纯逻辑）—— 回测 / 模拟盘 / 实盘共用
├── data/       行情：mootdx(实时+分钟) / 腾讯(日K) / akshare(现货表) + Parquet 缓存
├── backtest/   回测：限价单撮合 + 绩效 + 策略对比
├── scan/       参数扫描
├── dca/        量化定投引擎 + XIRR
├── income/     红利 ETF：分红 / 净值 / 四口径收益 / 增强 combo
├── paper/      模拟盘：实时轮询 + 虚拟账户 + replay
├── notify/     到价推送（Notifier 协议 + server酱 / pushplus）
├── analysis/   网格适配评分 + 黑天鹅推演
├── store/      SQLite 持久化
├── report/     绩效报告（Markdown + 终端摘要）
├── web/        控制台后端（FastAPI 各端点）
├── cli/        命令行入口
└── frontend/   控制台前端（见 frontend/）
```

## 快速开始

```bash
uv sync                     # 装依赖（含 dev）；无 uv 改 pip install -e ".[dev]"
cd frontend && npm install  # 前端依赖（首次）

# 跑一次回测尝鲜
uv run vgrid backtest --symbol 159920 --start 2024-01-01 --end 2025-01-01 \
    --frame 1d --config examples/159920.json
```

## 命令行

> 以下命令前缀 `uv run`，或激活 venv 后直接 `vgrid`。

```bash
# 取数并缓存（预热 / 调试）
vgrid fetch --symbol 159920 --start 2024-01-01 --end 2025-01-01 --frame 1d

# 网格回测 → 终端摘要 + Markdown 报告
vgrid backtest --symbol 159920 --start 2024-01-01 --end 2025-01-01 --frame 1d \
    --config examples/159920.json

# 参数扫描 → top-N + 最优组合报告（metric: sharpe/total_return/annualized_return/calmar）
vgrid scan --symbol 159920 --start 2024-01-01 --end 2025-01-01 --frame 1d \
    --spec examples/scan_159920.json --metric sharpe --top 10

# 量化定投回测（config 为 DcaConfig 的 to_dict 格式）
vgrid dca --symbol 159920 --start 2024-01-01 --end 2025-01-01 --frame 1d --config dca.json

# 网格 / 定投 / 买入持有 同区间对比
vgrid compare --symbol 159920 --start 2024-01-01 --end 2025-01-01 \
    --grid-config examples/159920.json --dca-config dca.json

# 红利 ETF 批量对比（默认红利关键词池；给 --symbols 跳过筛选）
vgrid income compare --start 2021-01-01 --end 2024-12-31
vgrid income compare --start 2021-01-01 --end 2024-12-31 --symbols 510880,515180

# 单只红利 ETF：策略 + 分红再投增强
vgrid income enhance --symbol 510880 --start 2021-01-01 --end 2024-12-31 \
    --strategy dca --config dca.json

# 模拟盘（盘中长驻轮询；--notify 半自动推微信，只通知不下单）
vgrid paper run    --symbol 159920 --config examples/159920.json --interval 15
vgrid paper run    --symbol 159920 --config examples/159920.json --notify serverchan
vgrid paper status
```

## 网页控制台

```bash
cd frontend && npm run build    # 构建前端 → frontend/dist（首次 / 改前端后跑一次）
vgrid paper serve --port 8000   # 启动控制台（127.0.0.1:8000，含前端）

cd frontend && npm run dev      # 开发模式（HMR，5180，proxy /api → 8000）
```

七屏：仪表盘 · 组合总览 · 回测 · 策略对比 · 红利（对比+增强）· 策略库 · 关注。
顶部模式开关切 `实盘 LIVE ⇄ 模拟盘 SIM`，切模式即换一整套数据（关注列表除外，跨模式共享）。

## 数据源

| 用途 | 源 | 备注 |
|---|---|---|
| 实时报价 / 名称 / 代码验证 / 分钟线 | mootdx（通达信 TCP 7709） | 海外稳定，主力 |
| 历史 K 线（日） | 腾讯 fqkline | 前复权 / 不复权 |
| 分红 / 基金净值 | 东方财富 em | 仅基金接口可用 |
| 现货报价表（批量） | akshare | Ticker / 关注 / 实例卡 |

行情有 Parquet 本地缓存，`--refresh` 强制重下。

## 开发（门禁）

```bash
uv run ruff format .            # 格式化
uv run ruff check .             # 静态检查（含类型标注 ANN）
uv run mypy                     # 严格类型检查
uv run pytest                   # 单测
cd frontend && npm run build    # 前端构建（含 tsc 类型检查）
cd frontend && npm run lint     # 前端 oxlint
```

## 部署

生产跑在 Linux 服务器，systemd 守护 `vgrid paper serve`，控制台只绑 `127.0.0.1`，通过 Cloudflare Tunnel 访问，不公网暴露。

## 文档

- [路线图](docs/roadmap.md) — 里程碑 M1–M7 + 竖切切0–10
- [前端驱动需求清单](docs/需求/前端驱动需求清单.md) — 控制台逐条 FR 验收清单
- [红利 ETF 分红收益对比需求](docs/需求/红利ETF分红收益对比需求.md)
- [模块设计](docs/模块设计/) — 各模块「不看代码就能看懂」的归档
- [设计 demo](docs/design/console.html) — 可交互的控制台原型
