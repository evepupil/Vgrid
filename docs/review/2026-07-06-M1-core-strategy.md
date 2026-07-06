# Review：M1（core + strategy）

- **区间**：`5e74c66`（搭建项目骨架）→ `cff3707`（统一 Bar 模型 + 配置序列化），HEAD
- **性质**：首次 review，覆盖 M1 全量已提交内容
- **范围**：`src/vgrid/core/**`、`src/vgrid/strategy/**`、`tests/` 下 M1 相关的 8 个测试文件
- **不在范围**：工作区里未提交的 `src/vgrid/data/**` 与 `tests/test_{akshare_provider,cache,loader,provider}.py`——属于 M2，尚未 commit，本次不看
- **门禁**（仅 M1 部分）：`pytest` 52 passed / `mypy` clean / `ruff` clean，全绿

---

## 发现的问题

### 1. 跌买触及资金上限时用 `continue`，与注释、与 `desired_orders` 都不一致（中）

**位置**：`src/vgrid/strategy/engine.py:173-174`

```python
fill = self._execute_buy(line.price, shares, target_line.price)
if fill is None:
    continue  # 触及资金上限，停止在更低的格子继续买
```

注释写的是"停止在更低的格子继续买"（即 `break` 语义），代码却是 `continue`。`desired_orders` 里同样这处判断用的是 `break`（`engine.py:149-150`）。两处决策口径不一致，正好撞上模块设计反复强调的"`desired_orders` 和 `step` 共用同一套口径，不会逻辑漂移"。

**实际危害**（在合法配置下能复现）：`down_amount_factor < 1` 是 roadmap 明确支持的档（"越跌买越少"，校验只要求 `>0`）。越往下延伸的格子金额越小、成本越低。当 cap 较紧时，`continue` 会在跳过某个买不起的格子后，继续去买更便宜的下下格，结果持仓位变成非连续的——比如 0.95 和 0.85 都买了、偏偏漏掉中间的 0.90。

**复现**（等差、4 格、`per_grid_amount=2000`、`down_amount_factor=0.5`、`down_spacing_factor=1`、`capital_cap=1200`，ZERO 模式，`start(1.00)` 后 `step(0.80)`）：
- 0.95 线：金额 1000 → 1000 份，成本 ≈ 950.1，committed=950.1 ≤ 1200，买入
- 0.90 线：金额 500 → 500 份，成本 ≈ 450.1，950.1+450.1=1400.2 > 1200，跳过
- 0.85 线：金额 250 → 200 份，成本 ≈ 170.1，950.1+170.1=1120.2 ≤ 1200，**又买入了**

最终持仓 {0.95, 0.85}，漏了 0.90。而 `desired_orders`（用 `break`）在同一状态下只会列到 0.95 为止。两边对不上。

**建议**：改成 `break`，和注释、和 `desired_orders` 对齐。`_fill_buys_descending` 里 `shares <= 0` 那处 `continue` 是对的（金额不够买一手只是个别格子的问题，更低的格子未必也买不起），要保留。

---

### 2. `desired_orders` 是只读查询，却会改 ladder 状态（中）

**位置**：`src/vgrid/strategy/engine.py:137`

```python
def desired_orders(self, price: Decimal) -> list[OrderIntent]:
    ...
    self._ladder.ensure_covers_down_to(price)   # ← 副作用：永久延伸阶梯
```

`desired_orders` 的定位是"当前应该挂着哪些单"，给实盘执行层对账用——按常识是只读查询。但它调了 `ensure_covers_down_to`，会把阶梯往下延伸、推进 `_next_gap` / `_ext_depth`，调用完引擎状态就变了。

由于向下延伸是确定性且幂等的，单看 P&L 数字通常不会立刻算错；但问题是契约层面的：一个"看一眼"的方法不该偷偷改状态。一旦以后加了持久化（M2+ 的 store 层）、或在任意价位反复调用 `desired_orders` 探查，这些提前延伸出来的网格线就会污染保存的状态和后续 `step` 的延伸节奏。

**建议**：让 `desired_orders` 纯粹只读——买单部分要么不改 ladder、在一份临时视图上算"如果现在挂着应该有哪些买单"；要么明确把"对齐阶梯到当前价"这个动作留给 `step`，`desired_orders` 只读当前 ladder。下探延伸的语义本来就该由 `step` 按真实价格驱动。

---

### 3. `extend_levels_down` 纯函数只被测试调用，生产路径另有一套实现（中）

**位置**：`src/vgrid/strategy/gridlines.py:68`（纯函数）vs `src/vgrid/strategy/ladder.py:106`（`Ladder._extend_one`）

