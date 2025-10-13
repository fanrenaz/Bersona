"""Central version definition.

Edit here (or use scripts/bump_version.py) when releasing.
"""
__all__ = ["__version__", "get_version"]
__version__ = "0.1.1"

def get_version() -> str:
    return __version__
