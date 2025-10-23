"""
Complete MoireTracker Agent Toolkit
Comprehensive tool suite for AutoGen agent swarms

Exposes all MoireTracker capabilities as AutoGen FunctionTool objects:
- Visual perception (OCR scanning, element finding)
- Window management (focus, close, resize, click)
- Keyboard/mouse input
- Status indicators
- Health monitoring

Usage with AutoGen:
    from moire_agent_toolkit import create_moire_toolkit

    tools = create_moire_toolkit(moire_client)

    agent = AssistantAgent(
        name="DesktopController",
        model_client=claude_client,
        tools=tools
    )
"""

import sys
import time
from pathlib import Path
from typing import List, Optional

# Add voice_dialog to path
sys.path.insert(0, str(Path('C:/Users/User/Desktop/voice_dialog/python')))

from tools.moire_client import MoireTrackerClient

# Global MoireTracker client (initialized externally)
_moire_client: Optional[MoireTrackerClient] = None

# Try importing pyautogui for keyboard/mouse control
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("[WARNING] pyautogui not available - keyboard/mouse tools disabled")


def set_moire_client(client: MoireTrackerClient):
    """Set global MoireTracker client instance"""
    global _moire_client
    _moire_client = client


# ============================================================================
# VISUAL PERCEPTION TOOLS
# ============================================================================

def scan_desktop() -> str:
    """Scan desktop for all visible UI elements using OCR

    Returns:
        Formatted string listing all detected elements with positions
        Format: "Found N elements:\n  1. 'text' at (x, y)\n  ..."

    Use cases:
        - See what's currently on screen
        - Find clickable buttons/icons
        - Verify application opened
        - Locate UI elements before clicking
    """
    if not _moire_client:
        return "ERROR: MoireTracker not initialized"

    try:
        elements = _moire_client.scan_desktop()

        # Filter out noise (empty text, control characters)
        text_elements = [e for e in elements if e.text.strip() and not e.text.strip().startswith('<')]

        result = f"Found {len(text_elements)} UI elements:\n"
        for i, elem in enumerate(text_elements[:30], 1):  # Limit to 30 to avoid overflow
            result += f"  {i}. '{elem.text}' at ({int(elem.x)},{int(elem.y)})\n"

        if len(text_elements) > 30:
            result += f"  ... and {len(text_elements) - 30} more elements\n"

        return result
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def find_text(search_text: str, exact_match: bool = False) -> str:
    """Find specific text on screen using OCR

    Args:
        search_text: Text to search for (e.g., "Excel", "Save", "File")
        exact_match: If True, require exact match (default: False for partial)

    Returns:
        "FOUND: 'text' at (x, y)" or "NOT FOUND: 'text'"

    Use cases:
        - Check if application opened (find "Excel")
        - Locate buttons (find "Save")
        - Verify UI elements visible (find "File")
    """
    if not _moire_client:
        return "ERROR: MoireTracker not initialized"

    try:
        element = _moire_client.find_element(search_text, exact_match=exact_match)
        if element:
            return f"FOUND: '{element.text}' at ({int(element.x)},{int(element.y)})"
        else:
            return f"NOT FOUND: '{search_text}'"
    except Exception as e:
        return f"ERROR: {e}"


def get_mouse_position() -> str:
    """Get current mouse cursor position

    Returns:
        "Mouse at (x, y)" or error message

    Use cases:
        - Debug click positions
        - Track mouse movement
    """
    if not _moire_client:
        return "ERROR: MoireTracker not initialized"

    try:
        pos = _moire_client.get_mouse_position()
        if pos:
            return f"Mouse at ({int(pos.x)},{int(pos.y)})"
        else:
            return "ERROR: Could not get mouse position"
    except Exception as e:
        return f"ERROR: {e}"


# ============================================================================
# WINDOW MANAGEMENT TOOLS
# ============================================================================

def focus_window(window_name: str, by_title: bool = True) -> str:
    """Focus (bring to front) a window by title or process name

    Args:
        window_name: Window title or process name to search for
        by_title: If True, search by window title; if False, by process name

    Returns:
        "SUCCESS: Focused 'window_name'" or "FAILED: Could not focus..."

    Use cases:
        - Switch to Excel: focus_window("Excel")
        - Switch to browser: focus_window("Chrome")
        - Prepare window for interaction
    """
    if not _moire_client:
        return "ERROR: MoireTracker not initialized"

    try:
        success = _moire_client.focus_window(window_name, by_title=by_title)
        if success:
            return f"SUCCESS: Focused '{window_name}'"
        else:
            return f"FAILED: Could not focus '{window_name}'"
    except Exception as e:
        return f"ERROR: {e}"


