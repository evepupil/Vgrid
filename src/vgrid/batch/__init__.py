"""batch —— 多标的批量回测：同一份定投配置跑一串 ETF，出排名 + 一次性买入对照。

纯消费现有回测引擎（``dca.run_dca``），逐只出「定投 vs 一次性买入」，横向排名。
网格批量因配置带绝对价格、跨标的套不过去，留作后续。
"""

from vgrid.batch.models import SORT_CHOICES, BatchResult, BatchRow
from vgrid.batch.runner import backtest_one, run_batch

__all__ = ["SORT_CHOICES", "BatchResult", "BatchRow", "backtest_one", "run_batch"]
