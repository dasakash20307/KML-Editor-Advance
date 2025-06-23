import sqlite3
import uuid
import os
import platformdirs
import json # Added for table view config

class CredentialManager:
    DB_FILE_NAME = "device_config.db"
    APP_NAME = "DilasaKMLTool_V5_Config" # Subdirectory for our config
    APP_AUTHOR = "Dilasa" # Optional, but good for platformdirs

    DEFAULT_KML_VIEW_SETTINGS = {
        "kml_fill_color_hex": "#007bff",  # Blue
        "kml_fill_opacity_percent": 50,   # 50%
        "kml_line_color_hex": "#000000",  # Black
        "kml_line_width_px": 1,
        "kml_view_mode": "Outline and Fill",  # Options: "Outline and Fill", "Outline Only", "Fill Only"
        "kml_max_zoom": 18 # Integer, e.g., 18 (typical max for many tile layers)
    }
    TABLE_VIEW_CONFIG_KEY = "table_view_column_config" # Key for storing table view config
    APP_THEME_KEY = "app_theme_preference" # Key for storing app theme
    DEFAULT_APP_THEME = "light" # Default theme

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

    def get_config_file_path(self) -> str:
        """Returns the full path to the device_config.db file."""
        return self.db_path

    def get_kml_default_view_settings(self) -> dict:
        """
        Retrieves KML default view settings from the database.
        If any setting is not found, it falls back to the class default for that setting.
        """
        settings_from_db = {}
        has_any_setting_from_db = False # To check if we should even try parsing

        # Check if any relevant setting exists to avoid defaulting everything if DB just created
        # This check is a bit indirect; ideally, we'd know if _create_config_db_if_not_exists ran
        # and inserted defaults, but this class doesn't do that for these new settings yet.
        # For now, we fetch and if a value is None, we use default.

        for key in self.DEFAULT_KML_VIEW_SETTINGS.keys():
            value_str = self._get_setting(key)
            if value_str is not None:
                has_any_setting_from_db = True # At least one setting was found
                if key in ["kml_fill_opacity_percent", "kml_line_width_px", "kml_max_zoom"]:
                    try:
                        settings_from_db[key] = int(value_str)
                    except ValueError:
                        print(f"Warning: Could not parse integer for {key}: '{value_str}'. Using default.")
                        settings_from_db[key] = self.DEFAULT_KML_VIEW_SETTINGS[key]
                else: # String values like colors, view_mode
                    settings_from_db[key] = value_str
            else:
                # Value not in DB, use default from class constant
                settings_from_db[key] = self.DEFAULT_KML_VIEW_SETTINGS[key]

        # If no specific KML settings were ever saved, settings_from_db will be populated by defaults.
        # This is the desired behavior: always return a full dict.
        return settings_from_db

    def save_kml_default_view_settings(self, settings_dict: dict) -> bool:
        """
        Saves KML default view settings to the database.
        Only saves keys that are defined in DEFAULT_KML_VIEW_SETTINGS.
        """
        try:
            for key, default_value in self.DEFAULT_KML_VIEW_SETTINGS.items():
                if key in settings_dict:
                    value_to_save = settings_dict[key]
                    # Ensure data types are consistent with defaults for casting if needed later,
                    # though _set_setting stores everything as text.
                    if isinstance(default_value, int):
                        try:
                            # Validate if it can be an int, but store as string
                            int(value_to_save)
                            self._set_setting(key, str(value_to_save))
                        except ValueError:
                            print(f"Warning: Invalid integer value for {key}: '{value_to_save}'. Skipping.")
                    else: # strings
                         self._set_setting(key, str(value_to_save))
                # else: key from DEFAULT_KML_VIEW_SETTINGS not in settings_dict, so don't update it.
                # This means partial updates are possible if desired, but the current design
                # of the calling dialog implies it will always provide all settings.
            return True
        except Exception as e:
            print(f"Error saving KML default view settings: {e}")
            return False

    def save_table_view_config(self, ordered_visible_headers: list[str]):
        """Saves the ordered list of visible table column headers as a JSON string."""
        if not isinstance(ordered_visible_headers, list):
            print("Error: save_table_view_config expects a list.")
            return False
        try:
            config_json = json.dumps(ordered_visible_headers)
            self._set_setting(self.TABLE_VIEW_CONFIG_KEY, config_json)
            # print(f"Saved table view config: {config_json}") # For debugging
            return True
        except TypeError as e:
            print(f"Error serializing table view config to JSON: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error saving table view config: {e}")
            return False

    def load_table_view_config(self) -> list[str] | None:
        """Loads the ordered list of visible table column headers. Returns None if not set or error."""
        try:
            config_json = self._get_setting(self.TABLE_VIEW_CONFIG_KEY)
            if config_json:
                # print(f"Loaded table view config JSON: {config_json}") # For debugging
                config_list = json.loads(config_json)
                if isinstance(config_list, list) and all(isinstance(item, str) for item in config_list):
                    return config_list
                else:
                    print("Error: Table view config in DB is not a list of strings.")
                    self._set_setting(self.TABLE_VIEW_CONFIG_KEY, None) # Clear invalid setting
                    return None
            return None # No config saved yet
        except json.JSONDecodeError as e:
            print(f"Error decoding table view config JSON from DB: {e}")
            self._set_setting(self.TABLE_VIEW_CONFIG_KEY, None) # Clear invalid setting
            return None
        except Exception as e:
            print(f"Unexpected error loading table view config: {e}")
            return None

    def save_app_theme(self, theme_name: str):
        """Saves the application theme preference (e.g., 'dark', 'light')."""
        if theme_name not in ["dark", "light"]:
            print(f"Warning: Invalid theme name '{theme_name}' provided to save_app_theme. Not saving.")
            return False
        try:
            self._set_setting(self.APP_THEME_KEY, theme_name)
            print(f"Saved app theme: {theme_name}")  # For debugging
            return True
        except Exception as e:
            print(f"Error saving app theme: {e}")
            return False

    def load_app_theme(self) -> str:
        """Loads the application theme preference. Returns default if not set or error."""
        try:
            theme_name = self._get_setting(self.APP_THEME_KEY)
            if theme_name in ["dark", "light"]:
                print(f"Loaded app theme: {theme_name}")  # For debugging
                return theme_name
            print(f"App theme not set or invalid in DB. Returning default: {self.DEFAULT_APP_THEME}")  # For debugging
            return self.DEFAULT_APP_THEME  # Return default if not set or invalid
        except Exception as e:
            print(f"Error loading app theme: {e}. Returning default.")
            return self.DEFAULT_APP_THEME

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
                 except OSError as e_dir_create: # Catches OSError from makedirs or remove
                     print(f"Error during directory creation or file removal: {e_dir_create}")
            else:
                print("Parent directory already existed. Removal failed for other reasons (e.g. permissions, file in use).")

    if not os.path.exists(expected_app_data_dir):
        os.makedirs(expected_app_data_dir, exist_ok=True)
        print(f"Pre-emptively created data directory for CredentialManager: {expected_app_data_dir}")

    cm = CredentialManager()
    print(f"Is first run? {cm.is_first_run()}")
    # Initial assertion depends on whether the DB file was actually deleted successfully above.
    # This test block is complex due to file system interactions.

    # Test KML View Settings
    print("\n--- Testing KML View Settings ---")
    if cm.is_first_run(): # If DB was just created
        print("First run: Getting KML default view settings (should be class defaults)...")
        kml_settings = cm.get_kml_default_view_settings()
        assert kml_settings == CredentialManager.DEFAULT_KML_VIEW_SETTINGS, \
            f"Expected default KML settings, got {kml_settings}"
        print(f"Initial KML settings (from class defaults): {kml_settings}")

    # Create a new CredentialManager instance to simulate fresh load after potential first run save_settings
    # This is because cm.save_settings() also sets self._first_run = False
    # To ensure we test loading from a DB that might or might not have KML settings yet:
    if os.path.exists(db_file_path_for_test) and not cm.is_first_run():
         # If the previous block ran save_settings, the DB exists.
         # We want to test get_kml_default_view_settings when no KML settings are explicitly saved yet.
         # The current implementation of get_kml_default_view_settings will return class defaults
         # if specific keys are not in the DB.
         pass # Covered by the logic below


    print("\nSaving new KML view settings...")
    new_kml_settings = {
        "kml_fill_color_hex": "#ff0000",
        "kml_fill_opacity_percent": 30,
        "kml_line_color_hex": "#00ff00",
        "kml_line_width_px": 3,
        "kml_view_mode": "Outline Only",
        "kml_zoom_offset": -1
    }
    save_success = cm.save_kml_default_view_settings(new_kml_settings)
    assert save_success, "Failed to save KML view settings."
    print("New KML settings saved.")

    print("Getting KML view settings after save...")
    retrieved_kml_settings = cm.get_kml_default_view_settings()
    assert retrieved_kml_settings == new_kml_settings, \
        f"Expected {new_kml_settings}, but got {retrieved_kml_settings}"
    print(f"Retrieved KML settings: {retrieved_kml_settings}")
    assert retrieved_kml_settings["kml_fill_opacity_percent"] == 30, "Opacity type check"
    assert retrieved_kml_settings["kml_line_width_px"] == 3, "Line width type check"
    assert retrieved_kml_settings["kml_zoom_offset"] == -1, "Zoom offset type check"


    print("\nTest saving partial KML settings (should only update provided ones)...")
    partial_settings = {
        "kml_fill_color_hex": "#cccccc",
        "kml_zoom_offset": 2
    }
    cm.save_kml_default_view_settings(partial_settings)
    retrieved_after_partial_save = cm.get_kml_default_view_settings()
    print(f"Settings after partial save: {retrieved_after_partial_save}")
    # Expected:
    # kml_fill_color_hex should be #cccccc
    # kml_fill_opacity_percent should be 30 (from previous save)
    # kml_line_color_hex should be #00ff00 (from previous save)
    # kml_line_width_px should be 3 (from previous save)
    # kml_view_mode should be "Outline Only" (from previous save)
    # kml_zoom_offset should be 2
    assert retrieved_after_partial_save["kml_fill_color_hex"] == "#cccccc"
    assert retrieved_after_partial_save["kml_fill_opacity_percent"] == 30
    assert retrieved_after_partial_save["kml_line_color_hex"] == "#00ff00"
    assert retrieved_after_partial_save["kml_line_width_px"] == 3
    assert retrieved_after_partial_save["kml_view_mode"] == "Outline Only"
    assert retrieved_after_partial_save["kml_zoom_offset"] == 2
    print("Partial KML settings save verified.")


    # Original tests for basic settings
    if cm.is_first_run(): # This block might not run if DB existed from previous KML tests
        print("\nSaving new settings for first run (original test flow)...")
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

    # Test Table View Config settings
    print("\n--- Testing Table View Config Settings ---")
    initial_tv_config = cm.load_table_view_config()
    print(f"Initial table view config (should be None if fresh DB): {initial_tv_config}")
    assert initial_tv_config is None, f"Expected initial table view config to be None, got {initial_tv_config}"

    test_config_v1 = ["ID", "Name", "Status"]
    print(f"Saving table view config v1: {test_config_v1}")
    save_v1_ok = cm.save_table_view_config(test_config_v1)
    assert save_v1_ok, "Failed to save table view config v1"
    loaded_config_v1 = cm.load_table_view_config()
    print(f"Loaded table view config v1: {loaded_config_v1}")
    assert loaded_config_v1 == test_config_v1, f"Load v1 failed. Expected {test_config_v1}, got {loaded_config_v1}"

    test_config_v2 = ["Name", "Status", "ID", "Date Added", "UUID"]
    print(f"Saving table view config v2: {test_config_v2}")
    save_v2_ok = cm.save_table_view_config(test_config_v2)
    assert save_v2_ok, "Failed to save table view config v2"
    loaded_config_v2 = cm.load_table_view_config()
    print(f"Loaded table view config v2: {loaded_config_v2}")
    assert loaded_config_v2 == test_config_v2, f"Load v2 failed. Expected {test_config_v2}, got {loaded_config_v2}"

    print("Saving empty list as table view config...")
    save_empty_ok = cm.save_table_view_config([])
    assert save_empty_ok, "Failed to save empty table view config"
    loaded_empty_config = cm.load_table_view_config()
    print(f"Loaded empty table view config: {loaded_empty_config}")
    assert loaded_empty_config == [], f"Load empty failed. Expected [], got {loaded_empty_config}"

    # Test loading invalid data (manual DB edit would be needed to fully test this part of load)
    # For now, setting an invalid JSON directly to test load_table_view_config error handling
    print("Testing load of intentionally malformed JSON for table view config...")
    cm._set_setting(cm.TABLE_VIEW_CONFIG_KEY, "not a json list")
    malformed_load = cm.load_table_view_config()
    assert malformed_load is None, f"Expected None for malformed JSON, got {malformed_load}"
    print(f"Loading malformed JSON resulted in: {malformed_load} (expected None)")
    # Check if the setting was cleared
    assert cm._get_setting(cm.TABLE_VIEW_CONFIG_KEY) is None, "Malformed JSON was not cleared from DB"
    print("Malformed JSON was correctly cleared from DB after failed load attempt.")

    print("\nAll CredentialManager tests (including platformdirs init, KML view, and Table view) completed.")