def close_window(window_name: str, by_title: bool = True, force: bool = False) -> str:
    """Close a window by title or process name

    Args:
        window_name: Window title or process name
        by_title: If True, search by window title; if False, by process name
        force: If True, force close; if False, graceful close

    Returns:
        "SUCCESS: Closed 'window_name'" or "FAILED: ..."

    Use cases:
        - Close Excel: close_window("Excel")
        - Force close hung app: close_window("Notepad", force=True)
    """
    if not _moire_client:
        return "ERROR: MoireTracker not initialized"

    try:
        success = _moire_client.close_window(window_name, by_title=by_title, force=force)
        if success:
            return f"SUCCESS: Closed '{window_name}'"
        else:
            return f"FAILED: Could not close '{window_name}'"
    except Exception as e:
        return f"ERROR: {e}"


def resize_window(window_name: str, x: int, y: int, width: int, height: int) -> str:
    """Resize and reposition a window

    Args:
        window_name: Window title to search for
        x: New x position (pixels from left)
        y: New y position (pixels from top)
        width: New width (pixels)
        height: New height (pixels)

    Returns:
        "SUCCESS: Resized 'window_name'" or "FAILED: ..."

    Use cases:
        - Position Excel: resize_window("Excel", 0, 0, 1920, 1080)
        - Side-by-side windows: resize_window("Chrome", 0, 0, 960, 1080)
    """
    if not _moire_client:
        return "ERROR: MoireTracker not initialized"

    try:
        success = _moire_client.resize_window(window_name, x, y, width, height, by_title=True)
        if success:
            return f"SUCCESS: Resized '{window_name}' to {width}x{height} at ({x},{y})"
        else:
            return f"FAILED: Could not resize '{window_name}'"
    except Exception as e:
        return f"ERROR: {e}"


def get_active_window() -> str:
    """Get information about currently active (focused) window

    Returns:
        Formatted string with window details or error message
        Format: "Active window: 'title' (process_name) at (x,y) size WxH"

    Use cases:
        - Check which app is focused
        - Get window coordinates
        - Verify focus changed
    """
    if not _moire_client:
        return "ERROR: MoireTracker not initialized"

    try:
        window = _moire_client.get_active_window()
        if window:
            width = window.right - window.left
            height = window.bottom - window.top
            return (f"Active window: '{window.title}' "
                   f"({window.process_name}) "
                   f"at ({window.left},{window.top}) "
                   f"size {width}x{height}")
        else:
            return "ERROR: Could not get active window"
    except Exception as e:
        return f"ERROR: {e}"


def click_window(window_name: str, x_offset: int, y_offset: int) -> str:
    """Click at specific coordinates within a window

    Args:
        window_name: Window title to click in
        x_offset: X coordinate relative to window's top-left (pixels)
        y_offset: Y coordinate relative to window's top-left (pixels)

    Returns:
        "SUCCESS: Clicked 'window' at (x, y)" or "FAILED: ..."

    Use cases:
        - Click Excel cell: click_window("Excel", 100, 150)
        - Click button: click_window("Notepad", 50, 30)
        - Interactive UI control
    """
    if not _moire_client:
        return "ERROR: MoireTracker not initialized"

    try:
        success = _moire_client.click_window(window_name, x_offset, y_offset, by_title=True)
        if success:
            return f"SUCCESS: Clicked '{window_name}' at ({x_offset},{y_offset})"
        else:
            return f"FAILED: Could not click '{window_name}'"
    except Exception as e:
        return f"ERROR: {e}"


# ============================================================================
# VISUAL CLICKING TOOL (OCR + Click Combined)
# ============================================================================

def click_on_text(target_text: str, exact_match: bool = False) -> str:
    """Find text on screen and click it (OCR-based clicking)

    Args:
        target_text: Text to find and click (e.g., "Save", "Excel", "File")
        exact_match: If True, require exact match; if False, partial match

    Returns:
        "SUCCESS: Clicked 'text' at (x, y)" or "FAILED: ..."

    Use cases:
        - Click "Save" button: click_on_text("Save")
        - Open Excel from search: click_on_text("Excel")
        - Click menu items: click_on_text("File")

    This is the KEY tool for OCR-driven navigation!
    """
    if not _moire_client:
        return "ERROR: MoireTracker not initialized"

    if not PYAUTOGUI_AVAILABLE:
        return "ERROR: pyautogui not available for clicking"

    try:
        # Find element via OCR
        element = _moire_client.find_element(target_text, exact_match=exact_match)

        if not element:
            return f"FAILED: Text '{target_text}' not found on screen"

        # Click at element position
        import pyautogui
        pyautogui.click(element.x, element.y)

        return f"SUCCESS: Clicked '{element.text}' at ({int(element.x)},{int(element.y)})"

    except Exception as e:
        return f"ERROR: {e}"


