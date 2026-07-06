"""领域枚举。"""

from enum import StrEnum


class Side(StrEnum):
    """买卖方向。"""

    BUY = "buy"
    SELL = "sell"


class OrderKind(StrEnum):
    """订单类型。

    - LIMIT：限价单。网格挂在某条网格线上等着被触发。
    - MARKET：市价单。建仓 / 立即重建底仓时按当前价直接成交。
    """

    LIMIT = "limit"
    MARKET = "market"


class SpacingMode(StrEnum):
    """网格间距模式。

    - ARITHMETIC：等差，每格固定「元数」。
    - GEOMETRIC：等比，每格固定「百分比」。
    """

    ARITHMETIC = "arithmetic"
    GEOMETRIC = "geometric"


class BaseBuildMode(StrEnum):
    """建仓模式。

    - CENTER：中枢建仓。启动时把启动价上方所有格子的份额一次买齐做底仓，
      涨上去就有货可卖。
    - ZERO：零底仓。启动不买，只在下方挂买单，跌下来才逐格建仓。
    """

    CENTER = "center"
    ZERO = "zero"


class Frame(StrEnum):
    """K 线时间周期。

    - DAILY：日线，每根代表一个交易日。
    - MINUTE：1 分钟线。后续可扩展 5m / 15m 等。
    """

    DAILY = "1d"
    MINUTE = "1m"
