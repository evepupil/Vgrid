"""JSON 序列化辅助：``Decimal`` / ``datetime`` / ``Enum`` → JSON 安全类型。

策略库、回测、看盘各路由共用，不重复写转换。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum


def jsonify(obj: object) -> object:
    """递归把 ``Decimal``→``str``、``datetime``→ISO、``Enum``→value，其余原样。"""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: jsonify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [jsonify(x) for x in obj]
    return obj