# ============================================================================
# KEYBOARD & MOUSE INPUT TOOLS
# ============================================================================

def type_text(text: str) -> str:
    """Type text using keyboard

    Args:
        text: Text to type

    Returns:
        "SUCCESS: Typed 'text'" or error message

    Use cases:
        - Enter data: type_text("Product Name")
        - Search: type_text("Excel")
        - Fill forms
    """
    if not PYAUTOGUI_AVAILABLE:
        return "ERROR: pyautogui not available"

    try:
        import pyautogui
        pyautogui.write(text, interval=0.03)
        return f"SUCCESS: Typed '{text}'"
    except Exception as e:
        return f"ERROR: {e}"


def press_keys(keys: str) -> str:
    """Press keyboard key or key combination

    Args:
        keys: Key(s) to press
            Single key: "enter", "tab", "escape", "backspace"
            Combination: "ctrl+c", "ctrl+v", "win+s", "alt+f4"
            Arrow keys: "up", "down", "left", "right"

    Returns:
        "SUCCESS: Pressed 'keys'" or error message

    Use cases:
        - Navigate: press_keys("tab"), press_keys("enter")
        - Shortcuts: press_keys("ctrl+s"), press_keys("ctrl+c")
        - Window control: press_keys("win+s"), press_keys("alt+f4")
        - Arrow navigation: press_keys("right"), press_keys("down")
    """
    if not PYAUTOGUI_AVAILABLE:
        return "ERROR: pyautogui not available"

    try:
        import pyautogui

        if '+' in keys:
            # Key combination (e.g., "ctrl+c")
            key_list = keys.split('+')
            pyautogui.hotkey(*key_list)
        else:
            # Single key
            pyautogui.press(keys)

        return f"SUCCESS: Pressed '{keys}'"
    except Exception as e:
        return f"ERROR: {e}"


# ============================================================================
# STATUS INDICATOR TOOLS
# ============================================================================

def set_ai_working() -> str:
    """Show moiré overlay to indicate AI is actively working

    Returns:
        "SUCCESS: AI indicator shown" or error message

    Use cases:
        - Start of automation task
        - Visual feedback to user
        - Debugging (see when AI is active)
    """
    if not _moire_client:
        return "ERROR: MoireTracker not initialized"

    try:
        success = _moire_client.set_active()
        if success:
            return "SUCCESS: AI indicator shown"
        else:
            return "FAILED: Could not show AI indicator"
    except Exception as e:
        return f"ERROR: {e}"


def set_ai_idle() -> str:
    """Hide moiré overlay to indicate AI is idle/standby

    Returns:
        "SUCCESS: AI indicator hidden" or error message

    Use cases:
        - End of automation task
        - Clear visual indicator
    """
    if not _moire_client:
        return "ERROR: MoireTracker not initialized"

    try:
        success = _moire_client.set_standby()
        if success:
            return "SUCCESS: AI indicator hidden"
        else:
            return "FAILED: Could not hide AI indicator"
    except Exception as e:
        return f"ERROR: {e}"


# ============================================================================
# HEALTH & MONITORING TOOLS
# ============================================================================

def check_health() -> str:
    """Check if MoireTracker is healthy and responsive

    Returns:
        "HEALTHY" or "UNHEALTHY" with details

    Use cases:
        - Diagnose connection issues
        - Monitor system health
        - Verify MoireTracker running
    """
    if not _moire_client:
        return "UNHEALTHY: MoireTracker not initialized"

    try:
        is_healthy = _moire_client.is_healthy()

        if is_healthy:
            return "HEALTHY: MoireTracker responding normally"
        else:
            metrics = _moire_client.get_health_metrics()
            return (f"UNHEALTHY: "
                   f"Circuit state: {metrics['circuit_state']}, "
                   f"Error rate: {metrics['error_rate_percent']}%")
    except Exception as e:
        return f"UNHEALTHY: {e}"


