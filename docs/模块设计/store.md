# 模块：store（SQLite 持久化）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：给模拟盘落盘 tick / 成交 / 配置，支持断点续跑。纯 I/O，金额 / 价格存 `string`
（`Decimal` 无损），ts 存 ISO 字符串。用 stdlib `sqlite3`，零额外依赖。

**关键决策**：
1. **单库单模拟盘**：`config` 表 `id=1` 单行约束，一个库对应一条策略的实盘。
2. **存原始值，不存派生**：只存 tick + 成交 + 配置；engine 状态（持仓 / 账本）由 `paper`
   replay tick 重建，不在 store 里序列化——engine 纯逻辑不加序列化代码。
3. **tick 用 INSERT OR REPLACE**：同 ts 覆盖，防重复。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `db.py` | `connect(path)` 建 schema（config / tick / fill 三表） |
| `repository.py` | `save/load_config`、`save/load_tick`、`save/load_fill` |

## ③ 表结构

- `config(id PK = 1, json)`：策略配置 JSON（`GridConfig.to_dict`）。
- `tick(ts PK, price)`：实时 tick，按 ts 升序读。
- `fill(seq PK 自增, ts, side, price, shares, fee, level_index, realized_pnl)`：成交历史，
  按 seq（写入顺序）升序读；`realized_pnl` 可空（买入为 NULL）。

## ④ 改动历史

- **2026-07-06（M4a 首次实现）**：db + repository（config upsert、tick `INSERT OR REPLACE`、
  fill 含 `realized_pnl`）。单测覆盖往返、精度、排序、同 ts 覆盖。
