"""GUI module for the Sakana Desktop Assistant.

This module provides a modular web interface for the assistant.
"""

from .interface import GUIInterface
from .config import set_data_directories

__all__ = ['GUIInterface', 'set_data_directories']