import unittest
import os
import json
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

# Ensure the test runner can find the core modules
import sys
# Add the project root to the Python path
# This assumes the tests are run from the project root or that the project structure is standard
# For example, if tests are in 'project_root/tests' and core is in 'project_root/core'
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.sync_manager import KMLFileLockManager
from core.credential_manager import CredentialManager # For spec in Mock

class TestKMLFileLockManager(unittest.TestCase):

    def setUp(self):
        self.test_kml_dir_obj = tempfile.TemporaryDirectory()
        self.test_kml_dir_path = Path(self.test_kml_dir_obj.name)

        self.mock_credential_manager = Mock(spec=CredentialManager)
        self.device_id_1 = "test_device_1"
        self.device_nickname_1 = "TestDevice1"
        self.mock_credential_manager.get_device_id.return_value = self.device_id_1
        self.mock_credential_manager.get_device_nickname.return_value = self.device_nickname_1

        self.lock_manager = KMLFileLockManager(str(self.test_kml_dir_path), self.mock_credential_manager)

        self.sample_kml_filename = "test_file.kml"
        self.other_device_id = "other_device_2"
        self.other_device_nickname = "OtherDevice2"

        # Constants from KMLFileLockManager for staleness calculations
        self.STALE_GRACE_PERIOD = self.lock_manager.STALE_LOCK_GRACE_PERIOD_SECONDS
        self.DEFAULT_DURATION = self.lock_manager.DEFAULT_KML_LOCK_DURATION_SECONDS

    def tearDown(self):
        self.test_kml_dir_obj.cleanup()

    def _create_manual_lock_file(self, kml_filename: str, holder_id: str, holder_nickname: str,
                                 start_time: datetime, heartbeat_time: datetime,
                                 duration: int, description: str = "Manual Lock"):
        lock_file_path = self.lock_manager._get_lock_file_path(kml_filename)
        lock_data = {
            'holder_device_id': holder_id,
            'holder_nickname': holder_nickname,
            'start_time_iso': start_time.isoformat(),
            'expected_duration_seconds': duration,
            'operation_description': description,
            'heartbeat_time_iso': heartbeat_time.isoformat()
        }
        with open(lock_file_path, 'w') as f:
            json.dump(lock_data, f, indent=4)
        return lock_file_path

    def test_get_lock_file_path(self):
        expected_path = self.test_kml_dir_path / f"{self.sample_kml_filename}.lock"
        self.assertEqual(self.lock_manager._get_lock_file_path(self.sample_kml_filename), expected_path)

    def test_acquire_lock_new(self):
        op_desc = "Test New Lock"
        duration = 600
        result = self.lock_manager.acquire_kml_lock(self.sample_kml_filename, op_desc, duration)
        self.assertTrue(result)

        lock_file_path = self.lock_manager._get_lock_file_path(self.sample_kml_filename)
        self.assertTrue(lock_file_path.exists())

        with open(lock_file_path, 'r') as f:
            lock_data = json.load(f)

        self.assertEqual(lock_data['holder_device_id'], self.device_id_1)
        self.assertEqual(lock_data['holder_nickname'], self.device_nickname_1)
        self.assertEqual(lock_data['operation_description'], op_desc)
        self.assertEqual(lock_data['expected_duration_seconds'], duration)
        self.assertTrue(datetime.fromisoformat(lock_data['start_time_iso']))
        self.assertTrue(datetime.fromisoformat(lock_data['heartbeat_time_iso']))
        self.assertAlmostEqual(
            datetime.fromisoformat(lock_data['start_time_iso']),
            datetime.fromisoformat(lock_data['heartbeat_time_iso']),
            delta=timedelta(seconds=1)
        )

    def test_acquire_lock_already_held_by_self(self):
        op_desc1 = "Initial acquire"
        self.lock_manager.acquire_kml_lock(self.sample_kml_filename, op_desc1, 300)

        lock_file_path = self.lock_manager._get_lock_file_path(self.sample_kml_filename)
        with open(lock_file_path, 'r') as f:
            initial_lock_data = json.load(f)
        initial_heartbeat_dt = datetime.fromisoformat(initial_lock_data['heartbeat_time_iso'])

        time.sleep(0.01) # Ensure time difference for heartbeat update

        op_desc2 = "Re-acquire by self"
        duration2 = 700
        # Credential manager already returns self.device_id_1
        result = self.lock_manager.acquire_kml_lock(self.sample_kml_filename, op_desc2, duration2)
        self.assertTrue(result)

        with open(lock_file_path, 'r') as f:
            updated_lock_data = json.load(f)

        self.assertEqual(updated_lock_data['holder_device_id'], self.device_id_1)
        self.assertEqual(updated_lock_data['operation_description'], op_desc2)
        self.assertEqual(updated_lock_data['expected_duration_seconds'], duration2)
        updated_heartbeat_dt = datetime.fromisoformat(updated_lock_data['heartbeat_time_iso'])
        self.assertGreater(updated_heartbeat_dt, initial_heartbeat_dt)

    def test_acquire_lock_busy_not_stale(self):
        now = datetime.now(timezone.utc)
        self._create_manual_lock_file(
            self.sample_kml_filename, self.other_device_id, self.other_device_nickname,
            start_time=now - timedelta(seconds=10),
            heartbeat_time=now - timedelta(seconds=5), # Recent heartbeat
            duration=self.DEFAULT_DURATION,
            description="Busy Lock Test"
        )
        # self.mock_credential_manager already set to device_id_1
        result = self.lock_manager.acquire_kml_lock(self.sample_kml_filename)
        self.assertFalse(result)

    def test_acquire_lock_stale(self):
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=self.DEFAULT_DURATION + self.STALE_GRACE_PERIOD + 100)
        self._create_manual_lock_file(
            self.sample_kml_filename, self.other_device_id, self.other_device_nickname,
            start_time=stale_time - timedelta(seconds=self.DEFAULT_DURATION), # Start even earlier
            heartbeat_time=stale_time, # Stale heartbeat
            duration=self.DEFAULT_DURATION
        )
        result = self.lock_manager.acquire_kml_lock(self.sample_kml_filename)
        self.assertEqual(result, "STALE_LOCK_DETECTED")

    def test_force_acquire_lock(self):
        self._create_manual_lock_file(
            self.sample_kml_filename, self.other_device_id, self.other_device_nickname,
            start_time=datetime.now(timezone.utc) - timedelta(seconds=10),
            heartbeat_time=datetime.now(timezone.utc) - timedelta(seconds=5),
            duration=300, description="To Be Overridden"
        )
        op_desc = "Forced Acquire"
        result = self.lock_manager.force_acquire_kml_lock(self.sample_kml_filename, operation_description=op_desc)
        self.assertTrue(result)

        lock_file_path = self.lock_manager._get_lock_file_path(self.sample_kml_filename)
        with open(lock_file_path, 'r') as f:
            lock_data = json.load(f)
        self.assertEqual(lock_data['holder_device_id'], self.device_id_1)
        self.assertEqual(lock_data['operation_description'], op_desc)

    def test_release_lock_owned(self):
        self.lock_manager.acquire_kml_lock(self.sample_kml_filename)
        result = self.lock_manager.release_kml_lock(self.sample_kml_filename)
        self.assertTrue(result)
        lock_file_path = self.lock_manager._get_lock_file_path(self.sample_kml_filename)
        self.assertFalse(lock_file_path.exists())

    def test_release_lock_not_owned(self):
        self._create_manual_lock_file(
            self.sample_kml_filename, self.other_device_id, self.other_device_nickname,
            start_time=datetime.now(timezone.utc), heartbeat_time=datetime.now(timezone.utc), duration=300
        )
        result = self.lock_manager.release_kml_lock(self.sample_kml_filename)
        self.assertFalse(result)
        lock_file_path = self.lock_manager._get_lock_file_path(self.sample_kml_filename)
        self.assertTrue(lock_file_path.exists())

    def test_release_lock_does_not_exist(self):
        result = self.lock_manager.release_kml_lock("non_existent.kml")
        self.assertTrue(result)

    def test_update_heartbeat_owned(self):
        self.lock_manager.acquire_kml_lock(self.sample_kml_filename)
        lock_file_path = self.lock_manager._get_lock_file_path(self.sample_kml_filename)
        with open(lock_file_path, 'r') as f:
            initial_lock_data = json.load(f)
        initial_heartbeat_dt = datetime.fromisoformat(initial_lock_data['heartbeat_time_iso'])

        time.sleep(0.01) # Ensure time difference

        result = self.lock_manager.update_kml_heartbeat(self.sample_kml_filename, new_operation_description="Heartbeat Update", new_expected_duration=999)
        self.assertTrue(result)

        with open(lock_file_path, 'r') as f:
            updated_lock_data = json.load(f)
        updated_heartbeat_dt = datetime.fromisoformat(updated_lock_data['heartbeat_time_iso'])
        self.assertGreater(updated_heartbeat_dt, initial_heartbeat_dt)
        self.assertEqual(updated_lock_data['operation_description'], "Heartbeat Update")
        self.assertEqual(updated_lock_data['expected_duration_seconds'], 999)


    def test_update_heartbeat_not_owned(self):
        self._create_manual_lock_file(
            self.sample_kml_filename, self.other_device_id, self.other_device_nickname,
            start_time=datetime.now(timezone.utc), heartbeat_time=datetime.now(timezone.utc), duration=300
        )
        result = self.lock_manager.update_kml_heartbeat(self.sample_kml_filename)
        self.assertFalse(result)

    def test_get_kml_lock_info_exists(self):
        self.lock_manager.acquire_kml_lock(self.sample_kml_filename, "Info Test", 123)
        lock_info = self.lock_manager.get_kml_lock_info(self.sample_kml_filename)
        self.assertIsNotNone(lock_info, "Lock info should not be None for an existing lock.")
        # Using .get() for safer access, though assertIsNotNone should ensure lock_info is a dict
        self.assertEqual(lock_info.get('holder_device_id'), self.device_id_1)
        self.assertEqual(lock_info.get('operation_description'), "Info Test")
        self.assertEqual(lock_info.get('expected_duration_seconds'), 123)

    def test_get_kml_lock_info_not_exists(self):
        lock_info = self.lock_manager.get_kml_lock_info("non_existent.kml")
        self.assertIsNone(lock_info)

    def test_is_kml_locked_true_active_other_user(self):
        now = datetime.now(timezone.utc)
        self._create_manual_lock_file(
            self.sample_kml_filename, self.other_device_id, self.other_device_nickname,
            start_time=now - timedelta(seconds=10),
            heartbeat_time=now - timedelta(seconds=5), # Active
            duration=self.DEFAULT_DURATION
        )
        self.assertTrue(self.lock_manager.is_kml_locked(self.sample_kml_filename))

    def test_is_kml_locked_false_stale_other_user(self):
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=self.DEFAULT_DURATION + self.STALE_GRACE_PERIOD + 100)
        self._create_manual_lock_file(
            self.sample_kml_filename, self.other_device_id, self.other_device_nickname,
            start_time=stale_time - timedelta(seconds=self.DEFAULT_DURATION),
            heartbeat_time=stale_time, # Stale
            duration=self.DEFAULT_DURATION
        )
        self.assertFalse(self.lock_manager.is_kml_locked(self.sample_kml_filename))

    def test_is_kml_locked_false_locked_by_self(self):
        self.lock_manager.acquire_kml_lock(self.sample_kml_filename)
        # Credential manager still points to self.device_id_1
        self.assertFalse(self.lock_manager.is_kml_locked(self.sample_kml_filename))

    def test_is_kml_locked_false_no_lock(self):
        self.assertFalse(self.lock_manager.is_kml_locked(self.sample_kml_filename))

    def test_acquire_lock_error_no_device_id(self):
        self.mock_credential_manager.get_device_id.return_value = None
        result = self.lock_manager.acquire_kml_lock(self.sample_kml_filename)
        self.assertEqual(result, "ERROR")

    def test_malformed_lock_file_acquire(self):
        lock_file_path = self.lock_manager._get_lock_file_path(self.sample_kml_filename)
        with open(lock_file_path, 'w') as f:
            f.write("this is not json")

        result = self.lock_manager.acquire_kml_lock(self.sample_kml_filename)
        self.assertEqual(result, "STALE_LOCK_DETECTED") # Current behavior treats parse error as potentially stale

    def test_malformed_lock_file_release_not_owned(self):
        lock_file_path = self.lock_manager._get_lock_file_path(self.sample_kml_filename)
        with open(lock_file_path, 'w') as f:
            f.write("this is not json {") # malformed

        result = self.lock_manager.release_kml_lock(self.sample_kml_filename)
        # If it cannot read the lock file, it cannot determine ownership, so it should not release.
        self.assertFalse(result)
        self.assertTrue(lock_file_path.exists()) # File should remain

    def test_malformed_lock_file_is_locked(self):
        lock_file_path = self.lock_manager._get_lock_file_path(self.sample_kml_filename)
        with open(lock_file_path, 'w') as f:
            f.write("this is not json")

        # is_kml_locked calls get_kml_lock_info, which returns None for malformed file.
        # If lock_info is None, is_kml_locked returns False.
        self.assertFalse(self.lock_manager.is_kml_locked(self.sample_kml_filename))


if __name__ == '__main__':
    unittest.main(verbosity=2)
