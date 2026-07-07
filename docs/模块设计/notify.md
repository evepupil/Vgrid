# 模块：notify（信号推送 / 执行抽象雏形）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：把网格触发的成交信号推到微信（server酱 / pushplus），人工在手机 APP 跟单。
切10a「半自动实盘」——只通知，不真下单。模拟盘照常按 `engine.step` 虚拟成交记账，Notifier
把每批成交信号推出去；这份账本 = "如果每次都跟会怎样"的纸面对照。

**定位**：`Notifier` 是「执行 / 通知」抽象的**雏形**。切10b 的光大 QMT Executor 在此接口位置
把 `send(fills)` 换成"调 xtquant 真实下单"，接口不动、只换实现。`core/models.py` 早把
`OrderIntent` 定成「引擎产出意图、执行层决定怎么下」的解耦点，切10b 走那条路。

**关键决策**：
1. **协议可注入（类比 `RealtimeProvider`）**：`Notifier` 是 `@runtime_checkable` Protocol，
   `PaperRunner` 构造时注入；测试 / 离线可 stub（mock post）。
2. **凭证走环境变量，不进代码 / git**：server酱 `SERVERCHAN_SENDKEY`、pushplus `PUSHPLUS_TOKEN`。
3. **标准库 HTTP（urllib），零新依赖**：`post_form` / `post_json` 包内共用，不引 requests，
   免掉 types-requests 依赖。
4. **推送失败不中断模拟盘**：`PaperRunner.process_tick` 里 `except OSError` 兜底——记账比
   通知重要，网络抖动不能停盘。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `base.py` | `Notifier` 协议 + `format_fills`（markdown 格式化）+ `post_form`/`post_json`（urllib） |
| `serverchan.py` | `ServerChanNotifier`：POST `sct.ftqq.com/{key}.send`（title + desp） |
| `pushplus.py` | `PushPlusNotifier`：POST `pushplus.plus/send` JSON `{token, title, content}` |
| `__init__.py` | 导出 + `make_notifier(channel)` 工厂（按通道名 + env 建实例，缺凭证抛 ValueError） |

## ③ 实现细节

- **format_fills**：一批 Fill → markdown（标题「网格 \<symbol\> N 笔」+ 逐笔「买/卖 N 份 @ 价
  （时间，费 X）→ 已实现 Y」）。卖出带 `realized_pnl`，买入不带。
- **make_notifier**：`serverchan` → 读 `SERVERCHAN_SENDKEY`；`pushplus` → 读 `PUSHPLUS_TOKEN`；
  缺凭证 / 未知通道抛 `ValueError`（CLI 捕获退 1，人话报错）。
- **monkeypatch 测试**：patch `vgrid.notify.serverchan.post_form`（模块命名空间里绑定的名字），
  验 URL 含 sendkey、title/desp 正确，不真发。

## ④ 改动历史

- **2026-07-07（切10a 首次实现）**：notify 包（协议 + server酱 + pushplus + 工厂，urllib 标准库）；
  `PaperRunner` 注入 `notifier`，`process_tick` 出 fills 后推送、失败降级；
  `paper run --notify {serverchan,pushplus}` CLI。单测 9 个（mock HTTP 验格式 + 工厂 + 协议结构）。
  门禁：ruff + mypy strict（74 文件）+ pytest 273 全过。
  **下一步切10b**：Notifier 换成光大 QMT Executor（xtquant 真实下单 + 成交回报校准引擎），
  执行器须在国内 Windows 跑（QMT 硬要求），首尔服务器只发指令。
