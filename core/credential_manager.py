import sqlite3
import uuid
import os
import platformdirs

class CredentialManager:
    DB_FILE_NAME = "device_config.db"
    APP_NAME = "DilasaKMLTool_V5_Config" # Subdirectory for our config
    APP_AUTHOR = "Dilasa" # Optional, but good for platformdirs

    def __init__(self):
        # Use platformdirs to get the user-specific data directory
        self.app_data_path = platformdirs.user_data_dir(self.APP_NAME, self.APP_AUTHOR)

        if not os.path.exists(self.app_data_path):
            os.makedirs(self.app_data_path, exist_ok=True)

        self.db_path = os.path.join(self.app_data_path, self.DB_FILE_NAME)
        self._first_run = not os.path.exists(self.db_path)

        self._device_id = None
        self._device_nickname = None
        self._app_mode = None
        self._main_db_path = None
        self._kml_folder_path = None

        if self._first_run:
            self._create_config_db_if_not_exists()
        else:
            self._load_settings()

    def _create_config_db_if_not_exists(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating config database or table: {e}")
        finally:
            if conn:
                conn.close()

    def is_first_run(self) -> bool:
        return self._first_run

    def _generate_device_uuid(self) -> str:
        return uuid.uuid4().hex[:8].upper()

    def _set_setting(self, key, value):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error setting setting {key}: {e}")
        finally:
            if conn:
                conn.close()

    def _get_setting(self, key):
        value = None
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                value = row[0]
        except sqlite3.Error as e:
            print(f"Error getting setting {key}: {e}")
        finally:
            if conn:
                conn.close()
        return value

    def save_settings(self, nickname: str, app_mode: str, main_db_path: str, kml_folder_path: str):
        self._create_config_db_if_not_exists()

        self._device_id = self._generate_device_uuid()
        self._device_nickname = nickname
        self._app_mode = app_mode
        self._main_db_path = main_db_path
        self._kml_folder_path = kml_folder_path

        self._set_setting("device_id", self._device_id)
        self._set_setting("device_nickname", self._device_nickname)
        self._set_setting("app_mode", self._app_mode)
        self._set_setting("main_db_path", self._main_db_path)
        self._set_setting("kml_folder_path", self._kml_folder_path)

        self._first_run = False

    def _load_settings(self):
        self._device_id = self._get_setting("device_id")
        self._device_nickname = self._get_setting("device_nickname")
        self._app_mode = self._get_setting("app_mode")
        self._main_db_path = self._get_setting("main_db_path")
        self._kml_folder_path = self._get_setting("kml_folder_path")

        if not all([self._device_id, self._device_nickname, self._app_mode, self._main_db_path, self._kml_folder_path]):
            print("Warning: Some settings could not be loaded from device_config.db. "
                  "The application might not behave as expected if these are critical and missing.")

    def get_device_id(self) -> str | None:
        return self._device_id

    def get_device_nickname(self) -> str | None:
        return self._device_nickname

    def get_app_mode(self) -> str | None:
        return self._app_mode

    def get_db_path(self) -> str | None:
        return self._main_db_path

    def get_kml_folder_path(self) -> str | None:
        return self._kml_folder_path

if __name__ == '__main__':
    print("--- Test CredentialManager (with platformdirs) ---")
    expected_app_data_dir = platformdirs.user_data_dir(CredentialManager.APP_NAME, CredentialManager.APP_AUTHOR)
    db_file_path_for_test = os.path.join(expected_app_data_dir, CredentialManager.DB_FILE_NAME)

    print(f"Config DB path for this test run: {db_file_path_for_test}")
    print(f"Platformdirs user_data_dir (raw, no appname/author): {platformdirs.user_data_dir()}")
    print(f"Platformdirs user_data_dir (used for APP_NAME, APP_AUTHOR): {expected_app_data_dir}")
    print(f"Platformdirs user_config_dir (for comparison): {platformdirs.user_config_dir(CredentialManager.APP_NAME, CredentialManager.APP_AUTHOR)}")

    print("\nSimulating first run...")
    if os.path.exists(db_file_path_for_test):
        print(f"Attempting to remove existing DB at: {db_file_path_for_test}")
        try:
            os.remove(db_file_path_for_test)
            print(f"Removed existing {CredentialManager.DB_FILE_NAME} for fresh test.")
        except OSError as e:
            print(f"Error removing DB file: {e}.")
            if not os.path.exists(expected_app_data_dir):
                 try:
                     os.makedirs(expected_app_data_dir, exist_ok=True)
                     print(f"Created directory: {expected_app_data_dir} as it was missing.")
                     if os.path.exists(db_file_path_for_test):
                        os.remove(db_file_path_for_test)
                        print("Removed DB after creating parent directory.")
                 except OSError as e_dir_create:
                     print(f"Error creating directory {expected_app_data_dir}: {e_dir_create}")
                 except OSError as e_retry:
                     print(f"Still failed to remove DB after attempting to create dir: {e_retry}")
            else:
                print("Parent directory already existed. Removal failed for other reasons (e.g. permissions, file in use).")

    if not os.path.exists(expected_app_data_dir):
        os.makedirs(expected_app_data_dir, exist_ok=True)
        print(f"Pre-emptively created data directory for CredentialManager: {expected_app_data_dir}")

    cm = CredentialManager()
    print(f"Is first run? {cm.is_first_run()}")
    assert cm.is_first_run(), "Should be a first run after cleaning DB file."

    if cm.is_first_run():
        print("Saving new settings for first run...")
        cm.save_settings(
            nickname="PlatformTestDevice",
            app_mode="Central App",
            main_db_path="/path/to/central/platform_main_data.db",
            kml_folder_path="/path/to/central/platform_kml_files/"
        )
        print("Settings saved.")
        print(f"Is first run after save? {cm.is_first_run()}")
        assert not cm.is_first_run(), "Should not be a first run after saving settings."

    print("\nLoading settings on subsequent launch simulation:")
    cm_new_instance = CredentialManager()
    print(f"Is first run (new instance)? {cm_new_instance.is_first_run()}")
    assert not cm_new_instance.is_first_run(), "New instance should load existing settings."
    print(f"Device ID: {cm_new_instance.get_device_id()}")
    print(f"Nickname: {cm_new_instance.get_device_nickname()}")
    assert cm_new_instance.get_device_nickname() == "PlatformTestDevice"

    print("\nTesting overwriting settings (simulating a re-setup):")
    original_id = cm_new_instance.get_device_id()
    cm_new_instance.save_settings(
        nickname="PlatformTestDeviceUpdated",
        app_mode="Connected App",
        main_db_path="/network/path/platform_another_main_data.db",
        kml_folder_path="/network/path/platform_another_kml_files/"
    )
    cm_third_instance = CredentialManager()
    assert cm_third_instance.get_device_id() != original_id, "Device ID should change on re-save"
    assert cm_third_instance.get_device_nickname() == "PlatformTestDeviceUpdated"
    assert cm_third_instance.get_app_mode() == "Connected App"
    print("Settings updated, new ID generated, and verified.")

    print(f"\nTo inspect, check the DB file: {db_file_path_for_test}")
    print("--- Test Complete ---")
