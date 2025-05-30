import sqlite3
import os
import datetime

# --- Database Configuration ---
# These constants will be used by the main application to instantiate the DB manager
# For modularity, the DB_FOLDER_NAME and DB_FILE_NAME could also be passed
# to the DatabaseManager constructor if you prefer more flexibility later.

class DatabaseManager:
    """
    Manages all interactions with the SQLite database for the Dilasa KML Tool.
    Handles creation of tables, and CRUD operations for API sources and polygon data.
    """
    def __init__(self, db_path):
        """
        Initializes the DatabaseManager.
        Connects to the database and creates tables if they don't exist.

        Args:
            db_path (str): The full path to the SQLite database file.
        """
        self.db_path = db_path
        
        # Ensure the directory for the db_path exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir): # Check if db_dir is not empty (for relative paths)
            os.makedirs(db_dir, exist_ok=True)

        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()
        self._migrate_schema() # Add migration step
        # print(f"Database initialized at: {self.db_path}") # For debugging

    def _migrate_schema(self):
        """Checks for and applies necessary schema migrations."""
        try:
            self.cursor.execute("PRAGMA table_info(polygon_data)")
            columns = [row[1] for row in self.cursor.fetchall()]
            if 'evaluation_status' not in columns:
                print("Schema migration: Adding 'evaluation_status' column to 'polygon_data' table.")
                self.cursor.execute("ALTER TABLE polygon_data ADD COLUMN evaluation_status TEXT DEFAULT 'Not Evaluated Yet'")
                self.conn.commit()
                print("'evaluation_status' column added successfully.")
        except sqlite3.Error as e:
            print(f"Schema migration error: {e}")

    def _connect(self):
        """Establishes a connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA foreign_keys = ON;") # Good practice
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            # Consider how to handle this - maybe raise an exception or exit
            raise # Re-raise the exception to make it clear DB is not available

    def _create_tables(self):
        """Creates the necessary tables if they don't already exist."""
        try:
            # mWater API Sources Table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS mwater_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE
                )
            ''')

            # Polygon Data Table - Updated for v4 with KML export tracking
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
                    status TEXT NOT NULL, -- e.g., 'valid_for_kml', 'error_missing_points', 'error_parsing'
                    error_messages TEXT,  -- Store as newline-separated string or JSON string
                    kml_export_count INTEGER DEFAULT 0,
                    last_kml_export_date TIMESTAMP,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    evaluation_status TEXT DEFAULT 'Not Evaluated Yet'
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")

    # --- mWater API Sources Methods ---
    def add_mwater_source(self, title, url):
        try:
            self.cursor.execute("INSERT INTO mwater_sources (title, url) VALUES (?, ?)", (title, url))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError: # For UNIQUE constraint on URL
            print(f"DB: mWater source with URL '{url}' already exists.")
            return None
        except sqlite3.Error as e:
            print(f"DB: Error adding mWater source: {e}")
            return None

    def get_mwater_sources(self):
        try:
            self.cursor.execute("SELECT id, title, url FROM mwater_sources ORDER BY title")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"DB: Error fetching mWater sources: {e}")
            return []

    def update_mwater_source(self, source_id, title, url):
        try:
            self.cursor.execute("UPDATE mwater_sources SET title = ?, url = ? WHERE id = ?", (title, url, source_id))
            self.conn.commit()
            return self.cursor.rowcount > 0 # Returns True if a row was updated
        except sqlite3.IntegrityError:
            print(f"DB: Error updating mWater source - URL '{url}' might conflict.")
            return False
        except sqlite3.Error as e:
            print(f"DB: Error updating mWater source: {e}")
            return False

    def delete_mwater_source(self, source_id):
        try:
            self.cursor.execute("DELETE FROM mwater_sources WHERE id = ?", (source_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"DB: Error deleting mWater source: {e}")
            return False

    # --- Polygon Data Methods ---
    def check_duplicate_response_code(self, response_code):
        """Checks if a response_code already exists. Returns the record ID if found, else None."""
        try:
            self.cursor.execute("SELECT id FROM polygon_data WHERE response_code = ?", (response_code,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"DB: Error checking duplicate response code: {e}")
            return None # Treat as not found on error to be safe

    def add_or_update_polygon_data(self, data_dict, overwrite=False):
        """
        Adds a new polygon record or updates an existing one based on response_code if overwrite is True.
        data_dict should contain keys matching the polygon_data table columns.
        """
        response_code_val = data_dict.get('response_code')
        if not response_code_val:
            print(f"DB Error: Missing 'response_code' in data_dict for add/update.")
            return None

        existing_record_id = self.check_duplicate_response_code(response_code_val)
        current_time_iso = datetime.datetime.now().isoformat()
        
        # Ensure error_messages is a string or None
        if 'error_messages' in data_dict and isinstance(data_dict['error_messages'], list):
            data_dict['error_messages'] = "\n".join(data_dict['error_messages']) if data_dict['error_messages'] else None

        # Filter data_dict to only include keys that are actual column names
        self.cursor.execute("PRAGMA table_info(polygon_data)")
        valid_columns = {row[1] for row in self.cursor.fetchall()}
        filtered_data = {k: v for k, v in data_dict.items() if k in valid_columns}
        filtered_data['last_modified'] = current_time_iso


        if existing_record_id and overwrite:
            # UPDATE existing record
            set_clauses = []
            values_for_update = []
            for key, value in filtered_data.items():
                if key not in ['id', 'response_code', 'date_added']: # Cannot update PK, unique key, or creation date
                    set_clauses.append(f"{key} = ?")
                    values_for_update.append(value)
            
            if not set_clauses: # Nothing to update other than last_modified perhaps
                # Still update last_modified if only that changed
                self.cursor.execute("UPDATE polygon_data SET last_modified = ? WHERE response_code = ?", (current_time_iso, response_code_val))
                self.conn.commit()
                return existing_record_id
            
            values_for_update.append(response_code_val) # For the WHERE clause
            sql = f"UPDATE polygon_data SET {', '.join(set_clauses)} WHERE response_code = ?"
            try:
                self.cursor.execute(sql, values_for_update)
                self.conn.commit()
                return existing_record_id
            except sqlite3.Error as e:
                print(f"DB Error updating polygon data for RC '{response_code_val}': {e}")
                return None
        elif not existing_record_id:
            # INSERT new record
            if 'date_added' not in filtered_data: # Set date_added for new records
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
            except sqlite3.IntegrityError as e: # Usually for UNIQUE constraint violations (uuid, response_code)
                print(f"DB Integrity Error adding polygon data for RC '{response_code_val}': {e}")
                return None # Or perhaps fetch and return the existing ID if it's a UUID conflict
            except sqlite3.Error as e:
                print(f"DB Error adding polygon data for RC '{response_code_val}': {e}")
                return None
        else: # Record exists, but overwrite is False
            return existing_record_id # Return existing ID, indicating no action taken

    def get_all_polygon_data_for_display(self):
        """Fetches specific columns for display in the Treeview."""
        try:
            self.cursor.execute("""
                SELECT id, status, uuid, farmer_name, village_name, date_added, kml_export_count, last_kml_export_date, evaluation_status
                FROM polygon_data 
                ORDER BY date_added DESC
            """) 
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"DB: Error fetching polygon data for display: {e}")
            return []

    def get_polygon_data_by_id(self, record_id):
        """Fetches a full polygon record by its database ID."""
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
        """Updates the KML export count and date for a given record ID."""
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
        if not isinstance(record_id_list, list): record_id_list = [record_id_list]
        if not record_id_list: return False # No IDs to delete
        try:
            placeholders = ','.join(['?'] * len(record_id_list))
            self.cursor.execute(f"DELETE FROM polygon_data WHERE id IN ({placeholders})", record_id_list)
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"DB: Error deleting polygon data: {e}")
            return False

    def delete_all_polygon_data(self):
        try:
            self.cursor.execute("DELETE FROM polygon_data")
            # Optionally, reset the autoincrement sequence if desired (usually not necessary)
            # self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='polygon_data';")
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"DB: Error deleting all polygon data: {e}")
            return False

    def update_evaluation_status(self, record_id, status):
        """Updates the evaluation_status for a given record ID."""
        try:
            current_time_iso = datetime.datetime.now().isoformat()
            self.cursor.execute("""
                UPDATE polygon_data
                SET evaluation_status = ?,
                    last_modified = ?
                WHERE id = ?
            """, (status, current_time_iso, record_id))
            self.conn.commit()
            return self.cursor.rowcount > 0 # True if a row was updated
        except sqlite3.Error as e:
            print(f"DB: Error updating evaluation_status for ID '{record_id}': {e}")
            return False

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None # Mark as closed
            # print("Database connection closed.")

if __name__ == '__main__':
    # Example Usage (for testing this module directly)
    print("Testing DatabaseManager...")
    # Create a temporary DB for testing or use the default path
    # For isolated testing, you might want to pass a specific test DB name
    db_manager = DatabaseManager(db_path="temp_v5_test.db")
    print(f"Using database at: {db_manager.db_path}")

    # Test mWater sources
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
        # db_manager.delete_mwater_source(source_id1)
        # print(f"Deleted source 1. Remaining sources: {db_manager.get_mwater_sources()}")

    # Test polygon data
    print("\n--- Testing Polygon Data ---")
    sample_poly_data1 = {
        "uuid": "uuid-test-001", "response_code": "rc-test-001", "farmer_name": "Test Farmer 1",
        "village_name": "Test Village", "status": "valid_for_kml", "evaluation_status": "Eligible", # Added for testing
        "p1_utm_str": "43Q 123 456", "p1_altitude": 100.0, "p1_easting": 123.0, "p1_northing": 456.0, "p1_zone_num": 43, "p1_zone_letter": "Q",
        # ... (add other point data if needed for full test)
    }
    sample_poly_data2 = {
        "uuid": "uuid-test-002", "response_code": "rc-test-002", "farmer_name": "Test Farmer 2",
        "village_name": "Another Village", "status": "error_missing_points", "error_messages": "Point 3 missing", "evaluation_status": "Not Evaluated Yet",
        # ...
    }

    poly_id1 = db_manager.add_or_update_polygon_data(sample_poly_data1)
    poly_id2 = db_manager.add_or_update_polygon_data(sample_poly_data2)
    print(f"Added polygon 1 ID: {poly_id1}")
    print(f"Added polygon 2 ID: {poly_id2}")

    if poly_id1:
        print(f"Updating evaluation status for ID {poly_id1} to 'Not Eligible'")
        db_manager.update_evaluation_status(poly_id1, "Not Eligible")
        updated_record = db_manager.get_polygon_data_by_id(poly_id1)
        print(f"Record {poly_id1} after status update: {updated_record.get('evaluation_status')}")


    # Test duplicate handling (skip)
    poly_id1_again = db_manager.add_or_update_polygon_data(sample_poly_data1, overwrite=False)
    print(f"Attempted to add polygon 1 again (no overwrite), result ID: {poly_id1_again}") # Should be same as poly_id1

    # Test duplicate handling (overwrite)
    sample_poly_data1_updated = sample_poly_data1.copy()
    sample_poly_data1_updated["farmer_name"] = "Test Farmer 1 Updated Name"
    sample_poly_data1_updated["evaluation_status"] = "Eligible" # Update for overwrite
    poly_id1_overwrite = db_manager.add_or_update_polygon_data(sample_poly_data1_updated, overwrite=True)
    print(f"Attempted to add polygon 1 again (overwrite), result ID: {poly_id1_overwrite}")

    all_polys = db_manager.get_all_polygon_data_for_display()
    print(f"All polygon data for display ({len(all_polys)} records):")
    for poly_row in all_polys:
        print(poly_row)
    
    if poly_id1_overwrite: # Use the ID from the overwritten record if it exists
        full_poly1 = db_manager.get_polygon_data_by_id(poly_id1_overwrite)
        print(f"\nFull data for polygon ID {poly_id1_overwrite}: {full_poly1}")
        if full_poly1:
            db_manager.update_kml_export_status(poly_id1_overwrite)
            updated_poly1 = db_manager.get_polygon_data_by_id(poly_id1_overwrite)
            print(f"Updated KML export status for ID {poly_id1_overwrite}: Count={updated_poly1.get('kml_export_count')}, Date={updated_poly1.get('last_kml_export_date')}")

    # db_manager.delete_all_polygon_data()
    # print("\nDeleted all polygon data.")
    # print(f"Polygon data after delete all: {db_manager.get_all_polygon_data_for_display()}")

    db_manager.close()
    print("\nDatabaseManager tests finished.")

    # To clean up the test database file (if created in current dir):
    # test_db_file = "temp_v5_test.db"
    # if os.path.exists(test_db_file):
    #     os.remove(test_db_file)
    #     print(f"Removed test database: {test_db_file}")
