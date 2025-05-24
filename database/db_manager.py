import sqlite3
import os
import datetime

# --- Database Configuration ---
DB_FOLDER_NAME_CONST = "DilasaKMLTool_v4" # AppData subfolder for this version
DB_FILE_NAME_CONST = "app_data_v4.db"   # Specific DB file for this version

class DatabaseManager:
    """
    Manages all interactions with the SQLite database for the Dilasa KML Tool.
    Handles creation of tables, and CRUD operations for API sources and polygon data.
    """
    def __init__(self, db_folder_name=None, db_file_name=None):
        folder_name = db_folder_name or DB_FOLDER_NAME_CONST
        file_name = db_file_name or DB_FILE_NAME_CONST
        
        app_data_dir = os.getenv('APPDATA')
        if not app_data_dir:
            app_data_dir = os.path.expanduser("~")
            print(f"Warning: APPDATA environment variable not found. Using user home directory: {app_data_dir}")

        self.db_path = os.path.join(app_data_dir, folder_name)
        os.makedirs(self.db_path, exist_ok=True)
        self.db_path = os.path.join(self.db_path, file_name)

        self.conn = None
        self.cursor = None # Explicitly initialize cursor
        self._connect()
        
        # Ensure connection and cursor are valid after _connect()
        if not self.conn or not self.cursor:
            # This should ideally be caught by _connect's raise, but Pylance might not fully infer it.
            raise sqlite3.OperationalError("DB_MGR_INIT_ERROR: Database connection or cursor failed to initialize.")
        
        self._create_tables()
        # print(f"Database initialized at: {self.db_path}")

    def _connect(self):
        """Establishes a connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA foreign_keys = ON;")
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            self.conn = None # Ensure conn is None on failure
            self.cursor = None # Ensure cursor is None on failure
            raise

    def _create_tables(self):
        """Creates the necessary tables if they don't already exist."""
        if not self.conn or not self.cursor:
            print(f"DB_MGR_ERROR (_create_tables): Database connection or cursor is not available.")
            raise sqlite3.OperationalError("DB_MGR_ERROR (_create_tables): Attempted to create tables without DB connection.")
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS mwater_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS polygon_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,
                    response_code TEXT UNIQUE NOT NULL,
                    farmer_name TEXT,
                    village_name TEXT,
                    block TEXT,
                    district TEXT,
                    proposed_area_acre TEXT,
                    p1_utm_str TEXT, p1_altitude REAL, p1_easting REAL, p1_northing REAL, p1_zone_num INTEGER, p1_zone_letter TEXT, p1_substituted BOOLEAN DEFAULT 0,
                    p2_utm_str TEXT, p2_altitude REAL, p2_easting REAL, p2_northing REAL, p2_zone_num INTEGER, p2_zone_letter TEXT, p2_substituted BOOLEAN DEFAULT 0,
                    p3_utm_str TEXT, p3_altitude REAL, p3_easting REAL, p3_northing REAL, p3_zone_num INTEGER, p3_zone_letter TEXT, p3_substituted BOOLEAN DEFAULT 0,
                    p4_utm_str TEXT, p4_altitude REAL, p4_easting REAL, p4_northing REAL, p4_zone_num INTEGER, p4_zone_letter TEXT, p4_substituted BOOLEAN DEFAULT 0,
                    status TEXT NOT NULL,
                    error_messages TEXT,
                    kml_export_count INTEGER DEFAULT 0,
                    last_kml_export_date TIMESTAMP,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")

    def add_mwater_source(self, title, url):
        if not self.conn or not self.cursor:
            print(f"DB_MGR_ERROR (add_mwater_source): Database connection or cursor is not available.")
            return None
        try:
            self.cursor.execute("INSERT INTO mwater_sources (title, url) VALUES (?, ?)", (title, url))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"DB: mWater source with URL '{url}' already exists.")
            return None
        except sqlite3.Error as e:
            print(f"DB: Error adding mWater source: {e}")
            return None

    def get_mwater_sources(self):
        if not self.conn or not self.cursor:
            print(f"DB_MGR_ERROR (get_mwater_sources): Database connection or cursor is not available.")
            return []
        try:
            self.cursor.execute("SELECT id, title, url FROM mwater_sources ORDER BY title")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"DB: Error fetching mWater sources: {e}")
            return []

    def update_mwater_source(self, source_id, title, url):
        if not self.conn or not self.cursor:
            print(f"DB_MGR_ERROR (update_mwater_source): Database connection or cursor is not available.")
            return False
        try:
            self.cursor.execute("UPDATE mwater_sources SET title = ?, url = ? WHERE id = ?", (title, url, source_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.IntegrityError:
            print(f"DB: Error updating mWater source - URL '{url}' might conflict.")
            return False
        except sqlite3.Error as e:
            print(f"DB: Error updating mWater source: {e}")
            return False

    def delete_mwater_source(self, source_id):
        if not self.conn or not self.cursor:
            print(f"DB_MGR_ERROR (delete_mwater_source): Database connection or cursor is not available.")
            return False
        try:
            self.cursor.execute("DELETE FROM mwater_sources WHERE id = ?", (source_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"DB: Error deleting mWater source: {e}")
            return False

    def check_duplicate_response_code(self, response_code):
        if not self.conn or not self.cursor:
            print(f"DB_MGR_ERROR (check_duplicate_response_code): Database connection or cursor is not available.")
            return None
        try:
            self.cursor.execute("SELECT id FROM polygon_data WHERE response_code = ?", (response_code,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"DB: Error checking duplicate response code: {e}")
            return None

    def add_or_update_polygon_data(self, data_dict, overwrite=False):
        if not self.conn or not self.cursor:
            print(f"DB_MGR_ERROR (add_or_update_polygon_data): Database connection or cursor is not available.")
            return None
        
        response_code_val = data_dict.get('response_code')
        if not response_code_val:
            print(f"DB Error: Missing 'response_code' in data_dict for add/update.")
            return None

        existing_record_id = self.check_duplicate_response_code(response_code_val)
        current_time_iso = datetime.datetime.now().isoformat()
        
        if 'error_messages' in data_dict and isinstance(data_dict['error_messages'], list):
            data_dict['error_messages'] = "\n".join(data_dict['error_messages']) if data_dict['error_messages'] else None

        # Guard for PRAGMA call
        if not self.conn or not self.cursor: 
            print(f"DB_MGR_ERROR (add_or_update_polygon_data - pre-pragma): Database connection or cursor is not available.")
            return None
        self.cursor.execute("PRAGMA table_info(polygon_data)")
        valid_columns = {row[1] for row in self.cursor.fetchall()}
        filtered_data = {k: v for k, v in data_dict.items() if k in valid_columns}
        filtered_data['last_modified'] = current_time_iso

        if existing_record_id and overwrite:
            set_clauses = []
            values_for_update = []
            for key, value in filtered_data.items():
                if key not in ['id', 'response_code', 'date_added']:
                    set_clauses.append(f"{key} = ?")
                    values_for_update.append(value)
            
            if not set_clauses:
                self.cursor.execute("UPDATE polygon_data SET last_modified = ? WHERE response_code = ?", (current_time_iso, response_code_val))
                self.conn.commit()
                return existing_record_id
            
            values_for_update.append(response_code_val)
            sql = f"UPDATE polygon_data SET {', '.join(set_clauses)} WHERE response_code = ?"
            try:
                self.cursor.execute(sql, values_for_update)
                self.conn.commit()
                return existing_record_id
            except sqlite3.Error as e:
                print(f"DB Error updating polygon data for RC '{response_code_val}': {e}")
                return None
        elif not existing_record_id:
            if 'date_added' not in filtered_data:
                filtered_data['date_added'] = current_time_iso
            
            columns = list(filtered_data.keys())
            placeholders = ['?'] * len(columns)
            values_for_insert = [filtered_data[col] for col in columns]
            
            if not columns: 
                print(f"DB Error: No valid columns to insert for RC '{response_code_val}'.")
                return None

            sql = f"INSERT INTO polygon_data ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            try:
                self.cursor.execute(sql, values_for_insert)
                self.conn.commit()
                return self.cursor.lastrowid
            except sqlite3.IntegrityError as e:
                print(f"DB Integrity Error adding polygon data for RC '{response_code_val}': {e}")
                return None
            except sqlite3.Error as e:
                print(f"DB Error adding polygon data for RC '{response_code_val}': {e}")
                return None
        else:
            return existing_record_id

    def get_all_polygon_data_for_display(self):
        if not self.conn or not self.cursor:
            print(f"DB_MGR_ERROR (get_all_polygon_data_for_display): Database connection or cursor is not available.")
            return []
        try:
            self.cursor.execute("""
                SELECT id, status, uuid, farmer_name, village_name, date_added, kml_export_count, last_kml_export_date 
                FROM polygon_data 
                ORDER BY date_added DESC
            """) 
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"DB: Error fetching polygon data for display: {e}")
            return []

    def get_polygon_data_by_id(self, record_id):
        if not self.conn or not self.cursor:
            print(f"DB_MGR_ERROR (get_polygon_data_by_id): Database connection or cursor is not available.")
            return None
        try:
            self.cursor.execute("SELECT * FROM polygon_data WHERE id = ?", (record_id,))
            row = self.cursor.fetchone()
            if row:
                col_names = [desc[0] for desc in self.cursor.description]
                return dict(zip(col_names, row))
            return None
        except sqlite3.Error as e:
            print(f"DB: Error fetching polygon data by ID '{record_id}': {e}")
            return None

    def update_kml_export_status(self, record_id):
        if not self.conn or not self.cursor:
            print(f"DB_MGR_ERROR (update_kml_export_status): Database connection or cursor is not available.")
            return False
        try:
            current_time_iso = datetime.datetime.now().isoformat()
            self.cursor.execute("""
                UPDATE polygon_data
                SET kml_export_count = kml_export_count + 1,
                    last_kml_export_date = ?,
                    last_modified = ? 
                WHERE id = ?
            """, (current_time_iso, current_time_iso, record_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"DB: Error updating KML export status for ID '{record_id}': {e}")
            return False

    def delete_polygon_data(self, record_id_list):
        if not self.conn or not self.cursor:
            print(f"DB_MGR_ERROR (delete_polygon_data): Database connection or cursor is not available.")
            return False
        if not isinstance(record_id_list, list): record_id_list = [record_id_list]
        if not record_id_list: return False
        try:
            placeholders = ','.join(['?'] * len(record_id_list))
            self.cursor.execute(f"DELETE FROM polygon_data WHERE id IN ({placeholders})", record_id_list)
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"DB: Error deleting polygon data: {e}")
            return False

    def delete_all_polygon_data(self):
        if not self.conn or not self.cursor:
            print(f"DB_MGR_ERROR (delete_all_polygon_data): Database connection or cursor is not available.")
            return False
        try:
            self.cursor.execute("DELETE FROM polygon_data")
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"DB: Error deleting all polygon data: {e}")
            return False

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None # Also set cursor to None
            # print("Database connection closed.")

if __name__ == '__main__':
    # Example Usage (for testing this module directly)
    print("Testing DatabaseManager...")
    db_manager = DatabaseManager()
    print(f"Using database at: {db_manager.db_path}")

    print("\n--- Testing mWater Sources ---")
    source_id1 = db_manager.add_mwater_source("Test Source 1", "http://example.com/api1")
    source_id2 = db_manager.add_mwater_source("Test Source 2", "http://example.com/api2")
    print(f"Added source 1 ID: {source_id1}")
    print(f"Added source 2 ID: {source_id2}")
    
    all_sources = db_manager.get_mwater_sources()
    print(f"All sources: {all_sources}")
    
    if source_id1:
        db_manager.update_mwater_source(source_id1, "Test Source 1 Updated", "http://example.com/api1_updated")
        print(f"Updated source 1. New sources: {db_manager.get_mwater_sources()}")

    print("\n--- Testing Polygon Data ---")
    sample_poly_data1 = {
        "uuid": "uuid-test-001", "response_code": "rc-test-001", "farmer_name": "Test Farmer 1",
        "village_name": "Test Village", "status": "valid_for_kml",
        "p1_utm_str": "43Q 123 456", "p1_altitude": 100.0, "p1_easting": 123.0, "p1_northing": 456.0, "p1_zone_num": 43, "p1_zone_letter": "Q",
    }
    sample_poly_data2 = {
        "uuid": "uuid-test-002", "response_code": "rc-test-002", "farmer_name": "Test Farmer 2",
        "village_name": "Another Village", "status": "error_missing_points", "error_messages": "Point 3 missing",
    }

    poly_id1 = db_manager.add_or_update_polygon_data(sample_poly_data1)
    poly_id2 = db_manager.add_or_update_polygon_data(sample_poly_data2)
    print(f"Added polygon 1 ID: {poly_id1}")
    print(f"Added polygon 2 ID: {poly_id2}")

    poly_id1_again = db_manager.add_or_update_polygon_data(sample_poly_data1, overwrite=False)
    print(f"Attempted to add polygon 1 again (no overwrite), result ID: {poly_id1_again}")

    sample_poly_data1_updated = sample_poly_data1.copy()
    sample_poly_data1_updated["farmer_name"] = "Test Farmer 1 Updated Name"
    poly_id1_overwrite = db_manager.add_or_update_polygon_data(sample_poly_data1_updated, overwrite=True)
    print(f"Attempted to add polygon 1 again (overwrite), result ID: {poly_id1_overwrite}")

    all_polys = db_manager.get_all_polygon_data_for_display()
    print(f"All polygon data for display ({len(all_polys)} records):")
    for poly_row in all_polys:
        print(poly_row)
    
    if poly_id1_overwrite:
        full_poly1 = db_manager.get_polygon_data_by_id(poly_id1_overwrite)
        print(f"\nFull data for polygon ID {poly_id1_overwrite}: {full_poly1}")
        if full_poly1:
            db_manager.update_kml_export_status(poly_id1_overwrite)
            updated_poly1 = db_manager.get_polygon_data_by_id(poly_id1_overwrite)
            if updated_poly1: # Added check for updated_poly1
                print(f"Updated KML export status for ID {poly_id1_overwrite}: Count={updated_poly1.get('kml_export_count')}, Date={updated_poly1.get('last_kml_export_date')}")
            else:
                print(f"Could not retrieve updated_poly1 for ID {poly_id1_overwrite}")


    db_manager.close()
    print("\nDatabaseManager tests finished.")

    # To clean up the test database file:
    # test_db_path = os.path.join(os.getenv('APPDATA') or os.path.expanduser("~"), DB_FOLDER_NAME_CONST, DB_FILE_NAME_CONST)
    # if db_manager.db_path == test_db_path: # Basic check to avoid deleting production DB if constants were changed
    #    if os.path.exists(test_db_path):
    #        try:
    #            # db_manager.close() # ensure it's closed
    #            # os.remove(test_db_path)
    #            # print(f"Removed test database: {test_db_path}")
    #            print(f"Test database cleanup: Would remove {test_db_path} if uncommented.")
    #        except Exception as e:
    #            print(f"Error removing test database: {e}")
    # else:
    #    print(f"Test cleanup: Skipped removal, db_path '{db_manager.db_path}' does not match expected test path.")

# Ensure __main__ block also handles potential None from db_manager methods if conn is not available
# For example, if db_manager.add_mwater_source returns None:
# if source_id1:
#    db_manager.update_mwater_source(source_id1, "Test Source 1 Updated", "http://example.com/api1_updated")
# This is already handled by the `if source_id1:` checks.
# The main goal of the guards is to prevent AttributeError within the class methods themselves.
# Client code should already be robust to methods returning None/False/[] on failure.
