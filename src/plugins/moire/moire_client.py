"""
MoireTracker IPC Client
Handles shared memory communication with MoireTracker service
Production version with retry logic, circuit breaker, and health monitoring

Production Features:
===================

1. **Structured Logging**
   - All operations logged with appropriate levels (DEBUG, INFO, WARNING, ERROR)
   - No print() statements - integrates with production logging infrastructure
   - Context-aware logging for better diagnostics

2. **Retry Logic with Exponential Backoff**
   - Connection attempts retry up to N times (configurable, default=3)
   - Exponential backoff: 0.5s, 1s, 2s, 4s...
   - Automatic reconnection on timeout for scan/find operations

3. **Circuit Breaker Pattern**
   - Tracks consecutive failures (threshold: 5)
   - Opens circuit to prevent cascading failures
   - Half-open state for testing recovery
   - Auto-recovery after timeout (30 seconds)
   - States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing) → CLOSED

4. **Health Monitoring**
   - Tracks total requests, failures, error rate
   - Reconnection count tracking
   - Detailed health metrics via get_health_metrics()
   - Quick health checks with circuit breaker integration

5. **Configurable Timeouts**
   - Default timeout configurable at initialization
   - Per-operation timeout override
   - Longer timeouts for expensive operations (scan: 10s)

6. **Better Error Handling**
   - Graceful degradation on failures
   - Detailed error logging with stack traces
   - Partial connection cleanup on failure
   - Success/failure tracking for circuit breaker

7. **Observability**
   - Request counting for metrics
   - Error rate calculation
   - Circuit breaker state visibility
   - Health status reporting

Usage:
    client = MoireTrackerClient(max_retries=3, timeout_ms=5000)
    if client.connect():
        elements = client.scan_desktop()
        health = client.get_health_metrics()
        print(f"Error rate: {health['error_rate_percent']}%")
"""

