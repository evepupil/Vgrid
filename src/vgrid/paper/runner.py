"""模拟盘 runner：replay 历史 tick 重建 engine + 长驻轮询实时价。

模拟盘 = 实时版的回测：每个实时 tick 喂给 M1 ``GridEngine.step``，触线即虚拟成交。
启动先 ``replay`` 历史 tick 重建 engine 状态（断点续跑），之后 ``run`` 长驻轮询。
"""

from __future__ import annotations

import sqlite3
import sys
import time as _time
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from vgrid.core.config import GridConfig
from vgrid.core.models import Fill
from vgrid.notify.base import Notifier
from vgrid.paper.realtime import RealtimeProvider
from vgrid.paper.session import in_session, next_session_open
from vgrid.store.repository import (
    load_config,
    load_fills,
    load_ticks,
    save_config,
    save_fill,
    save_tick,
)
from vgrid.strategy.engine import GridEngine


@dataclass(frozen=True, slots=True)
class PaperSnapshot:
    """模拟盘状态快照（展示 / status 用）。"""

    last_price: Decimal | None
    last_ts: datetime | None
    open_lots: int
    committed: Decimal
    realized_pnl: Decimal
    total_fee: Decimal
    cash_flow: Decimal
    n_fills: int


class PaperRunner:
    """模拟盘：replay 重建 engine，之后轮询实时价驱动。"""

    def __init__(
        self,
        config: GridConfig,
        provider: RealtimeProvider,
        conn: sqlite3.Connection,
        *,
        interval: float = 15.0,
        notifier: Notifier | None = None,
    ) -> None:
        self._config = config
        self._provider = provider
        self._conn = conn
        self._interval = interval
        self._notifier = notifier
        self._engine = GridEngine(config)
        self._started = False
        existing = load_config(conn)
        if existing is not None and existing != config:
            raise ValueError("DB 已存不同配置，请用同一库或新库")
        if existing is None:
            save_config(conn, config)

    @property
    def engine(self) -> GridEngine:
        return self._engine

    def replay(self) -> None:
        """读历史 tick 重建 engine 状态（启动时调一次）。无历史则跳过，等首个 tick 再 start。"""
        ticks = load_ticks(self._conn)
        if not ticks:
            return
        self._engine.start(ticks[0][1])
        self._started = True
        for _, price in ticks[1:]:
            self._engine.step(price)

    def process_tick(self, ts: datetime, price: Decimal) -> list[Fill]:
        """处理一个 tick：落库 + 喂 engine。

        首个 tick 走 start（零成交），之后 step。返回本次成交（已落库）。
        有 Notifier 则把成交信号推出去（切10a：只通知不真下单）；推送失败打日志、
        不中断模拟盘——记账比通知重要，不能因网络抖动停盘。
        """
        save_tick(self._conn, ts, price)
        if not self._started:
            fills = [replace(f, ts=ts) for f in self._engine.start(price)]
            self._started = True
        else:
            fills = [replace(f, ts=ts) for f in self._engine.step(price)]
        for f in fills:
            save_fill(self._conn, f)
        if fills and self._notifier is not None:
            try:
                self._notifier.send(fills, symbol=self._config.symbol)
            except OSError as e:
                print(f"推送失败（不中断模拟盘）：{e}", file=sys.stderr)
        return fills

    def step_once(self) -> list[Fill]:
        """盘中取一个实时 tick 并处理；非盘中返回空列表。"""
        now = datetime.now()
        if not in_session(now):
            return []
        ts, price = self._provider.fetch(self._config.symbol)
        return self.process_tick(ts, price)

    def run(self) -> None:
        """长驻循环：盘外 sleep 到开盘，盘中按 interval 轮询。Ctrl+C 停。"""
        self.replay()
        while True:
            now = datetime.now()
            if in_session(now):
                self.step_once()
                _time.sleep(self._interval)
            else:
                wait = max((next_session_open(now) - now).total_seconds(), 1.0)
                _time.sleep(min(wait, 60.0))  # 至多睡 60s，定期重判，防时钟漂移

    def snapshot(self) -> PaperSnapshot:
        """当前状态快照。调用前应已 ``replay``，否则 engine 是初态。"""
        ticks = load_ticks(self._conn)
        last_ts = ticks[-1][0] if ticks else None
        last_price = ticks[-1][1] if ticks else None
        return PaperSnapshot(
            last_price=last_price,
            last_ts=last_ts,
            open_lots=self._engine.open_lots,
            committed=self._engine.committed,
            realized_pnl=self._engine.realized_pnl,
            total_fee=self._engine.total_fee,
            cash_flow=self._engine.cash_flow,
            n_fills=len(load_fills(self._conn)),
        )
