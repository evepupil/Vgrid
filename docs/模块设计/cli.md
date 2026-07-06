# 模块：cli（命令行入口）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：把 data / backtest / report 串起来的命令行入口。两个子命令：`fetch`（只取数）、
`backtest`（取数 → 回测 → 终端摘要 + Markdown 报告）。纯胶水，按规范不写单测。

**关键决策**：
1. **argparse 零依赖**：不引 click / typer，标准库够用。
2. **策略参数走 JSON 文件**：`--config cfg.json`（`GridConfig.to_dict` 格式）承载完整策略
   旋钮；命令行只暴露数据相关的 symbol / start / end / frame。
3. **渲染与落盘分离**：调 report 拿文本，自己写文件（`reports/<symbol>_<frame>.md`）。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `app.py` | `main`：解析参数、派发 fetch / backtest；`_load_config` 读 JSON、`__write_report` 落盘 |
| `examples/159920.json` | 示例策略配置（`GridConfig.to_dict` 格式） |

## ③ 实现细节

- `fetch`：调 `load_bars` 下数据并缓存，打印根数与区间；无数据返回退出码 1。
- `backtest`：`_load_config` 读 JSON → `GridConfig.from_dict`；`load_bars` 取数；`simulate`
  跑回测；终端打印 `render_summary`，落盘 `render_report`。无数据返回 1。
- `_add_data_args`：fetch / backtest 共用的数据参数（symbol / start / end / frame / refresh）。
- pyproject `[project.scripts] vgrid = "vgrid.cli.app:main"` 注册命令。

## ④ 改动历史

- **2026-07-06（M2 首次实现）**：fetch / backtest 子命令 + 示例配置 + 注册 `vgrid` 脚本。
  端到端冒烟：159920 半年日线成功（下载 98 根 → 回测 → 报告，指标合理）。分钟线真实下载
  受本机代理限制（`push2his.eastmoney.com` 被拦）未验证，但代码路径与日线共用，逻辑由单测覆盖。
