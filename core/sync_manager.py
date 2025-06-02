import os
import json
import time
from datetime import datetime, timedelta, timezone # Added timezone

from typing import Optional, Union # Added for Optional type hints

# Try to import QMessageBox for stale lock prompting, but make it optional
try:
    from PySide6.QtWidgets import QMessageBox
    _QMESSAGEBOX_AVAILABLE = True
except ImportError:
    _QMESSAGEBOX_AVAILABLE = False
    QMessageBox = None # Placeholder

# For type hinting if needed, e.g.:
# from .credential_manager import CredentialManager

class DatabaseLockManager:
    def __init__(self, db_path_str: str, credential_manager, logger_callable=None): # Type hint: credential_manager: CredentialManager
        self.db_path_str = db_path_str
        self.credential_manager = credential_manager
        self.logger = logger_callable
        self.lock_file_path = None
        self._current_lock_info_cache = None

        if not self.db_path_str or not os.path.basename(self.db_path_str):
            self._log("Database path is invalid or empty.", "error")
            self.db_path_str = None
        else:
            db_dir = os.path.dirname(self.db_path_str)
            if not db_dir:
                # This means db_path_str is a relative path for a file in the current working directory.
                # The lock file should also be in the current working directory.
                db_dir = "."
            db_name = os.path.basename(self.db_path_str)
            self.lock_file_path = os.path.join(db_dir, f"{db_name}.lock")

    def _log(self, message, level='info'):
        if self.logger:
            self.logger(message, level)
        else:
            print(f"DBLockManager: [{level.upper()}] {message}")

    def _get_lock_file_path(self) -> str | None:
        return self.lock_file_path

    def get_current_lock_info(self) -> dict | None:
        if not self.lock_file_path:
            self._log("No lock file path configured (db_path_str might have been invalid).", "info")
            return None
        try:
            if os.path.exists(self.lock_file_path):
                with open(self.lock_file_path, 'r') as f:
                    return json.load(f)
            return None # File doesn't exist, so no lock info
        except (IOError, json.JSONDecodeError) as e:
            self._log(f"Error reading lock file for info ('{self.lock_file_path}'): {e}", "error")
            return None # Corrupt or unreadable

    def acquire_lock(self, expected_duration_seconds: int, operation_description: str) -> str | bool:
        self._current_lock_info_cache = None
        if not self.lock_file_path:
            self._log("Lock manager not properly initialized (no lock file path).", "error")
            return "ERROR"
        if not self.credential_manager:
            self._log("CredentialManager not available.", "error")
            return "ERROR"

        current_device_id = self.credential_manager.get_device_id()
        current_device_nickname = self.credential_manager.get_device_nickname()

        if not current_device_id or not current_device_nickname:
            self._log("Device ID or Nickname not available from CredentialManager.", "error")
            return "ERROR"

        grace_period_seconds = 60

        try:
            if os.path.exists(self.lock_file_path):
                lock_data = None
                try:
                    with open(self.lock_file_path, 'r') as f:
                        lock_data = json.load(f)
                    self._current_lock_info_cache = lock_data
                except (IOError, json.JSONDecodeError) as e:
                    self._log(f"Could not read or parse existing lock file '{self.lock_file_path}': {e}. Assuming stale.", "warning")
                    return "STALE_LOCK_DETECTED"

                holder_device_id = lock_data.get('holder_device_id')
                heartbeat_time_iso_str = lock_data.get('heartbeat_time_iso')
                expected_duration_from_file = lock_data.get('expected_duration_seconds')

                if holder_device_id == current_device_id:
                    self._log(f"Lock already held by this device ('{current_device_nickname}'). Updating heartbeat and operation.", "warning")
                    lock_data['heartbeat_time_iso'] = datetime.now(timezone.utc).isoformat() # Use timezone.utc
                    lock_data['operation_description'] = operation_description
                    lock_data['expected_duration_seconds'] = expected_duration_seconds
                    try:
                        with open(self.lock_file_path, 'w') as f:
                            json.dump(lock_data, f, indent=4)
                        self._current_lock_info_cache = lock_data
                        self._log(f"DB lock re-confirmed (heartbeat updated): {self.lock_file_path} by device {current_device_id}", "info")
                        return True
                    except IOError as e_write:
                        self._log(f"Failed to update existing lock file: {e_write}", "error")
                        return "ERROR"

                if heartbeat_time_iso_str and expected_duration_from_file is not None:
                    try:
                        heartbeat_dt = datetime.fromisoformat(heartbeat_time_iso_str)
                        if heartbeat_dt.tzinfo is None: heartbeat_dt = heartbeat_dt.replace(tzinfo=timezone.utc) # Make tz-aware
                        if datetime.now(timezone.utc) > (heartbeat_dt + timedelta(seconds=(expected_duration_from_file + grace_period_seconds))): # Use timezone.utc
                            self._log(f"Stale lock detected. Held by {lock_data.get('holder_nickname', 'Unknown')}. Last heartbeat: {heartbeat_time_iso_str}", "info")
                            return "STALE_LOCK_DETECTED"
                    except ValueError:
                        self._log(f"Could not parse heartbeat timestamp '{heartbeat_time_iso_str}'. Assuming stale.", "warning")
                        return "STALE_LOCK_DETECTED"
                else:
                    self._log("Lock file missing heartbeat or expected_duration. Assuming stale.", "warning")
                    return "STALE_LOCK_DETECTED"

                self._log(f"Lock held by another user: {lock_data.get('holder_nickname', 'Unknown')} for operation '{lock_data.get('operation_description', 'Unknown Op')}'", "info")
                return False

            # If lock file does not exist, create it
            new_lock_data = {
                'holder_device_id': current_device_id,
                'holder_nickname': current_device_nickname,
                'start_time_iso': datetime.now(timezone.utc).isoformat(), # Use timezone.utc
                'expected_duration_seconds': expected_duration_seconds,
                'operation_description': operation_description,
                'heartbeat_time_iso': datetime.now(timezone.utc).isoformat() # Use timezone.utc
            }
            with open(self.lock_file_path, 'w') as f:
                json.dump(new_lock_data, f, indent=4)
            self._current_lock_info_cache = new_lock_data
            self._log(f"DB lock acquired: {self.lock_file_path} by device {current_device_id}", "info")
            return True

        except IOError as e:
            self._log(f"IOError during acquire_lock ('{self.lock_file_path}'): {e}", "error")
            return "ERROR"
        except Exception as e_unhandled:
            self._log(f"Unexpected error in acquire_lock: {e_unhandled}", "error")
            return "ERROR"

    def force_acquire_lock(self, expected_duration_seconds: int, operation_description: str) -> bool:
        if not self.lock_file_path:
            self._log("Lock manager not properly initialized.", "error")
            return False

        current_device_id = self.credential_manager.get_device_id()
        current_device_nickname = self.credential_manager.get_device_nickname()
        if not current_device_id or not current_device_nickname:
            self._log("Device ID or Nickname not available.", "error")
            return False

        try:
            if os.path.exists(self.lock_file_path):
                os.remove(self.lock_file_path)
                self._log(f"Removed existing lock file ('{self.lock_file_path}') for force acquire by {current_device_nickname}.", "info")

            new_lock_data = {
                'holder_device_id': current_device_id,
                'holder_nickname': current_device_nickname,
                'start_time_iso': datetime.now(timezone.utc).isoformat(), # Use timezone.utc
                'expected_duration_seconds': expected_duration_seconds,
                'operation_description': operation_description,
                'heartbeat_time_iso': datetime.now(timezone.utc).isoformat() # Use timezone.utc
            }
            with open(self.lock_file_path, 'w') as f:
                json.dump(new_lock_data, f, indent=4)
            self._current_lock_info_cache = new_lock_data
            self._log(f"DB lock forcibly acquired: {self.lock_file_path} by device {current_device_id}", "warning")
            return True
        except (IOError, OSError) as e:
            self._log(f"Failed to remove or create lock file ('{self.lock_file_path}'): {e}", "error")
            return False
        except Exception as e_unhandled:
            self._log(f"Unexpected error in force_acquire_lock: {e_unhandled}", "error")
            return False

    def release_lock(self) -> bool:
        if not self.lock_file_path:
            self._log("No lock file path configured. Assuming released.", "warning")
            return True

        current_device_id = self.credential_manager.get_device_id()
        if not current_device_id:
            self._log("Cannot verify current device ID to release lock.", "error")
            return False

        try:
            if os.path.exists(self.lock_file_path):
                lock_data_on_release = None
                try:
                    with open(self.lock_file_path, 'r') as f:
                        lock_data_on_release = json.load(f)
                except (IOError, json.JSONDecodeError) as e:
                    self._log(f"Could not read lock file '{self.lock_file_path}' during release: {e}.", "warning")
                    if self._current_lock_info_cache and self._current_lock_info_cache.get('holder_device_id') == current_device_id:
                        self._log("Lock file unreadable but cache indicates current device owns it. Attempting removal.", "info")
                    else:
                        self._log("Lock file unreadable and no cached ownership by this device. Not removing.", "warning")
                        return False

                if lock_data_on_release and lock_data_on_release.get('holder_device_id') == current_device_id:
                    os.remove(self.lock_file_path)
                    self._log(f"DB lock released: {self.lock_file_path} by device {current_device_id}", "info")
                    self._current_lock_info_cache = None
                    return True
                elif lock_data_on_release:
                    self._log(f"Attempt to release lock on '{self.lock_file_path}' held by {lock_data_on_release.get('holder_nickname', 'Unknown')}. Not released by {self.credential_manager.get_device_nickname()}.", "warning")
                    return False
                else: # Unreadable lock file, but cache might allow release
                    if self._current_lock_info_cache and self._current_lock_info_cache.get('holder_device_id') == current_device_id:
                         os.remove(self.lock_file_path)
                         self._log(f"DB lock released: {self.lock_file_path} by device {current_device_id} (based on cache after read fail).", "info")
                         self._current_lock_info_cache = None
                         return True
                    self._log(f"Lock file '{self.lock_file_path}' was unreadable and not confirmed owned by cache.", "warning")
                    return False
            else: # Lock file does not exist
                self._log(f"DB lock release attempted but no lock file found: {self.lock_file_path}", "debug")
                self._current_lock_info_cache = None
                return True
        except (IOError, OSError) as e:
            self._log(f"Failed to remove lock file '{self.lock_file_path}': {e}", "error")
            return False
        except Exception as e_unhandled:
            self._log(f"Unexpected error in release_lock: {e_unhandled}", "error")
            return False
        return False


    def update_heartbeat(self) -> bool:
        if not self.lock_file_path or not os.path.exists(self.lock_file_path):
            self._log(f"Lock file '{self.lock_file_path}' not found.", "warning")
            return False

        current_device_id = self.credential_manager.get_device_id()
        if not current_device_id:
            self._log("Device ID not available.", "error")
            return False

        try:
            with open(self.lock_file_path, 'r+') as f:
                lock_data = json.load(f)
                if lock_data.get('holder_device_id') == current_device_id:
                    lock_data['heartbeat_time_iso'] = datetime.now(timezone.utc).isoformat() # Use timezone.utc
                    f.seek(0)
                    json.dump(lock_data, f, indent=4)
                    f.truncate()
                    self._current_lock_info_cache = lock_data
                    # self._log(f"Heartbeat updated by {self.credential_manager.get_device_nickname()}.", "debug") # Can be too verbose
                    return True
                else:
                    self._log(f"Attempt to update heartbeat for lock on '{self.lock_file_path}' held by {lock_data.get('holder_nickname','Unknown')}. Denied for {self.credential_manager.get_device_nickname()}.", "warning")
                    return False
        except (IOError, json.JSONDecodeError) as e:
            self._log(f"Failed to read/write lock file '{self.lock_file_path}': {e}", "error")
            return False
        except Exception as e_unhandled:
            self._log(f"Unexpected error in update_heartbeat: {e_unhandled}", "error")
            return False

