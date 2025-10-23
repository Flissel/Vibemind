"""
MoireTracker Integration Module

This module provides access to MoireTracker's desktop automation capabilities:
- Visual perception via OCR
- Window management
- Mouse/keyboard control

MoireTracker executable location: external/moire/build/Release/MoireTracker.exe
Python client: moire_client.py (from voice_dialog repo)
Toolkit: moire_agent_toolkit.py (from Moire repo)
"""

from .moire_client import MoireTrackerClient
from .moire_agent_toolkit import (
    scan_desktop,
    find_text,
    find_element,
    verify_text_visible,
    get_active_window,
    focus_window,
    close_window,
    click_at,
    type_text,
    press_keys,
    set_moire_client
)

__all__ = [
    'MoireTrackerClient',
    'scan_desktop',
    'find_text',
    'find_element',
    'verify_text_visible',
    'get_active_window',
    'focus_window',
    'close_window',
    'click_at',
    'type_text',
    'press_keys',
    'set_moire_client'
]
