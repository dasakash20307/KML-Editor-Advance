import os
import json
import time
from datetime import datetime, timedelta

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
    def __init__(self, db_path_str: str, credential_manager): # Type hint: credential_manager: CredentialManager
        self.db_path_str = db_path_str
        self.credential_manager = credential_manager
        self.lock_file_path = None
        self._current_lock_info_cache = None

        if not self.db_path_str or not os.path.basename(self.db_path_str):
            print("DBLockManager: ERROR - Database path is invalid or empty.")
            self.db_path_str = None
        else:
            db_dir = os.path.dirname(self.db_path_str)
            if not db_dir:
                # This means db_path_str is a relative path for a file in the current working directory.
                # The lock file should also be in the current working directory.
                db_dir = "."
            db_name = os.path.basename(self.db_path_str)
            self.lock_file_path = os.path.join(db_dir, f"{db_name}.lock")

    def _get_lock_file_path(self) -> str | None:
        return self.lock_file_path

    def get_current_lock_info(self) -> dict | None:
        if not self.lock_file_path:
            # This case can happen if __init__ received an invalid db_path_str
            print("DBLockManager: INFO (get_current_lock_info) - No lock file path configured (db_path_str might have been invalid).")
            return None
        try:
            if os.path.exists(self.lock_file_path):
                with open(self.lock_file_path, 'r') as f:
                    return json.load(f)
            return None # File doesn't exist, so no lock info
        except (IOError, json.JSONDecodeError) as e:
            print(f"DBLockManager: Error reading lock file for info ('{self.lock_file_path}'): {e}")
            return None # Corrupt or unreadable

    def acquire_lock(self, expected_duration_seconds: int, operation_description: str) -> str | bool:
        self._current_lock_info_cache = None
        if not self.lock_file_path:
            print("DBLockManager: ERROR (acquire_lock) - Lock manager not properly initialized (no lock file path).")
            return "ERROR"
        if not self.credential_manager:
            print("DBLockManager: ERROR (acquire_lock) - CredentialManager not available.")
            return "ERROR"

        current_device_id = self.credential_manager.get_device_id()
        current_device_nickname = self.credential_manager.get_device_nickname()

        if not current_device_id or not current_device_nickname:
            print("DBLockManager: ERROR (acquire_lock) - Device ID or Nickname not available from CredentialManager.")
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
                    print(f"DBLockManager: WARNING (acquire_lock) - Could not read or parse existing lock file '{self.lock_file_path}': {e}. Assuming stale.")
                    return "STALE_LOCK_DETECTED"

                holder_device_id = lock_data.get('holder_device_id')
                heartbeat_time_iso_str = lock_data.get('heartbeat_time_iso')
                expected_duration_from_file = lock_data.get('expected_duration_seconds')

                if holder_device_id == current_device_id:
                    print(f"DBLockManager: WARNING (acquire_lock) - Lock already held by this device ('{current_device_nickname}'). Updating heartbeat and operation.")
                    lock_data['heartbeat_time_iso'] = datetime.now().isoformat()
                    lock_data['operation_description'] = operation_description
                    lock_data['expected_duration_seconds'] = expected_duration_seconds
                    try:
                        with open(self.lock_file_path, 'w') as f:
                            json.dump(lock_data, f, indent=4)
                        self._current_lock_info_cache = lock_data
                        return True
                    except IOError as e_write:
                        print(f"DBLockManager: ERROR (acquire_lock) - Failed to update existing lock file: {e_write}")
                        return "ERROR"

                if heartbeat_time_iso_str and expected_duration_from_file is not None:
                    try:
                        heartbeat_dt = datetime.fromisoformat(heartbeat_time_iso_str)
                        if datetime.now() > (heartbeat_dt + timedelta(seconds=(expected_duration_from_file + grace_period_seconds))):
                            print(f"DBLockManager: Stale lock detected. Held by {lock_data.get('holder_nickname', 'Unknown')}. Last heartbeat: {heartbeat_time_iso_str}")
                            return "STALE_LOCK_DETECTED"
                    except ValueError:
                        print(f"DBLockManager: WARNING (acquire_lock) - Could not parse heartbeat timestamp '{heartbeat_time_iso_str}'. Assuming stale.")
                        return "STALE_LOCK_DETECTED"
                else:
                    print(f"DBLockManager: WARNING (acquire_lock) - Lock file missing heartbeat or expected_duration. Assuming stale.")
                    return "STALE_LOCK_DETECTED"

                print(f"DBLockManager: Lock held by another user: {lock_data.get('holder_nickname', 'Unknown')} for operation '{lock_data.get('operation_description', 'Unknown Op')}'")
                return False

            # If lock file does not exist, create it
            new_lock_data = {
                'holder_device_id': current_device_id,
                'holder_nickname': current_device_nickname,
                'start_time_iso': datetime.now().isoformat(),
                'expected_duration_seconds': expected_duration_seconds,
                'operation_description': operation_description,
                'heartbeat_time_iso': datetime.now().isoformat()
            }
            with open(self.lock_file_path, 'w') as f:
                json.dump(new_lock_data, f, indent=4)
            self._current_lock_info_cache = new_lock_data
            print(f"DBLockManager: Lock acquired by {current_device_nickname} for '{operation_description}'.")
            return True

        except IOError as e:
            print(f"DBLockManager: IOError during acquire_lock ('{self.lock_file_path}'): {e}")
            return "ERROR"
        except Exception as e_unhandled:
            print(f"DBLockManager: Unexpected error in acquire_lock: {e_unhandled}")
            return "ERROR"

    def force_acquire_lock(self, expected_duration_seconds: int, operation_description: str) -> bool:
        if not self.lock_file_path:
            print("DBLockManager: ERROR (force_acquire) - Lock manager not properly initialized.")
            return False

        current_device_id = self.credential_manager.get_device_id()
        current_device_nickname = self.credential_manager.get_device_nickname()
        if not current_device_id or not current_device_nickname:
            print("DBLockManager: ERROR (force_acquire) - Device ID or Nickname not available.")
            return False

        try:
            if os.path.exists(self.lock_file_path):
                os.remove(self.lock_file_path)
                print(f"DBLockManager: Removed existing lock file ('{self.lock_file_path}') for force acquire by {current_device_nickname}.")

            new_lock_data = {
                'holder_device_id': current_device_id,
                'holder_nickname': current_device_nickname,
                'start_time_iso': datetime.now().isoformat(),
                'expected_duration_seconds': expected_duration_seconds,
                'operation_description': operation_description,
                'heartbeat_time_iso': datetime.now().isoformat()
            }
            with open(self.lock_file_path, 'w') as f:
                json.dump(new_lock_data, f, indent=4)
            self._current_lock_info_cache = new_lock_data
            print(f"DBLockManager: Lock forcibly acquired by {current_device_nickname} for '{operation_description}'.")
            return True
        except (IOError, OSError) as e:
            print(f"DBLockManager: ERROR (force_acquire) - Failed to remove or create lock file ('{self.lock_file_path}'): {e}")
            return False
        except Exception as e_unhandled:
            print(f"DBLockManager: Unexpected error in force_acquire_lock: {e_unhandled}")
            return False

    def release_lock(self) -> bool:
        if not self.lock_file_path:
            print("DBLockManager: WARNING (release) - No lock file path configured. Assuming released.")
            return True

        current_device_id = self.credential_manager.get_device_id()
        if not current_device_id:
            print("DBLockManager: ERROR (release) - Cannot verify current device ID to release lock.")
            return False

        try:
            if os.path.exists(self.lock_file_path):
                lock_data_on_release = None
                try:
                    with open(self.lock_file_path, 'r') as f:
                        lock_data_on_release = json.load(f)
                except (IOError, json.JSONDecodeError) as e:
                    print(f"DBLockManager: WARNING (release) - Could not read lock file '{self.lock_file_path}' during release: {e}.")
                    if self._current_lock_info_cache and self._current_lock_info_cache.get('holder_device_id') == current_device_id:
                        print(f"DBLockManager: (release) Lock file unreadable but cache indicates current device owns it. Attempting removal.")
                        # Fall through to os.remove by not returning False yet
                    else:
                        print(f"DBLockManager: (release) Lock file unreadable and no cached ownership by this device. Not removing.")
                        return False

                if lock_data_on_release and lock_data_on_release.get('holder_device_id') == current_device_id:
                    os.remove(self.lock_file_path)
                    print(f"DBLockManager: Lock released by {self.credential_manager.get_device_nickname()} from file '{self.lock_file_path}'.")
                    self._current_lock_info_cache = None
                    return True
                elif lock_data_on_release:
                    print(f"DBLockManager: WARNING (release) - Attempt to release lock on '{self.lock_file_path}' held by {lock_data_on_release.get('holder_nickname', 'Unknown')}. Not released by {self.credential_manager.get_device_nickname()}.")
                    return False
                else:
                    if self._current_lock_info_cache and self._current_lock_info_cache.get('holder_device_id') == current_device_id:
                         os.remove(self.lock_file_path)
                         print(f"DBLockManager: Lock released by {self.credential_manager.get_device_nickname()} from file '{self.lock_file_path}' (based on cache after read fail).")
                         self._current_lock_info_cache = None
                         return True
                    print(f"DBLockManager: WARNING (release) - Lock file '{self.lock_file_path}' was unreadable and not confirmed owned by cache.")
                    return False


            else: # Lock file does not exist
                print(f"DBLockManager: Lock file '{self.lock_file_path}' not found on release (already released or never acquired).")
                self._current_lock_info_cache = None
                return True
        except (IOError, OSError) as e:
            print(f"DBLockManager: ERROR (release) - Failed to remove lock file '{self.lock_file_path}': {e}")
            return False
        except Exception as e_unhandled:
            print(f"DBLockManager: Unexpected error in release_lock: {e_unhandled}")
            return False
        # Fallback, though all paths should be covered.
        return False


    def update_heartbeat(self) -> bool:
        if not self.lock_file_path or not os.path.exists(self.lock_file_path):
            print(f"DBLockManager: WARNING (heartbeat) - Lock file '{self.lock_file_path}' not found.")
            return False

        current_device_id = self.credential_manager.get_device_id()
        if not current_device_id:
            print("DBLockManager: ERROR (heartbeat) - Device ID not available.")
            return False

        try:
            with open(self.lock_file_path, 'r+') as f:
                lock_data = json.load(f)
                if lock_data.get('holder_device_id') == current_device_id:
                    lock_data['heartbeat_time_iso'] = datetime.now().isoformat()
                    f.seek(0)
                    json.dump(lock_data, f, indent=4)
                    f.truncate()
                    self._current_lock_info_cache = lock_data
                    # print(f"DBLockManager: Heartbeat updated by {self.credential_manager.get_device_nickname()}.") # Can be too verbose
                    return True
                else:
                    print(f"DBLockManager: WARNING (heartbeat) - Attempt to update heartbeat for lock on '{self.lock_file_path}' held by {lock_data.get('holder_nickname','Unknown')}. Denied for {self.credential_manager.get_device_nickname()}.")
                    return False
        except (IOError, json.JSONDecodeError) as e:
            print(f"DBLockManager: ERROR (heartbeat) - Failed to read/write lock file '{self.lock_file_path}': {e}")
            return False
        except Exception as e_unhandled:
            print(f"DBLockManager: Unexpected error in update_heartbeat: {e_unhandled}")
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
    def __init__(self, kml_folder_path_str: str, credential_manager): # credential_manager: 'CredentialManager'
        self.kml_folder_path = Path(kml_folder_path_str)
        self.credential_manager = credential_manager
        self.STALE_LOCK_GRACE_PERIOD_SECONDS: int = 300
        self.DEFAULT_KML_LOCK_DURATION_SECONDS: int = 300

        if not self.kml_folder_path.is_dir():
            try:
                self.kml_folder_path.mkdir(parents=True, exist_ok=True)
                print(f"KMLFileLockManager: KML folder created at {self.kml_folder_path}")
            except OSError as e:
                print(f"KMLFileLockManager: ERROR - Could not create KML folder at {self.kml_folder_path}: {e}")
                # Potentially raise an error or set a state indicating failure
                # For now, path operations will likely fail if dir doesn't exist.

    def _get_lock_file_path(self, kml_filename: str) -> Path:
        """Constructs and returns the full path for a KML lock file."""
        return self.kml_folder_path / f"{kml_filename}.lock"

    def acquire_kml_lock(self, kml_filename: str, operation_description: str = "KML file operation",
                         expected_duration_seconds: int = None) -> Union[bool, str]:
        lock_file_path = self._get_lock_file_path(kml_filename)
        effective_duration_seconds = expected_duration_seconds or self.DEFAULT_KML_LOCK_DURATION_SECONDS

        current_device_id = self.credential_manager.get_device_id()
        current_device_nickname = self.credential_manager.get_device_nickname()

        if not current_device_id or not current_device_nickname:
            print("KMLFileLockManager: ERROR (acquire) - Device ID or Nickname not available.")
            return "ERROR"

        try:
            if lock_file_path.exists():
                lock_data = None
                try:
                    with open(lock_file_path, 'r') as f:
                        lock_data = json.load(f)
                except (IOError, json.JSONDecodeError) as e:
                    print(f"KMLFileLockManager: WARNING (acquire) - Could not read/parse lock file '{lock_file_path}': {e}. Assuming stale.")
                    return "STALE_LOCK_DETECTED"

                holder_device_id = lock_data.get('holder_device_id')
                heartbeat_time_iso_str = lock_data.get('heartbeat_time_iso')
                lock_expected_duration = lock_data.get('expected_duration_seconds', self.DEFAULT_KML_LOCK_DURATION_SECONDS)

                if holder_device_id == current_device_id:
                    print(f"KMLFileLockManager: Lock for '{kml_filename}' already held by this device ('{current_device_nickname}'). Updating.")
                    return self.update_kml_heartbeat(kml_filename,
                                                     new_operation_description=operation_description,
                                                     new_expected_duration=effective_duration_seconds)

                if heartbeat_time_iso_str:
                    try:
                        # Ensure datetime objects are timezone-aware for comparison
                        heartbeat_dt = datetime.fromisoformat(heartbeat_time_iso_str)
                        if heartbeat_dt.tzinfo is None:
                             heartbeat_dt = heartbeat_dt.replace(tzinfo=timezone.utc) # Assume UTC

                        staleness_threshold = heartbeat_dt + timedelta(seconds=(lock_expected_duration + self.STALE_LOCK_GRACE_PERIOD_SECONDS))
                        if staleness_threshold < datetime.now(timezone.utc):
                            holder_nickname = lock_data.get('holder_nickname', 'Unknown Device')
                            print(f"KMLFileLockManager: Stale lock for '{kml_filename}' detected. Held by {holder_nickname}. Last heartbeat: {heartbeat_time_iso_str}")
                            return "STALE_LOCK_DETECTED"
                    except ValueError:
                        print(f"KMLFileLockManager: WARNING (acquire) - Could not parse heartbeat timestamp '{heartbeat_time_iso_str}' for '{kml_filename}'. Assuming stale.")
                        return "STALE_LOCK_DETECTED"
                else:
                    print(f"KMLFileLockManager: WARNING (acquire) - Lock file for '{kml_filename}' missing heartbeat. Assuming stale.")
                    return "STALE_LOCK_DETECTED"

                holder_nickname = lock_data.get('holder_nickname', "Unknown Device")
                print(f"KMLFileLockManager: Lock for '{kml_filename}' is busy. Held by {holder_nickname}.")
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
                print(f"KMLFileLockManager: Lock acquired for '{kml_filename}' by {current_device_nickname}.")
                return True

        except IOError as e:
            print(f"KMLFileLockManager: IOError during acquire_kml_lock for '{kml_filename}': {e}")
            return "ERROR"
        except Exception as e_unhandled:
            print(f"KMLFileLockManager: Unexpected error in acquire_kml_lock for '{kml_filename}': {e_unhandled}")
            return "ERROR"

    def force_acquire_kml_lock(self, kml_filename: str, operation_description: str = "KML file operation",
                               expected_duration_seconds: int = None) -> bool:
        lock_file_path = self._get_lock_file_path(kml_filename)
        effective_duration_seconds = expected_duration_seconds or self.DEFAULT_KML_LOCK_DURATION_SECONDS

        current_device_id = self.credential_manager.get_device_id()
        current_device_nickname = self.credential_manager.get_device_nickname()

        if not current_device_id or not current_device_nickname:
            print("KMLFileLockManager: ERROR (force_acquire) - Device ID or Nickname not available.")
            return False

        try:
            if lock_file_path.exists():
                try:
                    os.remove(lock_file_path)
                    print(f"KMLFileLockManager: Removed existing lock file '{lock_file_path}' for force acquire by {current_device_nickname}.")
                except OSError as e_remove:
                    print(f"KMLFileLockManager: ERROR (force_acquire) - Failed to remove existing lock file '{lock_file_path}': {e_remove}")
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
            print(f"KMLFileLockManager: Lock forcibly acquired for '{kml_filename}' by {current_device_nickname}.")
            return True
        except IOError as e:
            print(f"KMLFileLockManager: IOError during force_acquire_kml_lock for '{kml_filename}': {e}")
            return False
        except Exception as e_unhandled:
            print(f"KMLFileLockManager: Unexpected error in force_acquire_kml_lock for '{kml_filename}': {e_unhandled}")
            return False

    def release_kml_lock(self, kml_filename: str) -> bool:
        lock_file_path = self._get_lock_file_path(kml_filename)
        current_device_id = self.credential_manager.get_device_id()

        if not current_device_id:
            print("KMLFileLockManager: ERROR (release) - Device ID not available. Cannot verify ownership.")
            return False

        try:
            if lock_file_path.exists():
                lock_data = None
                try:
                    with open(lock_file_path, 'r') as f:
                        lock_data = json.load(f)
                except (IOError, json.JSONDecodeError) as e:
                    print(f"KMLFileLockManager: WARNING (release) - Could not read/parse lock file '{lock_file_path}': {e}. Cannot verify ownership to release.")
                    return False

                holder_device_id = lock_data.get('holder_device_id')
                if holder_device_id == current_device_id:
                    try:
                        os.remove(lock_file_path)
                        print(f"KMLFileLockManager: Lock released for '{kml_filename}' by {self.credential_manager.get_device_nickname()}.")
                        return True
                    except OSError as e_remove:
                        print(f"KMLFileLockManager: ERROR (release) - Failed to remove lock file '{lock_file_path}': {e_remove}")
                        return False
                else:
                    holder_nickname = lock_data.get('holder_nickname', 'another device')
                    current_nickname = self.credential_manager.get_device_nickname()
                    print(f"KMLFileLockManager: WARNING (release) - {current_nickname} attempted to release lock for '{kml_filename}' held by {holder_nickname} (ID: {holder_device_id}). Denied.")
                    return False
            else:
                print(f"KMLFileLockManager: Lock for '{kml_filename}' not found on release (already released or never acquired).")
                return True
        except IOError as e:
            print(f"KMLFileLockManager: IOError during release_kml_lock for '{kml_filename}': {e}")
            return False
        except Exception as e_unhandled:
            print(f"KMLFileLockManager: Unexpected error in release_kml_lock for '{kml_filename}': {e_unhandled}")
            return False


    def update_kml_heartbeat(self, kml_filename: str, new_operation_description: str = None,
                             new_expected_duration: int = None) -> bool:
        lock_file_path = self._get_lock_file_path(kml_filename)
        current_device_id = self.credential_manager.get_device_id()

        if not current_device_id:
            print("KMLFileLockManager: ERROR (heartbeat) - Device ID not available.")
            return False

        try:
            if lock_file_path.exists():
                lock_data = None
                try:
                    with open(lock_file_path, 'r') as f:
                        lock_data = json.load(f)
                except (IOError, json.JSONDecodeError) as e:
                    print(f"KMLFileLockManager: ERROR (heartbeat) - Could not read/parse lock file '{lock_file_path}': {e}")
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
                        return True
                    except IOError as e_write:
                        print(f"KMLFileLockManager: ERROR (heartbeat) - Failed to write updated lock file '{lock_file_path}': {e_write}")
                        return False
                else:
                    holder_nickname = lock_data.get('holder_nickname', 'another device')
                    print(f"KMLFileLockManager: WARNING (heartbeat) - Attempt to update heartbeat for lock on '{kml_filename}' held by {holder_nickname}. Denied for {self.credential_manager.get_device_nickname()}.")
                    return False
            else:
                print(f"KMLFileLockManager: WARNING (heartbeat) - Lock file '{lock_file_path}' not found for heartbeat update.")
                return False
        except IOError as e:
            print(f"KMLFileLockManager: IOError during update_kml_heartbeat for '{kml_filename}': {e}")
            return False
        except Exception as e_unhandled:
            print(f"KMLFileLockManager: Unexpected error in update_kml_heartbeat for '{kml_filename}': {e_unhandled}")
            return False

    def get_kml_lock_info(self, kml_filename: str) -> Optional[dict]:
        lock_file_path = self._get_lock_file_path(kml_filename)
        try:
            if lock_file_path.exists():
                with open(lock_file_path, 'r') as f:
                    return json.load(f)
            return None
        except (IOError, json.JSONDecodeError) as e:
            print(f"KMLFileLockManager: Error reading lock info for '{kml_filename}' from '{lock_file_path}': {e}")
            return None
        except Exception as e_unhandled:
            print(f"KMLFileLockManager: Unexpected error in get_kml_lock_info for '{kml_filename}': {e_unhandled}")
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
            print(f"KMLFileLockManager: WARNING (is_locked) - Lock for '{kml_filename}' is malformed (missing heartbeat). Treating as not locked.")
            return False

        try:
            heartbeat_dt = datetime.fromisoformat(heartbeat_time_iso_str)
            if heartbeat_dt.tzinfo is None:
                heartbeat_dt = heartbeat_dt.replace(tzinfo=timezone.utc)

            staleness_threshold = heartbeat_dt + timedelta(seconds=(lock_expected_duration + self.STALE_LOCK_GRACE_PERIOD_SECONDS))
            if staleness_threshold < datetime.now(timezone.utc):
                return False
        except ValueError:
            print(f"KMLFileLockManager: WARNING (is_locked) - Could not parse heartbeat for '{kml_filename}'. Treating as not locked.")
            return False

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

    lock_manager_user1 = DatabaseLockManager(mock_db_file_path, cm_user1)
    lock_manager_user2 = DatabaseLockManager(mock_db_file_path, cm_user2)

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
