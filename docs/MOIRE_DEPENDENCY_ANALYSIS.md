# MoireTracker Dependency Analysis

## Risk Assessment: How Updates Affect Sakana

---

## Current Dependency Structure 🔗

### What Sakana Uses

```
Sakana Desktop Assistant
    ↓
src/plugins/moire/
    ├── moire_client.py         ← Depends on voice_dialog modules
    └── moire_agent_toolkit.py  ← Depends on moire_client.py

external/moire/                 ← Git submodule
    └── build/Release/
        └── MoireTracker.exe    ← C++ executable (IPC server)
```

### Dependency Chain

```
moire_agent_toolkit.py
    ↓ imports
moire_client.py
    ↓ imports
- logger (from voice_dialog)
- config (from voice_dialog)
- ipc_auth (from voice_dialog)
- moire_types (from voice_dialog)
- ipc_factory (from voice_dialog)
    ↓ communicates via IPC
MoireTracker.exe (C++ service)
```

---

## Missing Dependencies ❌

The `moire_client.py` file has imports that **don't exist** in Sakana:

```python
from logger import get_logger              # NOT in Sakana
from config import get_config              # NOT in Sakana
from ipc_auth import IPCAuthManager        # NOT in Sakana
from .moire_types import (...)             # NOT in Sakana
from .ipc_factory import create_ipc_backend # NOT in Sakana
```

These are from the **voice_dialog** project, which we didn't copy.

---

## Breaking Change Scenarios 💥

### 1. **MoireTracker.exe IPC Protocol Changes** ⚠️ HIGH RISK

**What could break:**
- Command format changes (e.g., new command structure)
- Response format changes (e.g., different data encoding)
- Shared memory layout changes
- New authentication requirements

**Example:**
```cpp
// OLD: MoireTracker v1.0
struct Command {
    int type;      // 4 bytes
    char data[256]; // 256 bytes
};

// NEW: MoireTracker v2.0 (BREAKING!)
struct Command {
    int version;   // NEW FIELD - shifts everything!
    int type;
    char data[512]; // Different size
};
```

**Impact on Sakana:** ⚠️ **CRITICAL**
- `moire_client.py` would fail to communicate
- All desktop observation would stop working
- Need to update Python client to match

**Likelihood:** Medium (you control both, can coordinate)

---

### 2. **Python Client API Changes** ⚠️ MEDIUM RISK

**What could break:**
- Function signature changes
- Return type changes
- New required parameters
- Removed functions

**Example:**
```python
# OLD: moire_client.py v1.0
def scan_desktop() -> List[DesktopElement]:
    pass

# NEW: moire_client.py v2.0 (BREAKING!)
def scan_desktop(filters: Optional[Dict] = None,
                 region: Optional[Rect] = None) -> ScanResult:
    pass
```

**Impact on Sakana:** ⚠️ **HIGH**
- `DesktopObserverPlugin` would break
- Need to update all call sites
- Tests would fail

**Likelihood:** Low (mature API)

---

### 3. **Missing Dependency Updates** ⚠️ HIGH RISK (Current Issue!)

**What's broken NOW:**
```python
# This import doesn't exist in Sakana:
from logger import get_logger
```

**Impact:** ⚠️ **CRITICAL**
- **Current Status:** `moire_client.py` WILL NOT WORK in Sakana
- Imports will fail immediately
- Cannot instantiate `MoireTrackerClient`

**Likelihood:** 100% (already broken!)

---

## Dependency Stability Tiers 📊

### Tier 1: Stable (Low Risk)
- **MoireTracker.exe location** - Always at `external/moire/build/Release/MoireTracker.exe`
- **Basic OCR functions** - `scan_desktop()`, `find_text()` unlikely to change
- **Window operations** - `get_active_window()` is fundamental

### Tier 2: Moderate (Medium Risk)
- **IPC protocol** - Could evolve (versioning helps)
- **Data structures** - `DesktopElement` fields might expand
- **Return types** - Could become more structured (e.g., Result<T>)

### Tier 3: Unstable (High Risk)
- **Internal dependencies** - logger, config, ipc_auth (currently broken!)
- **Authentication** - `IPCAuthManager` could add requirements
- **Configuration format** - `get_config()` structure might change

---

## Solutions to Dependency Issues ✅

### Option 1: **Make Client Self-Contained** (RECOMMENDED)

Create a standalone version without external dependencies:

```python
# src/plugins/moire/moire_client_standalone.py

import struct
import mmap
import logging
from typing import List, Optional
from dataclasses import dataclass

# Use Python's built-in logging (no external logger dependency)
logger = logging.getLogger(__name__)

@dataclass
class DesktopElement:
    """No external dependencies - define locally"""
    text: str
    x: int
    y: int
    confidence: float

class MoireTrackerClient:
    """Standalone client - no voice_dialog dependencies"""

    def __init__(self, timeout_ms: int = 5000):
        self.timeout_ms = timeout_ms
        self.shm = None  # Direct mmap usage

    def connect(self) -> bool:
        """Connect using Windows shared memory directly"""
        try:
            # Direct Windows IPC - no ipc_factory dependency
            import win32file
            import win32con

            self.shm = mmap.mmap(
                -1,  # Anonymous
                4096,  # Size
                "MoireTrackerIPC"  # Name
            )
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def scan_desktop(self) -> List[DesktopElement]:
        """Scan without external dependencies"""
        # Direct IPC implementation
        pass
```

**Pros:**
- ✅ No external dependencies
- ✅ Won't break when voice_dialog changes
- ✅ Full control over behavior
- ✅ Can use Sakana's logging system

**Cons:**
- ⚠️ Need to maintain IPC code ourselves
- ⚠️ Duplicate effort (reimplementing IPC)

