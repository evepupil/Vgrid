# 模块：web（控制台）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：本地 FastAPI 控制台后端 + Vite/React/AntD 前端。网页上管多策略 / 跑回测 /
看总资产 / 看在跑实例 / 收藏 ETF / 单实例看盘。后端只读聚合（启停走 `paper run` CLI），
不长驻 engine。

**关键决策**：
1. **后端按域拆 APIRouter**：`routes/{state,strategies,backtest,portfolio}.py` 各管一域，
   `server.py` 只组装 + 注入全局状态（默认库 / 策略库目录 / 数据目录）。新功能加 router，不堆一坨。
2. **纯逻辑与 I/O 分离**：`strategy_store` / `portfolio` / `backtest_api` / `state` 是纯逻辑（单测重点），
   routes 只调它们 + 转 JSON。
3. **通用序列化 / 降采样复用**：`jsonify.py`（Decimal/datetime/Enum → JSON 安全）、`curve.py`
   （等距降采样，PEP 695 泛型）被 state / backtest / portfolio 共用。
4. **Decimal 全程 string 保精度**：API 入参 / 出参的金额 / 价格用 string，前端 InputNumber
   `stringMode`，杜绝浮点误差（和后端 Decimal 一致）。
5. **前端独立 `frontend/`**：Vite + React 19 + TS strict（strict + noUncheckedIndexedAccess）+
   AntD 6 + react-router + TanStack Query + @ant-design/charts。dev server (5173) proxy /api → 8000。
6. **portfolio 只读聚合**：扫 `~/.vgrid/paper/*.db` 各 replay 出状态聚合总资产。「在跑」靠最近 tick
   时间判断（5 分钟内活跃）。启停走 `paper run --db` CLI，web 不跑线程池（避免生命周期 / 恢复复杂度）。
7. **策略库文件化**：`strategies/` 目录存策略 JSON（GridConfig.to_dict 格式），name 正则校验防路径穿越。
   一个策略绑一个 ETF（符合「策略文件化」定位）。

## ② 文件结构

### 后端 `src/vgrid/web/`

| 文件 | 内容 |
|---|---|
| `server.py` | `create_app`：组装 router + 注入 app.state + GET / 旧 HTML |
| `jsonify.py` | `jsonify`：递归 Decimal/datetime/Enum → JSON 安全类型 |
| `curve.py` | `downsample[T]`：等距降采样（PEP 695 泛型） |
| `state.py` | `load_state`：replay engine + 算 snapshot/曲线/指标/成交点 |
| `strategy_store.py` | 策略库 CRUD：文件 I/O + name 正则 + from_dict 校验 |
| `backtest_api.py` | `run_backtest`：simulate + 结果转 dict（曲线降采样 500 点） |
| `portfolio.py` | `PortfolioManager`：扫 paper DB 聚合 + 关注列表 CRUD |
| `routes/{state,strategies,backtest,portfolio}.py` | 各域 APIRouter |
| `templates/index.html` | M4b 旧看盘面板（GET / 默认页，保留） |

### 前端 `frontend/`

| 文件 | 内容 |
|---|---|
| `src/main.tsx` | QueryClientProvider + ConfigProvider(zhCN) + BrowserRouter |
| `src/App.tsx` | Layout：侧边栏导航 + 路由出口 |
| `src/api/client.ts` | 全部后端端点 + 类型定义（fetch 封装） |
| `src/pages/Dashboard.tsx` | 总资产卡片 + 实例表格 + 关注列表 CRUD |
| `src/pages/Backtest.tsx` | 选策略+区间跑回测 → 指标+净值曲线+成交 |
| `src/pages/Strategies.tsx` | 策略列表 + 新建/编辑/复制/删除 |
| `src/pages/Runners.tsx` | 实例列表 + 选中单实例看盘 |
| `src/components/StrategyForm.tsx` | 策略编辑 Modal 表单（GridConfig 全字段） |

## ③ 实现细节

### 后端

- **strategy_store**：`list/read/write/delete` 四操作，写前 `GridConfig.from_dict` 校验合法性；
  name 正则 `^[A-Za-z0-9_\-一-龥]{1,64}$` 防路径穿越；list 跳过坏文件。
- **backtest_api**：`simulate(config, bars)` → metrics + equity_curve + fills；曲线 `downsample` 到
  500 点；metrics 全字段 str 化（Decimal 保精度）。
- **portfolio**：`list_instances` 扫 `paper/*.sqlite`，每个 `load_state` replay → `InstanceView`；
  `summary` 聚合 total_equity / n_running / 累计盈亏；`_status` 按 last_ts 近期判 running/idle；
  关注列表存 `~/.vgrid/portfolio.sqlite`（单独 watchlist 表）。
- **routes**：每个 router 用 `Request.app.state` 取配置；HTTPException + `from exc` 保留异常链；
  策略库 400（非法）/ 404（不存在）。
- **state（M4b）**：replay `GridEngine` 逐 tick 算 `EquityPoint`；`downsample`（提到 curve.py）+
  `_map_to_sampled`（bisect）映射成交点；夏普按日折算近似。

### 前端

- **api/client.ts**：`get/post/put/del` 四 helper（fetch + ok 检查 + json）；每端点一个导出函数 +
  类型（`StrategySummary` / `BacktestResult` / `InstanceView` / `StateView` 等）。
- **TanStack Query**：`useQuery` 获取（refetchInterval 5s 刷新实例状态）、`useMutation` 改
  （成功 `invalidateQueries` 刷新列表）。
- **Table 类型**：AntD 6 顶层未导出 `ColumnsType`，用 `NonNullable<TableProps<T>['columns']>` 提取。
- **StrategyForm**：`configToForm` / `formToConfig` 双向转换（dict ↔ 表单值）；Decimal 字段用
  `InputNumber stringMode`（返 string 保精度）；Modal `destroyOnClose` + `preserve={false}` 关闭清表单。
- **图表**：`@ant-design/charts` 的 `Line`，data 映 equity_curve（equity 转 Number 供绘图）。
- **proxy**：`vite.config.ts` `server.proxy /api` → `http://127.0.0.1:8000`（dev 前端 5173 调后端 8000）。

## ④ 改动历史

- **2026-07-06（M4b）**：state（replay + 降采样 + 指标 + 成交点）、server（FastAPI + JSON 序列化）、
  index.html（卡片 + SVG 曲线 + 成交表格）。metrics 回撤/夏普提 public、db 加 WAL。单测覆盖
  load_state + TestClient。
- **2026-07-07（M5 控制台）**：后端拆 `routes/` 子包 + 通用 `jsonify` / `curve`；新增策略库 CRUD
  （`strategy_store`）、回测 API（`backtest_api`）、portfolio 组合层（多实例聚合 + 关注列表）。
  前端重做：`frontend/`（Vite + React 19 + TS strict + AntD 6 + react-router + TanStack Query +
  @ant-design/charts），4 页面（仪表盘 / 回测 / 策略库 / 模拟盘）+ StrategyForm 组件。旧 HTML 面板
  保留作 GET / 默认页。单测覆盖 strategy_store / backtest_api / portfolio 纯逻辑 + API 端点。
