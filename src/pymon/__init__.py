"""pymon: a Linux system monitor TUI."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("pymon")
except PackageNotFoundError:  # pragma: no cover - running from source tree
    __version__ = "0.1.0"