---

### Option 2: **Copy Full Voice Dialog Tooling**

Copy ALL dependencies from voice_dialog:

```
src/plugins/moire/
├── moire_client.py
├── moire_agent_toolkit.py
├── logger.py           # NEW: From voice_dialog
├── config.py           # NEW: From voice_dialog
├── ipc_auth.py         # NEW: From voice_dialog
├── moire_types.py      # NEW: From voice_dialog
└── ipc_factory.py      # NEW: From voice_dialog
```

**Pros:**
- ✅ Client works immediately
- ✅ No code changes needed
- ✅ All features preserved (auth, retry, circuit breaker)

**Cons:**
- ⚠️ More code to maintain
- ⚠️ Still coupled to voice_dialog design
- ⚠️ Updates require copying multiple files

---

### Option 3: **Voice Dialog as Submodule** (Like Moire)

```bash
git submodule add https://github.com/Flissel/voice-dialog.git external/voice-dialog
```

Then:
```python
# In Sakana
import sys
sys.path.insert(0, "external/voice-dialog/python/tools")
from moire_client import MoireTrackerClient  # Now works!
```

**Pros:**
- ✅ Always up-to-date with voice_dialog
- ✅ No code duplication
- ✅ Single source of truth

**Cons:**
- ⚠️ Two submodules to manage
- ⚠️ voice_dialog changes can break Sakana
- ⚠️ Tighter coupling

---

## Recommended Approach 🎯

### **Hybrid: Facade Pattern**

Create a **thin adapter** that wraps the complex client:

```python
# src/plugins/moire/sakana_moire_adapter.py

"""
Sakana-specific MoireTracker adapter
Isolates Sakana from voice_dialog dependencies
"""

import sys
from pathlib import Path
import logging

# Add voice_dialog to path ONLY for this module
VOICE_DIALOG_PATH = Path(__file__).parent.parent.parent.parent / "external" / "voice-dialog" / "python" / "tools"
if VOICE_DIALOG_PATH.exists():
    sys.path.insert(0, str(VOICE_DIALOG_PATH))
    from moire_client import MoireTrackerClient as _MoireClient
    HAS_FULL_CLIENT = True
else:
    HAS_FULL_CLIENT = False

logger = logging.getLogger(__name__)

class SakanaMoireClient:
    """Sakana-specific wrapper around MoireTracker"""

    def __init__(self):
        if HAS_FULL_CLIENT:
            self._client = _MoireClient()
        else:
            # Fallback: minimal implementation
            self._client = MinimalMoireClient()

    def scan_desktop(self):
        """Scan desktop - Sakana interface"""
        try:
            return self._client.scan_desktop()
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return []

    # ... other methods

class MinimalMoireClient:
    """Fallback implementation if voice_dialog not available"""
    def scan_desktop(self):
        # Basic implementation without dependencies
        pass
```

**Benefits:**
- ✅ Works with OR without voice_dialog
- ✅ Sakana code isolated from changes
- ✅ Can upgrade independently
- ✅ Graceful degradation

---

## Migration Strategy 📋

### Phase 1: Make It Work (This Week)
1. Copy missing dependencies from voice_dialog
2. Get `moire_client.py` working in Sakana
3. Test basic `scan_desktop()` call

### Phase 2: Isolate (Next Week)
1. Create `SakanaMoireAdapter`
2. Move Sakana code to use adapter
3. Test with/without voice_dialog

### Phase 3: Stabilize (Future)
1. Define stable interface contract
2. Version adapter API
3. Add integration tests

---

## Breaking Change Detection 🔍

### Add Version Checks

```python
# In adapter
REQUIRED_MOIRE_VERSION = "1.0.0"

def check_compatibility():
    """Verify MoireTracker version compatible"""
    try:
        version = moire_client.get_version()
        if version < REQUIRED_MOIRE_VERSION:
            logger.warning(f"MoireTracker {version} < {REQUIRED_MOIRE_VERSION}")
            return False
        return True
    except AttributeError:
        logger.error("MoireTracker missing get_version() - old version?")
        return False
```

### Add Integration Tests

```python
# tests/integration/test_moire_compatibility.py

def test_moire_scan_returns_elements():
    """Verify scan_desktop() returns expected structure"""
    client = SakanaMoireClient()
    elements = client.scan_desktop()

    assert isinstance(elements, list)
    if elements:
        elem = elements[0]
        assert hasattr(elem, 'text')
        assert hasattr(elem, 'x')
        assert hasattr(elem, 'y')

def test_moire_find_text_format():
    """Verify find_text() returns expected format"""
    client = SakanaMoireClient()
    result = client.find_text("test")

    assert isinstance(result, str)
    assert "FOUND" in result or "NOT FOUND" in result
```

---

## Summary 📝

### Current Status: ⚠️ **BROKEN**
- `moire_client.py` has missing dependencies
- Cannot instantiate `MoireTrackerClient` in Sakana
- Needs immediate fix

### Risk Levels:
- **IPC Protocol Changes**: Medium risk (you control both)
- **API Signature Changes**: Low risk (mature API)
- **Missing Dependencies**: **HIGH RISK (current issue!)**

### Recommended Fix:
1. **Short-term**: Copy missing files from voice_dialog
2. **Long-term**: Create `SakanaMoireAdapter` facade
3. **Best practice**: Add version checks + integration tests

### Next Action:
Choose Option 2 or 3 to resolve missing dependencies NOW.

**Should I:**
- **A)** Copy missing voice_dialog files to `src/plugins/moire/`?
- **B)** Add voice-dialog as second submodule?
- **C)** Create standalone minimal client?

Let me know which approach you prefer! 🎯
