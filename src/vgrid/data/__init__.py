"""data —— 行情下载 + 本地缓存。provider 取数，cache 落 Parquet，loader 是门面。"""

from vgrid.data.akshare_provider import AkshareProvider
from vgrid.data.cache import ParquetCache
from vgrid.data.loader import default_cache_dir, load_bars
from vgrid.data.provider import BarProvider

__all__ = [
    "AkshareProvider",
    "BarProvider",
    "ParquetCache",
    "default_cache_dir",
    "load_bars",
]