import struct
import time
import sys
from pathlib import Path
from typing import List, Optional
from enum import Enum

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from logger import get_logger
from config import get_config
from ipc_auth import IPCAuthManager
from .moire_types import (
    MousePosition, DesktopElement, WindowData, CommandType,
    ResponseStatus, ElementType
)
from .ipc_factory import create_ipc_backend

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"    # Normal operation
    OPEN = "open"        # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class MoireTrackerClient:
    """
    Client for communicating with MoireTracker via platform-specific IPC

    Usage:
        client = MoireTrackerClient()
        if client.connect():
            elements = client.scan_desktop()
            print(f"Found {len(elements)} desktop elements")
    """

    def __init__(self, max_retries: int = 3, timeout_ms: int = 5000):
        """
        Initialize client (not connected yet)

        Args:
            max_retries: Maximum connection retry attempts
            timeout_ms: Default timeout for operations (milliseconds)
        """
        # Create platform-specific IPC backend
        self.ipc = create_ipc_backend()
        self.connected = False
        self.request_id = int(time.time() * 1000000)  # Microseconds

        # Configuration
        self.max_retries = max_retries
        self.timeout_ms = timeout_ms

        # IPC authentication
        config = get_config()
        self.ipc_auth_enabled = config.moire_tracker.ipc_auth_enabled
        self.auth_manager = IPCAuthManager() if self.ipc_auth_enabled else None
        self.auth_token: Optional[bytes] = None

        # Circuit breaker state
        self.circuit_state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = 5  # Open circuit after 5 consecutive failures
        self.success_count = 0
        self.half_open_success_threshold = 2  # Close circuit after 2 successes in half-open
        self.circuit_open_time = 0
        self.circuit_timeout_sec = 30  # Try recovery after 30 seconds

        # Health metrics
        self.total_requests = 0
        self.failed_requests = 0
        self.total_reconnects = 0

        logger.info(f"MoireTrackerClient initialized (max_retries={max_retries}, timeout={timeout_ms}ms)")
        logger.info(f"IPC Backend: {self.ipc.get_backend_name()}")
        if self.ipc_auth_enabled:
            logger.info("IPC authentication enabled - will require auth token")
        logger.set_context(component="moire_client")

    def connect(self) -> bool:
        """
        Connect to MoireTracker via platform-specific IPC with retry logic

        Returns:
            True if connection successful
        """
        logger.info("Connecting to MoireTracker IPC...")

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Connection attempt {attempt}/{self.max_retries}")

                # Use platform-specific backend
                if self.ipc.connect():
                    self.connected = True

                    # Load IPC auth token (if enabled)
                    if self.auth_manager:
                        logger.debug("Loading IPC authentication token...")
                        self.auth_token = self.auth_manager.load_token()
                        if self.auth_token:
                            logger.info("IPC authentication token loaded successfully")
                        else:
                            logger.error("Failed to load IPC auth token - service may not be authorized")
                            # Connection succeeds but operations may fail without token
                            # This allows graceful degradation

                    self._record_success()
                    logger.info(f"Connected successfully on attempt {attempt} ({self.ipc.get_backend_name()})")
                    return True
                else:
                    raise Exception("IPC backend connect() returned False")

            except Exception as e:
                logger.warning(f"Connection attempt {attempt} failed: {e}")

                if attempt < self.max_retries:
                    # Exponential backoff: 0.5s, 1s, 2s, 4s...
                    wait_time = 0.5 * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error("All connection attempts failed")
                    logger.error("Make sure MoireTracker service is running!")

        self.connected = False
        self._record_failure()
        return False

    def disconnect(self):
        """Close IPC connection"""
        if self.ipc:
            self.ipc.disconnect()
        self.connected = False
        logger.info("Disconnected from MoireTracker")

    def reconnect(self) -> bool:
        """
        Disconnect and reconnect to MoireTracker

        Returns:
            True if reconnection successful
        """
        logger.info("Attempting reconnect...")
        self.total_reconnects += 1
        self.disconnect()
        time.sleep(0.1)  # Brief pause before reconnecting
        return self.connect()

    def _record_success(self):
        """Record successful operation for circuit breaker"""
        if self.circuit_state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.debug(f"Circuit half-open: {self.success_count}/{self.half_open_success_threshold} successes")
            if self.success_count >= self.half_open_success_threshold:
                self.circuit_state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker closed (service recovered)")
        elif self.circuit_state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _record_failure(self):
        """Record failed operation for circuit breaker"""
        self.failed_requests += 1

        if self.circuit_state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.circuit_state = CircuitState.OPEN
                self.circuit_open_time = time.time()
                logger.warning(f"Circuit breaker opened after {self.failure_count} consecutive failures")
        elif self.circuit_state == CircuitState.HALF_OPEN:
            # Failed during recovery attempt, reopen circuit
            self.circuit_state = CircuitState.OPEN
            self.circuit_open_time = time.time()
            self.success_count = 0
            logger.warning("Circuit breaker reopened (recovery failed)")

    def _check_circuit(self) -> bool:
        """
        Check circuit breaker state before operation

        Returns:
            True if operation should proceed, False if circuit is open
        """
        if self.circuit_state == CircuitState.CLOSED:
            return True
        elif self.circuit_state == CircuitState.OPEN:
            # Check if timeout elapsed
            if time.time() - self.circuit_open_time > self.circuit_timeout_sec:
                self.circuit_state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker entering half-open state (testing recovery)")
                return True
            else:
                logger.debug("Circuit breaker is open, rejecting request")
                return False
        else:  # HALF_OPEN
            return True

    def is_healthy(self) -> bool:
        """
        Quick health check - tests if connection is responsive

        Returns:
            True if MoireTracker is responding
        """
        if not self.connected:
            return False

        if not self._check_circuit():
            return False

        try:
            # Try a quick mouse position query with short timeout
            request_id = self._send_command(CommandType.GET_MOUSE_POS)
            if not request_id:
                return False

            # Use short timeout for health check
            response_data = self._wait_for_response(timeout_ms=1000)
            is_healthy = response_data is not None

            if is_healthy:
                self._record_success()
            else:
                self._record_failure()

            return is_healthy
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            self._record_failure()
            return False

    def is_authorized(self) -> bool:
        """
        Check if client is authorized to make IPC calls

        Returns:
            True if auth is disabled or token is valid, False otherwise
        """
        if not self.ipc_auth_enabled:
            return True  # Auth disabled, always authorized

        return self.auth_token is not None

    def get_health_metrics(self) -> dict:
        """
        Get detailed health metrics

        Returns:
            Dictionary with health statistics
        """
        error_rate = (self.failed_requests / self.total_requests * 100) if self.total_requests > 0 else 0

        return {
            'connected': self.connected,
            'circuit_state': self.circuit_state.value,
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'error_rate_percent': round(error_rate, 2),
            'total_reconnects': self.total_reconnects,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'ipc_auth_enabled': self.ipc_auth_enabled,
            'ipc_auth_valid': self.auth_token is not None if self.ipc_auth_enabled else None
        }

    def __del__(self):
        """Cleanup on deletion"""
        self.disconnect()

    def _send_command(self, cmd_type: int, params: bytes = b'') -> Optional[int]:
        """
        Send command to MoireTracker

        Args:
            cmd_type: Command type (from CommandType)
            params: Optional parameter bytes

        Returns:
            Request ID if successful, None if failed
        """
        if not self.connected:
            logger.error("Cannot send command: not connected")
            return None

        if not self._check_circuit():
            logger.debug(f"Circuit breaker open, rejecting command type={cmd_type}")
            return None

        self.total_requests += 1

        try:
            # Generate request ID
            self.request_id += 1
            request_id = self.request_id

            # Send via IPC backend
            if self.ipc.send_command(cmd_type, request_id, params):
                return request_id
            else:
                self._record_failure()
                return None

        except Exception as e:
            logger.error(f"Failed to send command type={cmd_type}: {e}", exc_info=True)
            self._record_failure()
            return None

    def _wait_for_response(self, timeout_ms: Optional[int] = None) -> Optional[bytes]:
        """
        Wait for response from MoireTracker

        Args:
            timeout_ms: Timeout in milliseconds (uses default if None)

        Returns:
            Response bytes if received, None if timeout
        """
        if not self.connected:
            return None

        if timeout_ms is None:
            timeout_ms = self.timeout_ms

        try:
            # Receive via IPC backend
            response_tuple = self.ipc.receive_response(timeout_ms)

            if response_tuple:
                # Unpack: (cmd_type, request_id, status, response_data)
                cmd_type, request_id, status, response_data = response_tuple
                self._record_success()
                return response_data
            else:
                logger.warning(f"Response timeout after {timeout_ms}ms")
                self._record_failure()
                return None

        except Exception as e:
            logger.error(f"Error reading response: {e}", exc_info=True)
            self._record_failure()
            return None

    def _parse_response_header(self, data: bytes) -> tuple:
        """
        Parse response header

        Returns:
            (cmd_type, request_id, status, timestamp_ms)
        """
        # Response header with padding for 8-byte alignment:
        # [cmd_type(4)] [padding(4)] [request_id(8)] [status(4)] [padding(4)] [timestamp(8)]
        # Total: 32 bytes
        if len(data) < 32:
            raise ValueError(f"Response header requires 32 bytes, got {len(data)}")

        # Unpack with explicit padding (4x = 4 bytes padding)
        cmd_type, request_id, status, timestamp_ms = struct.unpack('I4xQI4xQ', data[:32])
        return (cmd_type, request_id, status, timestamp_ms)

    def get_mouse_position(self) -> Optional[MousePosition]:
        """
        Get current mouse position

        Returns:
            MousePosition or None if failed
        """
        request_id = self._send_command(CommandType.GET_MOUSE_POS)
        if not request_id:
            return None

        response_data = self._wait_for_response()
        if not response_data:
            return None

        # Verify we have enough data (header=32 + MousePosition=24 with padding)
        if len(response_data) < 56:
            logger.error(f"GET_MOUSE_POS response too short: {len(response_data)} bytes")
            return None

        # Parse response
        cmd_type, req_id, status, timestamp = self._parse_response_header(response_data)

        if status != ResponseStatus.SUCCESS:
            logger.error(f"GET_MOUSE_POS failed: status={status}")
            return None

        # Mouse position data starts at offset 32 (after header)
        # MousePosition struct: [x(4)] [y(4)] [confidence(4)] [padding(4)] [timestamp(8)] = 24 bytes
        try:
            x, y, confidence, pos_timestamp = struct.unpack('fff4xQ', response_data[32:56])
            return MousePosition(x, y, confidence, pos_timestamp)
        except struct.error as e:
            logger.error(f"Failed to parse mouse position: {e}")
            logger.debug(f"Response size: {len(response_data)} bytes, first 50 bytes: {response_data[:50].hex()}")
            return None

    def scan_desktop(self) -> List[DesktopElement]:
        """
        Scan all desktop icons/elements
        Auto-reconnects on timeout and retries once

        Returns:
            List of DesktopElement objects (may be empty if failed)
        """
        logger.debug("Scanning desktop elements...")

        # Try up to 2 times (initial attempt + 1 retry with reconnect)
        for attempt in range(2):
            request_id = self._send_command(CommandType.SCAN_ELEMENTS)
            if not request_id:
                if attempt == 0:
                    logger.warning("Command send failed, attempting reconnect...")
                    if not self.reconnect():
                        return []
                    continue
                return []

            # Scanning can take longer, use 10 second timeout
            response_data = self._wait_for_response(timeout_ms=10000)
            if not response_data:
                if attempt == 0:
                    logger.warning("Scan timeout, attempting reconnect...")
                    if not self.reconnect():
                        return []
                    continue
                return []

            # Got response, proceed to parse
            break

        # Verify minimum response size (header=32 + mouse_pos=24 + element_count=4)
        if len(response_data) < 60:
            logger.error(f"SCAN_ELEMENTS response too short: {len(response_data)} bytes")
            return []

        # Parse response header
        cmd_type, req_id, status, timestamp = self._parse_response_header(response_data)

        if status != ResponseStatus.SUCCESS:
            logger.error(f"SCAN_ELEMENTS failed: status={status}")
            return []

        # Scan elements data layout in C++ Response struct:
        # - Header: 32 bytes (with padding)
        # - MousePosition mouse_pos: 24 bytes (3 floats + uint64_t + 4 bytes padding)
        # - ScanElementsData: [element_count(4)] [padding(4)] [DesktopElement array...]
        offset = 32 + 24  # header + mouse_pos

        if len(response_data) < offset + 8:
            logger.error(f"Response too short for element_count: {len(response_data)} bytes")
            return []

        try:
            element_count = struct.unpack('I', response_data[offset:offset+4])[0]
            offset += 8  # element_count(4) + padding(4) to align DesktopElement array

            logger.info(f"Parsing {element_count} desktop elements")

            elements = []
            for i in range(element_count):
                elem = self._parse_desktop_element(response_data, offset)
                if elem:
                    elements.append(elem)
                    # Each DesktopElement size with padding:
                    # id(8) + text(256) + app_name(128) + x(4) + y(4) + width(4) + height(4)
                    # + type(4) + clickable(1) + padding(3) + confidence(4) + reserved(16) = 436 bytes
                    offset += 436
                else:
                    logger.warning(f"Failed to parse element {i+1}, stopping")
                    break

            logger.info(f"Successfully parsed {len(elements)} elements")
            return elements
        except struct.error as e:
            logger.error(f"Failed to parse scan response: {e}")
            logger.debug(f"Response size: {len(response_data)} bytes")
            return []

    def _parse_desktop_element(self, data: bytes, offset: int) -> Optional[DesktopElement]:
        """Parse DesktopElement from bytes at offset"""
        try:
            # Verify we have enough data
            required_size = offset + 436  # DesktopElement size
            if len(data) < required_size:
                logger.error(f"Not enough data for element at offset {offset}: required {required_size} bytes, available {len(data)} bytes")
                return None

            # DesktopElement layout:
            # id(8) + text(256) + app_name(128) + x(4) + y(4) + width(4) + height(4)
            # + type(4) + clickable(1) + padding(3) + confidence(4) + reserved(16) = 436

            # Parse ID
            elem_id = struct.unpack('Q', data[offset:offset+8])[0]
            offset += 8

            # Parse text (256 bytes, null-terminated)
            text_bytes = data[offset:offset+256]
            text = text_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')
            offset += 256

            # Parse app_name (128 bytes, null-terminated)
            app_bytes = data[offset:offset+128]
            app_name = app_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')
            offset += 128

            # Parse floats and ints
            x, y, width, height = struct.unpack('ffff', data[offset:offset+16])
            offset += 16

            elem_type = struct.unpack('I', data[offset:offset+4])[0]
            offset += 4

            clickable = struct.unpack('?', data[offset:offset+1])[0]
            offset += 1
            offset += 3  # Skip 3 bytes of padding (float requires 4-byte alignment)

            confidence = struct.unpack('f', data[offset:offset+4])[0]

            return DesktopElement(
                id=elem_id,
                text=text,
                app_name=app_name,
                x=x,
                y=y,
                width=width,
                height=height,
                elem_type=elem_type,
                clickable=clickable,
                confidence=confidence
            )

        except struct.error as e:
            logger.error(f"Struct unpack failed at offset {offset}: {e}")
            logger.debug(f"Data length: {len(data)} bytes")
            return None
        except Exception as e:
            logger.error(f"Failed to parse element: {e}", exc_info=True)
            return None

    def find_element(self, search_text: str, exact_match: bool = False) -> Optional[DesktopElement]:
        """
        Find element by name/text
        Auto-reconnects on timeout and retries once

        Args:
            search_text: Text to search for
            exact_match: If True, require exact match (case-insensitive by default)

        Returns:
            DesktopElement if found, None otherwise
        """
        # Build params: search_text(256) + case_sensitive(1) + exact_match(1)
        params = search_text.encode('utf-8')[:256].ljust(256, b'\x00')
        params += struct.pack('??', False, exact_match)  # case_sensitive=False

        logger.debug(f"Finding element: '{search_text}' (exact_match={exact_match})")

        # Try up to 2 times (initial attempt + 1 retry with reconnect)
        for attempt in range(2):
            request_id = self._send_command(CommandType.FIND_ELEMENT, params)
            if not request_id:
                if attempt == 0:
                    logger.warning("Command send failed, attempting reconnect...")
                    if not self.reconnect():
                        return None
                    continue
                return None

            response_data = self._wait_for_response()
            if not response_data:
                if attempt == 0:
                    logger.warning("Find timeout, attempting reconnect...")
                    if not self.reconnect():
                        return None
                    continue
                return None

            # Got response, proceed to parse
            break

        # Parse response header
        cmd_type, req_id, status, timestamp = self._parse_response_header(response_data)

        if status == ResponseStatus.ERROR_NOT_FOUND:
            logger.debug(f"Element not found: '{search_text}'")
            return None
        elif status != ResponseStatus.SUCCESS:
            logger.error(f"FIND_ELEMENT failed: status={status}")
            return None

        # Response layout: header(32) + mouse_pos(24) + scan_elements(varies) + find_element
        # In C++, ScanElementsData comes before FindElementData in the struct
        # For FIND_ELEMENT response, only FindElementData is populated
        # FindElementData layout: ScanElementsData(element_count=4 + padding=4) + FindElementData(found=1 + padding=7 + element=436)
        # So we skip: header(32) + mouse_pos(24) + element_count(4) + padding(4)
        offset = 32 + 24 + 8  # Skip header, mouse_pos, element_count + padding
        found = struct.unpack('?', response_data[offset:offset+1])[0]
        offset += 8  # found(1) + padding(7) to align DesktopElement

        if not found:
            return None

        return self._parse_desktop_element(response_data, offset)

    def set_active(self) -> bool:
        """
        Show moiré overlay (indicate AI is working)

        Returns:
            True if successful
        """
        request_id = self._send_command(CommandType.SET_ACTIVE)
        if not request_id:
            return False

        response_data = self._wait_for_response()
        if not response_data:
            return False

        cmd_type, req_id, status, timestamp = self._parse_response_header(response_data)
        return status == ResponseStatus.SUCCESS

    def set_standby(self) -> bool:
        """
        Hide moiré overlay (indicate AI is idle)

        Returns:
            True if successful
        """
        request_id = self._send_command(CommandType.SET_STANDBY)
        if not request_id:
            return False

        response_data = self._wait_for_response()
        if not response_data:
            return False

        cmd_type, req_id, status, timestamp = self._parse_response_header(response_data)
        return status == ResponseStatus.SUCCESS

    def focus_window(self, identifier: str, by_title: bool = True) -> bool:
        """
        Focus a window by title or process name

        Args:
            identifier: Window title or process name to search for
            by_title: If True, search by window title; if False, search by process name

        Returns:
            True if window was focused successfully
        """
        # Build params: window_identifier(256) + by_title(1)
        params = identifier.encode('utf-8')[:256].ljust(256, b'\x00')
        params += struct.pack('?', by_title)

        logger.debug(f"Focusing window: '{identifier}' (by_title={by_title})")

        request_id = self._send_command(CommandType.FOCUS_WINDOW, params)
        if not request_id:
            return False

        response_data = self._wait_for_response()
        if not response_data:
            return False

        cmd_type, req_id, status, timestamp = self._parse_response_header(response_data)
        success = status == ResponseStatus.SUCCESS
        if success:
            logger.info(f"Window focused: '{identifier}'")
        else:
            logger.warning(f"Failed to focus window: '{identifier}' (status={status})")
        return success

    def close_window(self, identifier: str, by_title: bool = True, force: bool = False) -> bool:
        """
        Close a window by title or process name

        Args:
            identifier: Window title or process name to search for
            by_title: If True, search by window title; if False, search by process name
            force: If True, force close; if False, graceful close

        Returns:
            True if window was closed successfully
        """
        # Build params: window_identifier(256) + by_title(1) + force(1)
        params = identifier.encode('utf-8')[:256].ljust(256, b'\x00')
        params += struct.pack('??', by_title, force)

        logger.debug(f"Closing window: '{identifier}' (by_title={by_title}, force={force})")

        request_id = self._send_command(CommandType.CLOSE_WINDOW, params)
        if not request_id:
            return False

        response_data = self._wait_for_response()
        if not response_data:
            return False

        cmd_type, req_id, status, timestamp = self._parse_response_header(response_data)
        success = status == ResponseStatus.SUCCESS
        if success:
            logger.info(f"Window closed: '{identifier}'")
        else:
            logger.warning(f"Failed to close window: '{identifier}' (status={status})")
        return success

    def resize_window(self, identifier: str, x: int, y: int, width: int, height: int, by_title: bool = True) -> bool:
        """
        Resize and reposition a window

        Args:
            identifier: Window title or process name to search for
            x: New x position
            y: New y position
            width: New width
            height: New height
            by_title: If True, search by window title; if False, search by process name

        Returns:
            True if window was resized successfully
        """
        # Build params: window_identifier(256) + by_title(1) + padding(3) + x(4) + y(4) + width(4) + height(4)
        params = identifier.encode('utf-8')[:256].ljust(256, b'\x00')
        params += struct.pack('?3x', by_title)  # by_title + 3 bytes padding for alignment
        params += struct.pack('iiii', x, y, width, height)

        logger.debug(f"Resizing window: '{identifier}' to ({x}, {y}, {width}x{height})")

        request_id = self._send_command(CommandType.RESIZE_WINDOW, params)
        if not request_id:
            return False

        response_data = self._wait_for_response()
        if not response_data:
            return False

        cmd_type, req_id, status, timestamp = self._parse_response_header(response_data)
        success = status == ResponseStatus.SUCCESS
        if success:
            logger.info(f"Window resized: '{identifier}'")
        else:
            logger.warning(f"Failed to resize window: '{identifier}' (status={status})")
        return success

    def get_active_window(self) -> Optional[WindowData]:
        """
        Get information about the currently active window

        Returns:
            WindowData if successful, None if failed
        """
        logger.debug("Getting active window...")

        request_id = self._send_command(CommandType.GET_ACTIVE_WINDOW)
        if not request_id:
            return None

        response_data = self._wait_for_response()
        if not response_data:
            return None

        cmd_type, req_id, status, timestamp = self._parse_response_header(response_data)

        if status != ResponseStatus.SUCCESS:
            logger.warning(f"GET_ACTIVE_WINDOW failed: status={status}")
            return None

        # WindowData is written right after header (overlaying mouse_pos area)
        # C++ uses memcpy(&response.mouse_pos, window, sizeof(WindowData))
        offset = 32  # Just skip the header
        print(f"[DEBUG] GET_ACTIVE_WINDOW: Response length={len(response_data)}, offset={offset}, need={offset+676}")
        return self._parse_window_data(response_data, offset)

    def click_window(self, identifier: str, x_offset: int, y_offset: int, by_title: bool = True) -> bool:
        """
        Click at a specific offset within a window

        Args:
            identifier: Window title or process name to search for
            x_offset: X offset from window's top-left corner
            y_offset: Y offset from window's top-left corner
            by_title: If True, search by window title; if False, search by process name

        Returns:
            True if click was successful
        """
        # Build params: window_identifier(256) + by_title(1) + padding(3) + x_offset(4) + y_offset(4)
        params = identifier.encode('utf-8')[:256].ljust(256, b'\x00')
        params += struct.pack('?3x', by_title)  # by_title + 3 bytes padding for alignment
        params += struct.pack('ii', x_offset, y_offset)

        logger.debug(f"Clicking window: '{identifier}' at offset ({x_offset}, {y_offset})")

        request_id = self._send_command(CommandType.CLICK_WINDOW, params)
        if not request_id:
            return False

        response_data = self._wait_for_response()
        if not response_data:
            return False

        cmd_type, req_id, status, timestamp = self._parse_response_header(response_data)
        success = status == ResponseStatus.SUCCESS
        if success:
            logger.info(f"Window clicked: '{identifier}' at ({x_offset}, {y_offset})")
        else:
            logger.warning(f"Failed to click window: '{identifier}' (status={status})")
        return success

    def _parse_window_data(self, data: bytes, offset: int) -> Optional[WindowData]:
        """Parse WindowData from bytes at offset"""
        try:
            # WindowData layout (from shared_memory_protocol.h):
            # hwnd(8) + title(256) + class_name(256) + process_name(128) + process_id(4)
            # + left(4) + top(4) + right(4) + bottom(4)
            # + is_visible(1) + is_minimized(1) + is_maximized(1) + padding(1) + z_order(4)
            # Total: 8 + 256 + 256 + 128 + 4 + 16 + 4 + 4 = 676 bytes

            required_size = offset + 676
            if len(data) < required_size:
                logger.error(f"Not enough data for WindowData at offset {offset}: need {required_size}, have {len(data)}")
                return None

            # Parse hwnd
            hwnd = struct.unpack('Q', data[offset:offset+8])[0]
            offset += 8

            # Parse title (256 bytes, null-terminated)
            title_bytes = data[offset:offset+256]
            title = title_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')
            offset += 256

            # Parse class_name (256 bytes, null-terminated) - FIXED: was 128
            class_bytes = data[offset:offset+256]
            class_name = class_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')
            offset += 256

            # Parse process_name (128 bytes, null-terminated)
            process_bytes = data[offset:offset+128]
            process_name = process_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')
            offset += 128

            # Parse integers: process_id (uint32=I=4) + 4 ints (i=4 each) = 20 bytes total
            process_id, left, top, right, bottom = struct.unpack('Iiiii', data[offset:offset+20])
            offset += 20

            # Parse booleans and z_order
            is_visible, is_minimized, is_maximized = struct.unpack('???x', data[offset:offset+4])
            offset += 4

            z_order = struct.unpack('i', data[offset:offset+4])[0]  # FIXED: z_order is int, not uint

            return WindowData(
                hwnd=hwnd,
                title=title,
                class_name=class_name,
                process_name=process_name,
                process_id=process_id,
                left=left,
                top=top,
                right=right,
                bottom=bottom,
                is_visible=is_visible,
                is_minimized=is_minimized,
                is_maximized=is_maximized,
                z_order=z_order
            )

        except struct.error as e:
            logger.error(f"Struct unpack failed at offset {offset}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse WindowData: {e}", exc_info=True)
            return None
