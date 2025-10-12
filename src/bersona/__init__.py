"""Bersona package (src layout).

Public API: from bersona import Bersona
"""
from .astrology_kernel import Bersona  # re-export
from ._version import __version__, get_version

__all__ = ["Bersona", "__version__", "get_version"]
