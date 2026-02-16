"""
zepp-export: Open-source tools for accessing your Amazfit/Zepp health data.

Your health data. Your rules.
"""

__version__ = "0.3.0"

from .client import ZeppClient
from .exceptions import ZeppAuthError, ZeppAPIError, ZeppDecodeError

__all__ = ["ZeppClient", "ZeppAuthError", "ZeppAPIError", "ZeppDecodeError"]
