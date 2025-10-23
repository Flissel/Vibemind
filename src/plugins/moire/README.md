# MoireTracker Integration

This directory contains the Python client for MoireTracker desktop automation.

## Components

### Core Files
- **`moire_client.py`** - Low-level client for IPC communication with MoireTracker.exe
- **`moire_agent_toolkit.py`** - High-level toolkit with AutoGen FunctionTool wrappers
- **`__init__.py`** - Module exports and convenient imports

### MoireTracker Executable
The C++ executable is in the git submodule: `external/moire/build/Release/MoireTracker.exe`

## Quick Start

```python
from src.plugins.moire import MoireTrackerClient, scan_desktop, find_text, click_at

# Initialize client
client = MoireTrackerClient()
client.connect()

# Scan desktop
elements = scan_desktop()
print(f"Found {len(elements)} UI elements")

# Find specific text
result = find_text("Excel")
if "FOUND" in result:
    # Click on it
    x, y = 100, 200  # Parse from result
    click_at(x, y)

# Cleanup
client.disconnect()
```

## Available Functions

### Visual Perception
- `scan_desktop()` - OCR scan of entire desktop
- `find_text(text)` - Locate specific text on screen
- `find_element(text)` - Find UI element with coordinates
- `verify_text_visible(text)` - Check if text exists

### Window Management
- `get_active_window()` - Get current window title
- `focus_window(title)` - Bring window to front
- `close_window(title)` - Close application

### Input Control
- `click_at(x, y)` - Click at coordinates
- `type_text(text)` - Type text
- `press_keys(keys)` - Press key combinations

## MoireTracker Submodule

The MoireTracker C++ code and executable are in a git submodule at `external/moire/`.

To update the submodule:
```bash
git submodule update --remote external/moire
```

To rebuild MoireTracker:
```bash
cd external/moire
cmake --build build --config Release
```

## Source Repositories

- **MoireTracker C++**: https://github.com/Flissel/MoireTracker
- **Python Client** (original): `C:/Users/User/Desktop/voice_dialog/python/tools/moire_client.py`
- **Agent Toolkit** (original): `C:/Users/User/Desktop/Moire/moire_agent_toolkit.py`

## Integration Notes

These files are copied from the voice_dialog and Moire repos. If those repos update, sync changes here:

```bash
# Update client
cp "C:/Users/User/Desktop/voice_dialog/python/tools/moire_client.py" src/plugins/moire/

# Update toolkit
cp "C:/Users/User/Desktop/Moire/moire_agent_toolkit.py" src/plugins/moire/
```

## Usage in Sakana

The MoireTracker integration is used by:
- `DesktopObserverPlugin` - Continuous desktop observation
- `AutomationExecutor` - Execute learned automation strategies
- `UIPatternDetector` - Detect UI interaction patterns