grep 确认：`extend_levels_down` 只在 `tests/test_gridlines.py` 和 `strategy/__init__.py` 的导出里出现，`Ladder` 和 `GridEngine` 都没用它。生产路径走的是 `Ladder._extend_one`，自己重新实现了一遍"逐级放大格距往下延伸"。

两套实现已经分叉：`_extend_one` 会按 `down_amount_factor^depth` 放大每格金额（挂单金额随深度变），纯函数 `extend_levels_down` 完全不算金额、只返回价格。模块设计文档把 `extend_levels_down` 列为 gridlines 的四块能力之一，但实际引擎并不通过它走。

**建议**：二选一——要么让 `Ladder` 复用这个纯函数（把"算下一格价格"集中到一处，`_extend_one` 只负责状态推进和金额放大），要么删掉纯函数和它的测试，免得以后改了一处忘了另一处。

---

### 4. 文档/工具链的 Python 版本对不齐（低）

**位置**：`docs/roadmap.md:74`（"Python 3.12"）、`pyproject.toml:6`（`requires-python = ">=3.12"`）、`pyproject.toml:33`（`target-version = "py313"`）、`pyproject.toml:54`（`python_version = "3.13"`）、commit `d4e933c`（"适配 Python 3.13"）

roadmap 工程约定还写着"Python 3.12"，但实际已经升到 3.13（ruff/mypy 都锁 py313，commit log 也明说适配 3.13）。按"文档 = 当前实现"的原则，roadmap 这行得改成 3.13。另外 `requires-python = ">=3.12"` 比工具链目标（3.13）宽松一档，运行时倒不会炸（`StrEnum` 是 3.11+），但语义上最好统一到 3.13。

**建议**：roadmap 工程约定改 3.13；`requires-python` 视实际情况收紧到 `>=3.13`，或显式说明为什么放 3.12。

---

### 5. M1 测试覆盖几个关键分支没摸到（低）

**位置**：`tests/test_engine.py` 等

- **等比模式在引擎层完全没测**。`test_gridlines` 测了等比阶梯生成和等比 `shift_window_up`，但引擎测试的 `make_config` 默认等差，没有任何引擎测试覆盖"等比 ladder + 上破追踪"的完整链路。等比是配置里和等差并列的一档策略，引擎层该有端到端用例。
- **`upper_rebuild_ratio` 只测了 0 和 1**，中间值（按比例部分重建，`_build_center` 里 `shares_for_amount(per_grid_amount * ratio, price)` 走的是分数份额）没测。
- **守卫分支没测**：`start` 重复调用抛 `RuntimeError`、`step` 未 `start` 抛 `RuntimeError`。
- **`down_amount_factor < 1` 没测**——正是问题 1 的盲区，所以那个 bug 没被测试挡住。

**建议**：补等比引擎用例、中间 ratio 用例、两个守卫用例、以及 `down_amount_factor<1` + 紧 cap 的用例（修完问题 1 后顺带加回归）。

---

### 6. `pyproject.toml` 永远显示 modified（CRLF 噪音）（低）

**位置**：仓库根 `core.autocrlf = true` + 工作区 `pyproject.toml` 为 LF

`git status` 一直把 `pyproject.toml` 标成 modified，但 `git diff` 内容为空——因为提交进库的 blob 是 LF，工作区文件也是 LF，而 `autocrlf=true` 期望 Windows 工作区是 CRLF，于是永远认为"该换行的文件被改了"。这对"门禁全绿才 commit"的流程是个持续的噪音：每次都会看到一个假的 dirty 文件。

**建议**：加 `.gitattributes`（推荐 `* text=auto eol=lf`，把全仓统一成 LF，和现有提交一致），然后 `git add --renormalize .` 一次性 normalize。之后这个幽灵 modified 就消失，跨平台也稳定。

---

## 小结

M1 的核心账本逻辑（建仓 / 跌买涨卖配对 / 向上追踪 / 向下放大延伸 / 资金上限 / 守恒）设计是干净的，52 个单测过、类型和风格门禁全绿。主要问题集中在两处决策口径：
- `step` 里跌买的资金上限处理（问题 1）和 `desired_orders`（问题 2 + 问题 1 的另一面）——这两块直接关系到"回测和实盘同一套口径"这个地基，建议优先修。
- `extend_levels_down` 双实现（问题 3）属于工程整洁度，不紧急但该收拢。

文档和工程层面的版本对齐（问题 4、6）和测试补强（问题 5）可以随后跟进。
