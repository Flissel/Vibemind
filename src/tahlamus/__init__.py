"""
Tahlamus Integration Module for Sakana

This module provides integration with the Tahlamus cognitive architecture
from https://github.com/Flissel/the_brain

Architecture:
- Tahlamus provides 13 neuroscience-inspired cognitive features
- Sakana uses Tahlamus via path-based import (not pip install)
- Integration enhances Sakana's 7 learning systems
"""

import sys
from pathlib import Path

# Add Tahlamus to Python path
TAHLAMUS_PATH = Path(__file__).parent.parent.parent.parent / "Tahlamus"

if TAHLAMUS_PATH.exists():
    sys.path.insert(0, str(TAHLAMUS_PATH))
    TAHLAMUS_AVAILABLE = True
else:
    TAHLAMUS_AVAILABLE = False
    import warnings
    warnings.warn(
        f"Tahlamus not found at {TAHLAMUS_PATH}. "
        f"Clone from: https://github.com/Flissel/the_brain"
    )

__all__ = ["TAHLAMUS_AVAILABLE", "TAHLAMUS_PATH"]
