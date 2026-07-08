"""data —— 行情下载 + 本地缓存。provider 取数，cache 落 Parquet，loader 是门面。

行情源：日线走 ``TencentProvider``（前复权），分钟走 ``MootdxProvider``（通达信）。
东财 / 新浪（akshare）源已弃用——em 海外不通、sina 不复权。
"""

from vgrid.data.cache import ParquetCache
from vgrid.data.loader import default_cache_dir, load_bars
from vgrid.data.mootdx_provider import MootdxProvider
from vgrid.data.provider import BarProvider
from vgrid.data.tencent_provider import TencentProvider

__all__ = [
    "BarProvider",
    "MootdxProvider",
    "ParquetCache",
    "TencentProvider",
    "default_cache_dir",
    "load_bars",
]
