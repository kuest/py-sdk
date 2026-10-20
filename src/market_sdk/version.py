"""Package version helpers."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("market-sdk")
except PackageNotFoundError:
    __version__ = "0.13.0"