# --- Mock CredentialManager for testing (if needed directly in this file) ---
# This part is for standalone testing of the module and is good practice to keep.
class MockCredentialManager:
    def __init__(self, device_id="test_dev_id", nickname="TestDevice"):
        self._device_id = device_id
        self._device_nickname = nickname
    def get_device_id(self): return self._device_id
    def get_device_nickname(self): return self._device_nickname


# --- KMLFileLockManager Class ---
from pathlib import Path
from typing import Optional, Union
# Assuming CredentialManager would be imported from a module like core.credential_manager
# For now, we'll use a forward reference string 'CredentialManager' if needed for type hints
# or rely on the MockCredentialManager structure.

class KMLFileLockManager:
    def __init__(self, kml_folder_path_str: str, credential_manager, logger_callable=None): # credential_manager: 'CredentialManager'
        self.kml_folder_path = Path(kml_folder_path_str) if kml_folder_path_str else None # Handle None path
        self.credential_manager = credential_manager
        self.logger = logger_callable
        self.STALE_LOCK_GRACE_PERIOD_SECONDS: int = 300
        self.DEFAULT_KML_LOCK_DURATION_SECONDS: int = 300

        if not self.kml_folder_path.is_dir():
            try:
                self.kml_folder_path.mkdir(parents=True, exist_ok=True)
                self._log(f"KML folder created at {self.kml_folder_path}", "info")
            except OSError as e:
                self._log(f"Could not create KML folder at {self.kml_folder_path}: {e}", "error")
                # Potentially raise an error or set a state indicating failure
                # For now, path operations will likely fail if dir doesn't exist.

    def _log(self, message, level='info'):
        if self.logger:
            self.logger(message, level)
        else:
            # Fallback to print if no logger is provided
            print(f"KMLFileLockManager: [{level.upper()}] {message}")

    def _get_lock_file_path(self, kml_filename: str) -> Path:
        """Constructs and returns the full path for a KML lock file."""
        if not self.kml_folder_path: return None # Return None if base path is None
        return self.kml_folder_path / f"{kml_filename}.lock"

    def acquire_kml_lock(self, kml_filename: str, operation_description: str = "KML file operation",
                         expected_duration_seconds: Optional[int] = None) -> Union[bool, str]:
        lock_file_path = self._get_lock_file_path(kml_filename)
        if not lock_file_path: # Check if path construction failed
            self._log("KML folder path not configured for lock file.", "error")
            return "ERROR"
        effective_duration_seconds = expected_duration_seconds if expected_duration_seconds is not None else self.DEFAULT_KML_LOCK_DURATION_SECONDS

        current_device_id = self.credential_manager.get_device_id()
        current_device_nickname = self.credential_manager.get_device_nickname()

        if not current_device_id or not current_device_nickname:
            self._log("Device ID or Nickname not available.", "error")
            return "ERROR"

        try:
            if lock_file_path.exists():
                lock_data = None
                try:
                    with open(lock_file_path, 'r') as f:
                        lock_data = json.load(f)
                except (IOError, json.JSONDecodeError) as e:
                    self._log(f"Could not read/parse lock file '{lock_file_path}': {e}. Assuming stale.", "warning")
                    return "STALE_LOCK_DETECTED"

                holder_device_id = lock_data.get('holder_device_id')
                heartbeat_time_iso_str = lock_data.get('heartbeat_time_iso')
                lock_expected_duration = lock_data.get('expected_duration_seconds', self.DEFAULT_KML_LOCK_DURATION_SECONDS)

                if holder_device_id == current_device_id:
                    self._log(f"Lock for '{kml_filename}' already held by this device ('{current_device_nickname}'). Updating.", "info")
                    if self.update_kml_heartbeat(kml_filename,
                                                 new_operation_description=operation_description,
                                                 new_expected_duration=effective_duration_seconds):
                        # Log specific re-confirmation message
                        self._log(f"KML lock re-confirmed (heartbeat updated) for '{kml_filename}': {lock_file_path} by device {current_device_id}", "info")
                        return True
                    else:
                        # update_kml_heartbeat would have logged the error
                        return "ERROR" # Failed to update existing lock

                if heartbeat_time_iso_str:
                    try:
                        heartbeat_dt = datetime.fromisoformat(heartbeat_time_iso_str)
                        if heartbeat_dt.tzinfo is None:
                             heartbeat_dt = heartbeat_dt.replace(tzinfo=timezone.utc)

                        staleness_threshold = heartbeat_dt + timedelta(seconds=(lock_expected_duration + self.STALE_LOCK_GRACE_PERIOD_SECONDS))
                        if staleness_threshold < datetime.now(timezone.utc):
                            holder_nickname = lock_data.get('holder_nickname', 'Unknown Device')
                            self._log(f"Stale lock for '{kml_filename}' detected. Held by {holder_nickname}. Last heartbeat: {heartbeat_time_iso_str}", "info")
                            return "STALE_LOCK_DETECTED"
                    except ValueError:
                        self._log(f"Could not parse heartbeat timestamp '{heartbeat_time_iso_str}' for '{kml_filename}'. Assuming stale.", "warning")
                        return "STALE_LOCK_DETECTED"
                else:
                    self._log(f"Lock file for '{kml_filename}' missing heartbeat. Assuming stale.", "warning")
                    return "STALE_LOCK_DETECTED"

                holder_nickname = lock_data.get('holder_nickname', "Unknown Device")
                self._log(f"Lock for '{kml_filename}' is busy. Held by {holder_nickname}.", "info")
                return False # Busy

            else: # Lock file does not exist, create it
                new_lock_data = {
                    'holder_device_id': current_device_id,
                    'holder_nickname': current_device_nickname,
                    'start_time_iso': datetime.now(timezone.utc).isoformat(),
                    'expected_duration_seconds': effective_duration_seconds,
                    'operation_description': operation_description,
                    'heartbeat_time_iso': datetime.now(timezone.utc).isoformat()
                }
                with open(lock_file_path, 'w') as f:
                    json.dump(new_lock_data, f, indent=4)
                self._log(f"KML lock acquired for '{kml_filename}': {lock_file_path} by device {current_device_id}", "info")
                return True

        except IOError as e:
            self._log(f"IOError during acquire_kml_lock for '{kml_filename}': {e}", "error")
            return "ERROR"
        except Exception as e_unhandled:
            self._log(f"Unexpected error in acquire_kml_lock for '{kml_filename}': {e_unhandled}", "error")
            return "ERROR"

    def force_acquire_kml_lock(self, kml_filename: str, operation_description: str = "KML file operation",
                               expected_duration_seconds: Optional[int] = None) -> bool:
        lock_file_path = self._get_lock_file_path(kml_filename)
        if not lock_file_path:
            self._log("KML folder path not configured for lock file (force acquire).", "error")
            return False
        effective_duration_seconds = expected_duration_seconds if expected_duration_seconds is not None else self.DEFAULT_KML_LOCK_DURATION_SECONDS

        current_device_id = self.credential_manager.get_device_id()
        current_device_nickname = self.credential_manager.get_device_nickname()

        if not current_device_id or not current_device_nickname:
            self._log("Device ID or Nickname not available for force_acquire.", "error")
            return False

        try:
            if lock_file_path.exists():
                try:
                    os.remove(lock_file_path)
                    self._log(f"Removed existing lock file '{lock_file_path}' for force acquire by {current_device_nickname}.", "info")
                except OSError as e_remove:
                    self._log(f"Failed to remove existing lock file '{lock_file_path}' for force_acquire: {e_remove}", "error")
                    return False

            new_lock_data = {
                'holder_device_id': current_device_id,
                'holder_nickname': current_device_nickname,
                'start_time_iso': datetime.now(timezone.utc).isoformat(),
                'expected_duration_seconds': effective_duration_seconds,
                'operation_description': operation_description,
                'heartbeat_time_iso': datetime.now(timezone.utc).isoformat()
            }
            with open(lock_file_path, 'w') as f:
                json.dump(new_lock_data, f, indent=4)
            self._log(f"KML lock forcibly acquired for '{kml_filename}': {lock_file_path} by device {current_device_id}", "warning")
            return True
        except IOError as e:
            self._log(f"IOError during force_acquire_kml_lock for '{kml_filename}': {e}", "error")
            return False
        except Exception as e_unhandled:
            self._log(f"Unexpected error in force_acquire_kml_lock for '{kml_filename}': {e_unhandled}", "error")
            return False

    def release_kml_lock(self, kml_filename: str) -> bool:
        lock_file_path = self._get_lock_file_path(kml_filename)
        if not lock_file_path: # Check if path construction failed
            self._log("KML folder path not configured for lock file (release).", "warning")
            return True # Consistent with original logic for DB lock if path is None
        current_device_id = self.credential_manager.get_device_id()
        action_taken = False

        if not current_device_id:
            self._log("Device ID not available. Cannot verify ownership to release KML lock.", "error")
            return False

        try:
            if lock_file_path.exists():
                lock_data = None
                try:
                    with open(lock_file_path, 'r') as f:
                        lock_data = json.load(f)
                except (IOError, json.JSONDecodeError) as e:
                    self._log(f"Could not read/parse lock file '{lock_file_path}' during release: {e}. Cannot verify ownership.", "warning")
                    # No explicit return False here, will fall through to "no action taken" log if file still exists

                if lock_data and lock_data.get('holder_device_id') == current_device_id:
                    try:
                        os.remove(lock_file_path)
                        self._log(f"KML lock released for '{kml_filename}': {lock_file_path} by device {current_device_id}", "info")
                        action_taken = True
                        return True
                    except OSError as e_remove:
                        self._log(f"Failed to remove owned KML lock file '{lock_file_path}': {e_remove}", "error")
                        return False # Explicit failure to remove
                elif lock_data : # Lock exists but not owned by current device
                    holder_nickname = lock_data.get('holder_nickname', 'another device')
                    current_nickname = self.credential_manager.get_device_nickname()
                    self._log(f"{current_nickname} attempted to release KML lock for '{kml_filename}' held by {holder_nickname} (ID: {lock_data.get('holder_device_id')}). Denied.", "warning")
                    # This is a "no action taken" scenario from the perspective of this device's ownership.
                    # Per strict interpretation of original prompt: return False
                    return False

            # If action_taken is still False here, it means:
            # 1. Lock file didn't exist initially.
            # 2. Lock file existed but was unreadable (lock_data remained None).
            # 3. Lock file existed, was readable, but not owned (already handled by returning False above).
            # The specific log for "not found or not owned" should cover cases 1 and 2 primarily.
            if not action_taken:
                 self._log(f"KML lock release: No action taken for '{kml_filename}' (not found, unreadable, or not owned by {current_device_id}). Path: {lock_file_path}", "debug")
            return True # True if lock didn't exist, or if it wasn't ours (so no action needed that would return False earlier)

        except IOError as e: # Should be less likely now with specific error handling for open/remove
            self._log(f"IOError during release_kml_lock for '{kml_filename}': {e}", "error")
            return False
        except Exception as e_unhandled:
            self._log(f"Unexpected error in release_kml_lock for '{kml_filename}': {e_unhandled}", "error")
            return False


    def update_kml_heartbeat(self, kml_filename: str, new_operation_description: Optional[str] = None,
                             new_expected_duration: Optional[int] = None) -> bool:
        lock_file_path = self._get_lock_file_path(kml_filename)
        if not lock_file_path: # Check if path construction failed
            self._log("KML folder path not configured for lock file (heartbeat).", "warning")
            return False
        current_device_id = self.credential_manager.get_device_id()

        if not current_device_id:
            self._log("Device ID not available for KML heartbeat.", "error")
            return False

        try:
            if lock_file_path.exists():
                lock_data = None
                try:
                    with open(lock_file_path, 'r') as f:
                        lock_data = json.load(f)
                except (IOError, json.JSONDecodeError) as e:
                    self._log(f"Could not read/parse KML lock file '{lock_file_path}' for heartbeat: {e}", "error")
                    return False

                if lock_data.get('holder_device_id') == current_device_id:
                    lock_data['heartbeat_time_iso'] = datetime.now(timezone.utc).isoformat()
                    if new_operation_description is not None:
                        lock_data['operation_description'] = new_operation_description
                    if new_expected_duration is not None:
                        lock_data['expected_duration_seconds'] = new_expected_duration

                    try:
                        with open(lock_file_path, 'w') as f:
                            json.dump(lock_data, f, indent=4)
                        # self._log(f"KML Heartbeat updated for '{kml_filename}' by {self.credential_manager.get_device_nickname()}.", "debug") # Can be verbose
                        return True
                    except IOError as e_write:
                        self._log(f"Failed to write updated KML lock file '{lock_file_path}' for heartbeat: {e_write}", "error")
                        return False
                else:
                    holder_nickname = lock_data.get('holder_nickname', 'another device')
                    self._log(f"Attempt to update KML heartbeat for lock on '{kml_filename}' held by {holder_nickname}. Denied for {self.credential_manager.get_device_nickname()}.", "warning")
                    return False
            else:
                self._log(f"KML lock file '{lock_file_path}' not found for heartbeat update.", "warning")
                return False
        except IOError as e:
            self._log(f"IOError during update_kml_heartbeat for '{kml_filename}': {e}", "error")
            return False
        except Exception as e_unhandled:
            self._log(f"Unexpected error in update_kml_heartbeat for '{kml_filename}': {e_unhandled}", "error")
            return False

    def get_kml_lock_info(self, kml_filename: str) -> Optional[dict]:
        lock_file_path = self._get_lock_file_path(kml_filename)
        if not lock_file_path: return None # Check if path construction failed
        try:
            if lock_file_path.exists():
                with open(lock_file_path, 'r') as f:
                    return json.load(f)
            return None
        except (IOError, json.JSONDecodeError) as e:
            self._log(f"Error reading KML lock info for '{kml_filename}' from '{lock_file_path}': {e}", "error")
            return None
        except Exception as e_unhandled:
            self._log(f"Unexpected error in get_kml_lock_info for '{kml_filename}': {e_unhandled}", "error")
            return None


    def is_kml_locked(self, kml_filename: str) -> bool:
        lock_info = self.get_kml_lock_info(kml_filename)

        if not lock_info:
            return False

        holder_device_id = lock_info.get('holder_device_id')
        if holder_device_id == self.credential_manager.get_device_id():
            return False

        heartbeat_time_iso_str = lock_info.get('heartbeat_time_iso')
        lock_expected_duration = lock_info.get('expected_duration_seconds', self.DEFAULT_KML_LOCK_DURATION_SECONDS)

        if not heartbeat_time_iso_str:
            self._log(f"KML lock for '{kml_filename}' is malformed (missing heartbeat). Treating as not locked.", "warning")
            return False

        try:
            heartbeat_dt = datetime.fromisoformat(heartbeat_time_iso_str)
            if heartbeat_dt.tzinfo is None:
                heartbeat_dt = heartbeat_dt.replace(tzinfo=timezone.utc)

            staleness_threshold = heartbeat_dt + timedelta(seconds=(lock_expected_duration + self.STALE_LOCK_GRACE_PERIOD_SECONDS))
            if staleness_threshold < datetime.now(timezone.utc):
                # self._log(f"KML lock for '{kml_filename}' is stale (held by {lock_info.get('holder_nickname', 'Unknown')}).", "debug")
                return False
        except ValueError:
            self._log(f"Could not parse KML lock heartbeat for '{kml_filename}'. Treating as not locked.", "warning")
            return False

        # self._log(f"KML lock for '{kml_filename}' is actively held by {lock_info.get('holder_nickname', 'Unknown')}.", "debug")
        return True