def get_metrics() -> str:
    """Get detailed health metrics from MoireTracker

    Returns:
        Formatted string with all metrics

    Use cases:
        - Debugging issues
        - Performance monitoring
        - Understanding failure patterns
    """
    if not _moire_client:
        return "ERROR: MoireTracker not initialized"

    try:
        metrics = _moire_client.get_health_metrics()

        return (f"MoireTracker Metrics:\n"
               f"  Connected: {metrics['connected']}\n"
               f"  Circuit State: {metrics['circuit_state']}\n"
               f"  Total Requests: {metrics['total_requests']}\n"
               f"  Failed Requests: {metrics['failed_requests']}\n"
               f"  Error Rate: {metrics['error_rate_percent']}%\n"
               f"  Reconnects: {metrics['total_reconnects']}\n"
               f"  Failure Count: {metrics['failure_count']}/{metrics['failure_threshold']}")
    except Exception as e:
        return f"ERROR: {e}"


# ============================================================================
# TOOLKIT FACTORY
# ============================================================================

def create_moire_toolkit(moire_client: MoireTrackerClient) -> list:
    """Create complete MoireTracker toolkit for AutoGen agents

    Args:
        moire_client: Initialized MoireTrackerClient instance

    Returns:
        List of FunctionTool objects for AutoGen

    Usage:
        from autogen_core.tools import FunctionTool

        # Initialize MoireTracker
        client = MoireTrackerClient()
        client.connect()

        # Create toolkit
        tools = create_moire_toolkit(client)

        # Use with AutoGen agent
        agent = AssistantAgent(
            name="DesktopController",
            model_client=claude_client,
            tools=tools
        )
    """
    from autogen_core.tools import FunctionTool

    # Set global client
    set_moire_client(moire_client)

    # Create all tools
    tools = [
        # Visual Perception
        FunctionTool(scan_desktop, description="Scan desktop for all visible UI elements using OCR"),
        FunctionTool(find_text, description="Find specific text on screen"),
        FunctionTool(get_mouse_position, description="Get current mouse position"),

        # Window Management
        FunctionTool(focus_window, description="Focus (bring to front) a window"),
        FunctionTool(close_window, description="Close a window"),
        FunctionTool(resize_window, description="Resize and reposition a window"),
        FunctionTool(get_active_window, description="Get active window information"),
        FunctionTool(click_window, description="Click at coordinates in a window"),

        # OCR-Based Clicking (KEY TOOL!)
        FunctionTool(click_on_text, description="Find text via OCR and click it"),

        # Keyboard & Mouse Input
        FunctionTool(type_text, description="Type text using keyboard"),
        FunctionTool(press_keys, description="Press keyboard keys or combinations"),

        # Status Indicators
        FunctionTool(set_ai_working, description="Show moiré overlay (AI working)"),
        FunctionTool(set_ai_idle, description="Hide moiré overlay (AI idle)"),

        # Health & Monitoring
        FunctionTool(check_health, description="Check MoireTracker health"),
        FunctionTool(get_metrics, description="Get detailed health metrics"),
    ]

    return tools


# ============================================================================
# TOOL CATEGORIES
# ============================================================================

def get_visual_tools(moire_client: MoireTrackerClient) -> list:
    """Get only visual perception tools"""
    from autogen_core.tools import FunctionTool
    set_moire_client(moire_client)

    return [
        FunctionTool(scan_desktop, description="Scan desktop for UI elements"),
        FunctionTool(find_text, description="Find text on screen"),
        FunctionTool(click_on_text, description="Find and click text"),
    ]


def get_window_tools(moire_client: MoireTrackerClient) -> list:
    """Get only window management tools"""
    from autogen_core.tools import FunctionTool
    set_moire_client(moire_client)

    return [
        FunctionTool(focus_window, description="Focus window"),
        FunctionTool(close_window, description="Close window"),
        FunctionTool(resize_window, description="Resize window"),
        FunctionTool(get_active_window, description="Get active window"),
        FunctionTool(click_window, description="Click in window"),
    ]


def get_input_tools(moire_client: MoireTrackerClient) -> list:
    """Get only keyboard/mouse input tools"""
    from autogen_core.tools import FunctionTool
    set_moire_client(moire_client)

    return [
        FunctionTool(type_text, description="Type text"),
        FunctionTool(press_keys, description="Press keys"),
    ]


if __name__ == "__main__":
    # Test the toolkit
    print("MoireTracker Agent Toolkit")
    print(f"Total tools: {len(create_moire_toolkit(None))}")
    print("\nCategories:")
    print(f"  Visual tools: {len(get_visual_tools(None))}")
    print(f"  Window tools: {len(get_window_tools(None))}")
    print(f"  Input tools: {len(get_input_tools(None))}")
