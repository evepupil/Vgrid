"""曲线等距降采样：web 展示用，避免前端渲染上万点卡顿。

state（看盘）和 backtest_api（回测）共用，避免重复实现。
"""

from __future__ import annotations

from collections.abc import Sequence


def downsample[T](curve: Sequence[T], m: int) -> tuple[list[T], list[int]]:
    """等距采样到 m 个点；返回采样曲线 + 采样点在原曲线的索引（升序）。

    n <= m 时原样返回（不采样）。n > m 时取 ``round(i·(n-1)/(m-1))`` 去重排序，
    端点必含。
    """
    n = len(curve)
    if n <= m:
        return list(curve), list(range(n))
    indices = sorted({round(i * (n - 1) / (m - 1)) for i in range(m)})
    return [curve[i] for i in indices], indices