if __name__ == '__main__':
    print("--- Testing DatabaseLockManager ---")
    # Setup a test directory for mock db and lock files
    test_dir = "test_lock_dir_sync_manager" # Unique name for this test run
    if not os.path.exists(test_dir):
        os.makedirs(test_dir, exist_ok=True)

    mock_db_file_path = os.path.join(test_dir, "test_db_for_lock.db")

    # Create a dummy db file if it doesn't exist
    if not os.path.exists(mock_db_file_path):
        with open(mock_db_file_path, 'w') as f_db:
            f_db.write("dummy database content")

    cm_user1 = MockCredentialManager("device_one_sync", "UserSyncOne")
    cm_user2 = MockCredentialManager("device_two_sync", "UserSyncTwo")

    # Example of passing a simple print-based logger
    test_logger = lambda msg, level: print(f"TEST_LOGGER: [{level.upper()}] {msg}")

    lock_manager_user1 = DatabaseLockManager(mock_db_file_path, cm_user1, logger_callable=test_logger)
    lock_manager_user2 = DatabaseLockManager(mock_db_file_path, cm_user2, logger_callable=test_logger)

    actual_lock_file = lock_manager_user1._get_lock_file_path()
    print(f"Actual lock file path for tests: {actual_lock_file}")

    # Ensure no old lock file from previous test runs
    if actual_lock_file and os.path.exists(actual_lock_file):
        os.remove(actual_lock_file)

    # Test 1: User1 acquires lock
    print("\n--- Test 1: User1 acquires lock ---")
    acq_status_u1 = lock_manager_user1.acquire_lock(60, "User1_Initial_Sync")
    assert acq_status_u1 is True, f"Test 1 Failed: User1 could not acquire lock. Status: {acq_status_u1}"
    assert os.path.exists(actual_lock_file), f"Test 1 Failed: Lock file '{actual_lock_file}' not created."
    print(f"Test 1 Passed. User1 acquired lock. Status: {acq_status_u1}")

    # Test 2: User2 tries to acquire (should be busy)
    print("\n--- Test 2: User2 tries to acquire (expect busy) ---")
    acq_status_u2_busy = lock_manager_user2.acquire_lock(30, "User2_Quick_Update")
    assert acq_status_u2_busy is False, f"Test 2 Failed: User2 should be busy. Status: {acq_status_u2_busy}"
    print(f"Test 2 Passed. User2 found lock busy. Status: {acq_status_u2_busy}")
    current_lock_holder_info = lock_manager_user2.get_current_lock_info() # From User2's perspective
    assert current_lock_holder_info is not None, "Test 2 Failed: Lock info should not be None for busy lock"
    assert current_lock_holder_info['holder_nickname'] == "UserSyncOne", "Test 2 Failed: Lock holder info mismatch."
    print(f"Lock correctly reported as held by: {current_lock_holder_info['holder_nickname']}")

    # Test 3: User1 updates heartbeat
    print("\n--- Test 3: User1 updates heartbeat ---")
    time.sleep(0.1) # Ensure timestamp can change if system clock resolution is low
    hb_status_u1 = lock_manager_user1.update_heartbeat()
    assert hb_status_u1 is True, "Test 3 Failed: User1 could not update heartbeat."
    print("Test 3 Passed. User1 updated heartbeat.")
    lock_info_after_hb = lock_manager_user1.get_current_lock_info() # From User1's perspective
    assert lock_info_after_hb is not None, "Test 3 Failed: Lock info should not be None after heartbeat"
    assert lock_info_after_hb['heartbeat_time_iso'] != current_lock_holder_info['heartbeat_time_iso'], "Test 3 Failed: Heartbeat time did not change"

    # Test 4: User1 re-acquires its own lock
    print("\n--- Test 4: UserOne re-acquires its own lock ---")
    status1_reacquire = lock_manager_user1.acquire_lock(120, "Further processing by UserSyncOne")
    assert status1_reacquire is True, f"Test 4 Failed: UserOne failed to re-acquire its own lock, got {status1_reacquire}"
    print(f"Test 4 Passed. UserOne re-acquire_lock status: {status1_reacquire}")
    reacquired_info = lock_manager_user1.get_current_lock_info()
    assert reacquired_info is not None, "Test 4 Failed: Lock info should not be None after re-acquire"
    assert reacquired_info['operation_description'] == "Further processing by UserSyncOne", "Test 4 Failed: Operation description not updated"
    assert reacquired_info['expected_duration_seconds'] == 120, "Test 4 Failed: Duration not updated"

    # Test 5: User1 releases lock
    print("\n--- Test 5: User1 releases lock ---")
    rel_status_u1 = lock_manager_user1.release_lock()
    assert rel_status_u1 is True, "Test 5 Failed: User1 could not release lock."
    assert not os.path.exists(actual_lock_file), f"Test 5 Failed: Lock file '{actual_lock_file}' not deleted."
    print("Test 5 Passed. User1 released lock.")

    # Test 6: User2 acquires lock now
    print("\n--- Test 6: User2 acquires lock (should succeed) ---")
    acq_status_u2_ok = lock_manager_user2.acquire_lock(45, "User2_Main_Task")
    assert acq_status_u2_ok is True, f"Test 6 Failed: User2 could not acquire lock. Status: {acq_status_u2_ok}"
    assert os.path.exists(actual_lock_file), f"Test 6 Failed: Lock file '{actual_lock_file}' not created by User2."
    print(f"Test 6 Passed. User2 acquired lock. Status: {acq_status_u2_ok}")

    # Test 7: Simulate stale lock by User2, User1 detects and force acquires
    print("\n--- Test 7: User1 detects stale lock from User2 and force acquires ---")
    if os.path.exists(actual_lock_file):
        with open(actual_lock_file, 'r+') as f_stale:
            stale_lock_data = json.load(f_stale)
            # Make it significantly stale
            stale_lock_data['heartbeat_time_iso'] = (datetime.now() - timedelta(seconds=300)).isoformat()
            stale_lock_data['expected_duration_seconds'] = 30
            f_stale.seek(0)
            json.dump(stale_lock_data, f_stale, indent=4)
            f_stale.truncate()
        print("Manually made User2's lock stale.")

    # User1 attempts to acquire, should detect stale
    print("UserOne trying to acquire (should detect stale from UserTwo)")
    # Temporarily disable QMessageBox for this test if it was enabled
    original_qmessagebox_available_state = _QMESSAGEBOX_AVAILABLE
    _QMESSAGEBOX_AVAILABLE = False

    acq_status_u1_stale = lock_manager_user1.acquire_lock(60, "User1_Checking_Stale_Lock")
    assert acq_status_u1_stale == "STALE_LOCK_DETECTED", f"Test 7 Failed: User1 should have detected stale. Status: {acq_status_u1_stale}"
    print(f"User1 detected stale lock. Status: {acq_status_u1_stale}")

    # User1 force acquires
    print("UserOne forcing acquire on stale lock")
    force_acq_status_u1 = lock_manager_user1.force_acquire_lock(70, "User1_Forced_Acquisition")
    assert force_acq_status_u1 is True, "Test 7 Failed: User1 could not force acquire."
    print("User1 force acquired the lock.")
    new_holder_info = lock_manager_user1.get_current_lock_info()
    assert new_holder_info is not None, "Test 7 Failed: Lock info should not be None after force acquire"
    assert new_holder_info['holder_nickname'] == "UserSyncOne", "Test 7 Failed: User1 is not the new holder."
    print(f"Lock now held by {new_holder_info['holder_nickname']}.")

    _QMESSAGEBOX_AVAILABLE = original_qmessagebox_available_state # Restore

    # Test 8: User2 tries to release User1's forcibly acquired lock (should fail)
    print("\n--- Test 8: User2 tries to release User1's lock (expect fail) ---")
    rel_status_u2_fail = lock_manager_user2.release_lock()
    assert rel_status_u2_fail is False, "Test 8 Failed: User2 should not have released User1's lock."
    print(f"Test 8 Passed. User2 failed to release lock. Status: {rel_status_u2_fail}")
    assert os.path.exists(actual_lock_file), "Test 8 Failed: Lock file should still exist (held by User1)."

    # Test 9: User1 releases its lock
    print("\n--- Test 9: User1 releases its forcibly acquired lock ---")
    rel_status_u1_final = lock_manager_user1.release_lock()
    assert rel_status_u1_final is True, "Test 9 Failed: User1 could not release its lock."
    assert not os.path.exists(actual_lock_file), f"Test 9 Failed: Lock file '{actual_lock_file}' not deleted."
    print("Test 9 Passed. User1 released lock.")

    # Cleanup
    print("\n--- Cleaning up ---")
    # Attempt to remove lock file first if it exists (e.g. if a test failed midway)
    if actual_lock_file and os.path.exists(actual_lock_file):
        os.remove(actual_lock_file)
        print(f"Cleaned up lingering lock file: {actual_lock_file}")
    if os.path.exists(mock_db_file_path):
        os.remove(mock_db_file_path)
        print(f"Cleaned up mock DB file: {mock_db_file_path}")
    if os.path.exists(test_dir):
        try:
            os.rmdir(test_dir) # Remove dir only if empty
            print(f"Cleaned up test directory: {test_dir}")
        except OSError as e_rmdir: # If lock file was somehow not deleted by test
            print(f"Could not remove test_dir {test_dir} initially: {e_rmdir}")
            if actual_lock_file and os.path.exists(actual_lock_file): # Final attempt
                 os.remove(actual_lock_file)
                 print(f"Force removed lock file {actual_lock_file} during cleanup")
            os.rmdir(test_dir)
            print(f"Cleaned up test directory (after attempting to remove lock file again): {test_dir}")

    print("--- DatabaseLockManager All Tests Finished ---")
