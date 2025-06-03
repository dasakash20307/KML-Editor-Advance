import os
import sys # Not directly used in these methods but often by os related tasks. Keeping for now.
import csv
import datetime
import uuid
import simplekml

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QMessageBox, QFileDialog, QApplication

# Assuming these are correctly placed and contain necessary components
from core.data_processor import process_csv_row_data, CSV_HEADERS, process_api_row_data
from core.api_handler import fetch_data_from_mwater_api
from core.kml_generator import add_polygon_to_kml_object
from core.kml_utils import merge_kml_files
# from database.db_manager import DatabaseManager # Type hinted in __init__
# from core.credential_manager import CredentialManager # Type hinted in __init__
# from .lock_handlers import LockHandler # Type hinted in __init__
from .dialogs import APIImportProgressDialog # APIImportProgressDialog is already correctly imported due to previous subtask

# Local constant, simplified from main_window.py's CSV_HEADERS
# Only 'response_code' key was used for non-API data in _process_imported_data.
LOCAL_CSV_RESPONSE_CODE_HEADER = "Response Code"

class DataHandler(QObject):
    data_changed_signal = Signal()
    request_main_window_reference = Signal() # To ask MainWindow for itself, if needed for dialogs

    def __init__(self, main_window_ref, db_manager, credential_manager, lock_handler,
                 log_message_callback, update_status_bar_callback,
                 source_model, table_view, api_field_to_db_map, parent=None): # Added api_field_to_db_map
        super().__init__(parent)
        self.main_window_ref = main_window_ref
        self.db_manager = db_manager
        self.credential_manager = credential_manager
        self.lock_handler = lock_handler
        self.log_message_callback = log_message_callback
        self.update_status_bar_callback = update_status_bar_callback # For methods that use it
        self.source_model = source_model
        self.table_view = table_view
        self.API_FIELD_TO_DB_FIELD_MAP = api_field_to_db_map


    def update_evaluation_status_in_db(self, record_id: int, new_status: str):
        self.log_message_callback(f"Attempting to update evaluation status for DB ID {record_id} to '{new_status}'.", "info")

        def db_operation():
            success = self.db_manager.update_evaluation_status(record_id, new_status)
            if success:
                self.log_message_callback(f"Successfully updated evaluation status for DB ID {record_id} to '{new_status}' in DB.", "info")
                self.data_changed_signal.emit()
            else:
                self.log_message_callback(f"Failed to update evaluation status for DB ID {record_id} in DB.", "error")
                QMessageBox.warning(self.main_window_ref, "DB Error", f"Failed to update evaluation status in database for ID {record_id}.")
            return success

        operation_desc = f"Updating evaluation status for DB ID {record_id} via DataHandler"
        args_for_retry = [record_id, new_status]

        success = self.lock_handler._execute_db_operation_with_lock(
            operation_callable=db_operation,
            operation_desc=operation_desc,
            lock_duration=15,
            retry_callable_for_timer=self.update_evaluation_status_in_db, # Pass the method itself
            args_for_retry_callable=args_for_retry
        )
        if not success:
            self.log_message_callback(f"Evaluation status update for DB ID {record_id} ultimately failed. Refreshing table (signal).", "warning")
            self.data_changed_signal.emit()
        return success

    def handle_import_csv(self):
        filepath, _ = QFileDialog.getOpenFileName(self.main_window_ref, "Select CSV File", os.path.expanduser("~/Documents"), "CSV files (*.csv);;All files (*.*)")
        if not filepath:
            self.log_message_callback("CSV import cancelled by user (file dialog).", "info")
            return
        
        self.log_message_callback(f"Attempting to load CSV: {filepath}", "info")
        try:
            with open(filepath, mode='r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                if not rows:
                    self.log_message_callback(f"CSV file '{filepath}' is empty or has no data rows.", "info")
                    QMessageBox.information(self.main_window_ref, "CSV Import", "The selected CSV file is empty or contains no data.")
                    return
            
            # Define a worker function for CSV processing to be wrapped by the DB lock
            def do_csv_import_processing():
                # Call _process_imported_data, ensuring it handles CSV specific logic
                # The 'is_api_data=False' flag will guide _process_imported_data
                return self._process_imported_data(rows, f"CSV '{os.path.basename(filepath)}'", is_api_data=False)

            # Execute the CSV import processing within a database lock
            operation_desc = f"Processing CSV import from '{os.path.basename(filepath)}'"
            
            # The _execute_db_operation_with_lock expects operation_callable to return True on success, False on failure or exception
            # We'll need to ensure _process_imported_data (or the wrapper) adheres to this or adapt.
            # For now, assume _process_imported_data will run to completion or raise an exception handled by the lock handler.
            # A simple way is to have do_csv_import_processing return True if no major exceptions occur during its run.
            # The actual success (how many rows imported) is logged internally by _process_imported_data.

            success_status = self.lock_handler._execute_db_operation_with_lock(
                operation_callable=do_csv_import_processing,
                operation_desc=operation_desc,
                # lock_duration can be dynamic based on number of rows, e.g., len(rows) * 0.5 seconds
                lock_duration=max(30, len(rows) * 0.5), # At least 30s, 0.5s per row
                # retry_callable_for_timer: For CSV, retry might be complex if partial data was processed.
                # For now, not providing a direct retry mechanism for the whole CSV batch via timer.
                # User can re-initiate the import.
                retry_callable_for_timer=None 
            )
            
            if success_status: # This means the lock was acquired and operation_callable completed without unhandled error
                self.log_message_callback(f"CSV import operation for '{filepath}' completed (see logs for details on rows).", "info")
            else: # This means lock acquisition failed or operation_callable itself indicated failure (e.g. returned False)
                self.log_message_callback(f"CSV import operation for '{filepath}' failed or was aborted (e.g. lock issue).", "error")
                # QMessageBox.warning(self.main_window_ref, "CSV Import Failed", f"Could not complete the CSV import from '{filepath}'. Check logs.")
            
            # Refresh data regardless of detailed outcome, as some rows might have been processed before a potential issue
            self.data_changed_signal.emit()

        except Exception as e:
            self.log_message_callback(f"Error reading or preparing CSV '{filepath}' for processing: {e}", "error")
            QMessageBox.critical(self.main_window_ref, "CSV Read Error", f"Could not read or prepare CSV file for processing:\n{e}")

    def handle_fetch_from_api(self, url=None, title=None, api_source_combo_toolbar=None): # api_source_combo_toolbar added for direct call
        selected_api_url = None
        selected_api_title = None

        if url and title:
            selected_api_url, selected_api_title = url, title
            self.log_message_callback(f"Fetching directly from API (via dialog):{selected_api_title}...", "info")
        elif api_source_combo_toolbar: # Check if the combo box was passed
            selected_api_title = api_source_combo_toolbar.currentText()
            selected_api_url = api_source_combo_toolbar.currentData()
            if not selected_api_url:
                QMessageBox.information(self.main_window_ref, "API Fetch", "No API source selected from dropdown or URL is missing.")
                return
            self.log_message_callback(f"Fetching from selected API (dropdown):{selected_api_title}...", "info")
        else: # Fallback or error
             self.log_message_callback("API fetch called without URL/title or combo box reference.", "error")
             QMessageBox.warning(self.main_window_ref, "API Fetch Error", "API source information not provided.")
             return

        rows_from_api, error_msg = fetch_data_from_mwater_api(selected_api_url, selected_api_title)
        if error_msg:
            self.log_message_callback(f"API Fetch Error ({selected_api_title}):{error_msg}", "error")
            QMessageBox.warning(self.main_window_ref, "API Fetch Error", error_msg)
            return
        if rows_from_api is not None:
            self._process_imported_data(rows_from_api, selected_api_title, is_api_data=True, api_map=self.API_FIELD_TO_DB_FIELD_MAP)
        else:
            self.log_message_callback(f"No data returned or error for {selected_api_title}.", "info")

    def _process_imported_data(self, row_list, source_description, is_api_data=False, api_map=None):
        if not row_list:
            self.log_message_callback(f"No data rows found in {source_description}.", "info")
            return

        if is_api_data and not api_map:
            self.log_message_callback(f"API data processing aborted: api_map not provided for {source_description}.", "error")
            QMessageBox.critical(self.main_window_ref, "Processing Error", "API map is missing for API data processing.")
            return
        
        if is_api_data:
            cleaned_row_list = []
            for api_row_original_keys in row_list:
                cleaned_row_list.append({k.lstrip('\ufeff'): v for k, v in api_row_original_keys.items()})
            row_list = cleaned_row_list
            self.log_message_callback("Cleaned BOM characters from API data keys.", "info")
            if row_list: self.log_message_callback(f"API Data Keys (first row after BOM cleaning):{list(row_list[0].keys())}", "info")

        if not self.credential_manager:
            self.log_message_callback("Credential Manager not available.", "error")
            QMessageBox.critical(self.main_window_ref, "Error", "Credential Manager not available.")
            return False # Indicate failure for _execute_db_operation_with_lock if this path is hit

        kml_root_path = self.credential_manager.get_kml_folder_path()
        device_id = self.credential_manager.get_device_id()
        device_nickname = self.credential_manager.get_device_nickname()

        if not kml_root_path or not device_id:
            self.log_message_callback("KML root path or device ID not set.", "error")
            QMessageBox.warning(self.main_window_ref, "Configuration Error", "KML root path or device ID not set.")
            return False # Indicate failure

        progress_dialog = APIImportProgressDialog(self.main_window_ref)
        progress_dialog.set_total_records(len(row_list))
        progress_dialog.show()
        
        processed_in_loop, skipped_in_loop, new_added_in_loop = 0, 0, 0
        # overall_success will be True if the loop completes, False if user cancels early
        overall_success = True 

        for i, original_row_dict in enumerate(row_list):
            # DB Heartbeat for long operations
            if not is_api_data and self.lock_handler.db_lock_manager: # Only for CSV import under DB lock
                 self.lock_handler.db_lock_manager.update_heartbeat()

            processed_in_loop += 1
            current_errors = []
            rc_from_row = "" # Response code from the current row

            # Determine response_code based on data type
            if is_api_data and api_map: # API Data
                # Find the API key that maps to the "response_code" database field
                api_rc_key = next((key for key, db_field in api_map.items() if db_field == "response_code"), None)
                if api_rc_key:
                    rc_from_row = original_row_dict.get(api_rc_key, "").strip()
            else: # CSV Data - use CSV_HEADERS to find the response code
                  # CSV_HEADERS maps internal names to user-facing CSV column names.
                  # We need the user-facing name for 'response_code'.
                response_code_csv_header = CSV_HEADERS.get("response_code")
                if response_code_csv_header:
                    # BOM characters were stripped from keys of original_row_dict at the start of process_csv_row_data
                    # but if _process_imported_data gets raw CSV rows, it needs to handle BOM for key lookup.
                    # Assuming original_row_dict keys are clean here for CSV if process_csv_row_data handles it.
                    # If not, we'd need: cleaned_original_row_dict = {k.lstrip('\ufeff'): v for k,v in original_row_dict.items()}
                    # For now, assume original_row_dict is okay for CSV or process_csv_row_data handles it.
                    rc_from_row = original_row_dict.get(response_code_csv_header, "").strip()


            if not rc_from_row: # If response code is still empty after trying to find it
                msg = f"Row {i+1} from {source_description} skipped: Response Code is missing or could not be identified."
                self.log_message_callback(msg, "error"); current_errors.append("Missing or unidentified Response Code.")
                skipped_in_loop += 1
                progress_dialog.update_progress(processed_in_loop, skipped_in_loop, new_added_in_loop)
                if progress_dialog.was_cancelled(): overall_success = False; break
                continue

            # Check for duplicate response_code in DB
            if self.db_manager.check_duplicate_response_code(rc_from_row):
                self.log_message_callback(f"Skipped duplicate RC '{rc_from_row}'.", "info")
                skipped_in_loop += 1
                progress_dialog.update_progress(processed_in_loop, skipped_in_loop, new_added_in_loop)
                if progress_dialog.was_cancelled(): overall_success = False; break
                continue
            
            # Process data (API or CSV)
            if is_api_data:
                processed_flat = process_api_row_data(original_row_dict, api_map)
            else: # CSV Data
                processed_flat = process_csv_row_data(original_row_dict) # Uses updated V5 processor

            # Ensure UUID exists or generate one
            if not processed_flat.get("uuid"):
                generated_uuid = str(uuid.uuid4())
                self.log_message_callback(f"UUID missing for RC '{rc_from_row}'. Generated: {generated_uuid}", "warning")
                current_errors.append(f"UUID missing, generated: {generated_uuid}")
                processed_flat["uuid"] = generated_uuid
            
            # Accumulate processing errors
            if processed_flat.get('error_messages'):
                # error_messages from processor might be a string or list
                if isinstance(processed_flat['error_messages'], str):
                    current_errors.append(f"Data processing issues: {processed_flat['error_messages']}")
                elif isinstance(processed_flat['error_messages'], list): # Should be list of strings
                    current_errors.extend(processed_flat['error_messages'])
            
            # KML generation and saving logic
            kml_file_name = f"{processed_flat['uuid']}.kml"
            full_kml_path = os.path.join(kml_root_path, kml_file_name)
            kml_content_ok = False
            kml_saved_successfully = False
            lock_acquired_for_kml = False
            kml_file_status_for_db = "Errored" # Default KML status

            if processed_flat.get('status') == 'valid_for_kml':
                kml_op_description = f"Creating KML {kml_file_name} during import ({source_description})"
                
                if self.lock_handler.kml_file_lock_manager:
                    try:
                        kml_lock_status = self.lock_handler.kml_file_lock_manager.acquire_kml_lock(kml_file_name, operation_description=kml_op_description)
                        if kml_lock_status is True:
                            lock_acquired_for_kml = True
                        elif kml_lock_status == "STALE_LOCK_DETECTED":
                            self.log_message_callback(f"Overriding stale KML lock for '{kml_file_name}' for new import.", "warning")
                            if self.lock_handler.kml_file_lock_manager.force_acquire_kml_lock(kml_file_name, operation_description=kml_op_description):
                                lock_acquired_for_kml = True
                            else:
                                current_errors.append(f"Failed to force acquire stale KML lock for {kml_file_name}.")
                                kml_file_status_for_db = "Error - KML Lock Failed"
                        elif kml_lock_status is False: # Busy
                            current_errors.append(f"KML lock busy for {kml_file_name}.")
                            kml_file_status_for_db = "Error - KML Lock Failed"
                        else: # ERROR
                            current_errors.append(f"KML lock acquisition error for {kml_file_name}.")
                            kml_file_status_for_db = "Error - KML Lock Failed"

                        if lock_acquired_for_kml:
                            kml_doc = simplekml.Kml()
                            kml_content_ok = add_polygon_to_kml_object(kml_doc, processed_flat) # This calls create_kml_description
                            if not kml_content_ok:
                                current_errors.append("Failed KML content generation (geometry/description error).")
                            else:
                                try:
                                    kml_doc.save(full_kml_path)
                                    kml_saved_successfully = True
                                    kml_file_status_for_db = "Created"
                                    self.log_message_callback(f"KML saved: {full_kml_path}", "info")
                                except Exception as e_kml_save:
                                    current_errors.append(f"Failed KML save for '{full_kml_path}': {e_kml_save}")
                                    self.log_message_callback(f"KML Save Exception for {processed_flat['uuid']}: {e_kml_save}", "error")
                    finally: # Ensure KML lock is released if it was acquired
                        if lock_acquired_for_kml:
                            self.lock_handler.kml_file_lock_manager.release_kml_lock(kml_file_name)
                else: # KMLFileLockManager not available
                    current_errors.append(f"KML lock manager unavailable for {kml_file_name}.")
                    kml_file_status_for_db = "Error - KML Lock Manager Unavailable"
            else: # Not valid_for_kml
                msg = f"Skipping KML generation for RC '{rc_from_row}' (UUID {processed_flat['uuid']}), status: '{processed_flat.get('status')}'"
                current_errors.append(msg); self.log_message_callback(msg, "info")
                # kml_file_status_for_db remains "Errored" or could be more specific like "Error - Invalid Data"

            # Prepare data for DB insertion
            db_data = processed_flat.copy()
            db_data['kml_file_name'] = kml_file_name
            db_data['kml_file_status'] = kml_file_status_for_db
            
            # <<<< ADD INITIAL PLACEMARK NAME >>>>
            # add_polygon_to_kml_object sets polygon.name using processed_flat.get("uuid", "Unnamed Polygon")
            # or the name from the original data record if it existed and was mapped.
            # For consistency, let's assume the initial name is based on UUID or a default.
            # If processed_flat contains a 'name' or 'placemark_name' field mapped from API/CSV for the KML, use that.
            # Otherwise, default to UUID.
            initial_placemark_name = processed_flat.get("name_for_kml_placemark", processed_flat.get("uuid", "Unnamed Polygon"))
            db_data['kml_placemark_name'] = initial_placemark_name

            if is_api_data: # API data might have device_code from source
                db_data['device_code'] = processed_flat.get('device_code', device_id) # Use API's if present, else this app's
            else: # CSV data always uses this app's device_id as creator
                db_data['device_code'] = device_id
            
            db_data['editor_device_id'] = device_id # Current app instance is the editor/importer
            db_data['editor_device_nickname'] = device_nickname
            
            db_data.pop('status', None) # Remove temp processing status, not a direct DB field for polygon_data.status
            
            final_error_messages = "\n".join(filter(None, current_errors))
            db_data['error_messages'] = final_error_messages if final_error_messages else None
            
            current_time_iso = datetime.datetime.now().isoformat()
            db_data["last_modified"] = current_time_iso
            # For CSV imports, date_added is always now. For API, it might come from source.
            if not is_api_data or not processed_flat.get("date_added"):
                db_data["date_added"] = current_time_iso
            # Else, if it's API data and date_added was in processed_flat, it's already in db_data

            # Add/Update record in DB
            db_result_id = self.db_manager.add_or_update_polygon_data(db_data, overwrite=False)
                
            if db_result_id is not None:
                new_added_in_loop += 1
                self.log_message_callback(f"RC'{rc_from_row}'(UUID {db_data['uuid']}) saved to DB ID {db_result_id}. KML: {db_data['kml_file_status']}.", "info")
            else: # DB save failed
                self.log_message_callback(f"Failed to save RC'{rc_from_row}'(UUID {db_data['uuid']}) to DB.", "error")
                skipped_in_loop += 1
            
            # Update progress dialog
            progress_dialog.update_progress(processed_in_loop, skipped_in_loop, new_added_in_loop)
            if progress_dialog.was_cancelled():
                self.log_message_callback("Import cancelled by user.", "info")
                overall_success = False # Mark as not fully successful due to cancellation
                break
        
        progress_dialog.close()
        # self.data_changed_signal.emit() # Emit signal outside if this function is called by the lock wrapper
        self.log_message_callback(f"Import from {source_description}: Attempted: {processed_in_loop}, New Added: {new_added_in_loop}, Skipped: {skipped_in_loop}.", "info")
        return overall_success # Return status for the lock handler

    def handle_export_displayed_data_csv(self):
        # model_to_export is self.table_view.model() which is the proxy model
        model_to_export = self.table_view.model() 
        if not model_to_export or model_to_export.rowCount() == 0:
            QMessageBox.information(self.main_window_ref, "Export Data", "No data to export.")
            return

        filepath, _ = QFileDialog.getSaveFileName(self.main_window_ref, "Save Displayed Data As CSV", os.path.expanduser("~/Documents/dilasa_displayed_data.csv"), "CSV Files (*.csv)")
        if not filepath:
            return
        try:
            # headers are from the source model (PolygonTableModel)
            headers = self.source_model._headers 
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers[1:]) # Skip checkbox column header
                for row in range(model_to_export.rowCount()):
                    row_data = [model_to_export.data(model_to_export.index(row, col)) for col in range(1, model_to_export.columnCount())]
                    writer.writerow(row_data)
            self.log_message_callback(f"Data exported to {filepath}", "success")
            QMessageBox.information(self.main_window_ref, "Export Successful", f"{model_to_export.rowCount()} displayed records exported to:\n{filepath}")
        except Exception as e:
            self.log_message_callback(f"Error exporting CSV:{e}", "error")
            QMessageBox.critical(self.main_window_ref, "Export Error", f"Could not export data:{e}")

    def handle_delete_checked_rows(self):
        checked_db_ids = self.source_model.get_checked_item_db_ids()
        if not checked_db_ids:
            QMessageBox.information(self.main_window_ref, "Delete Checked", "No records checked.")
            return

        kml_folder_path = self.credential_manager.get_kml_folder_path()
        if not kml_folder_path:
            self.log_message_callback("KML folder path not configured. Cannot check KML locks for deletion.", "error")
            QMessageBox.critical(self.main_window_ref, "Configuration Error", "KML folder path is not configured. KML files cannot be managed.")
            return
        
        if not self.lock_handler.kml_file_lock_manager:
             self.log_message_callback("KMLFileLockManager not available. Proceeding with DB deletion only.", "error")
             QMessageBox.warning(self.main_window_ref, "KML Lock Error", "KML Lock Manager is not available. KML files will not be deleted (if locked by others).")
             # Simplified: just try to delete from DB
             def db_only_op():
                 if QMessageBox.question(self.main_window_ref, "Confirm Delete (DB Only)", f"Delete {len(checked_db_ids)} record(s) from DB (KMLs not checked)?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                     if self.db_manager.delete_polygon_data(checked_db_ids):
                         self.log_message_callback(f"{len(checked_db_ids)} DB record(s) deleted.", "info")
                         return True
                     self.log_message_callback("DB deletion failed.", "error"); return False
                 return False
             
             op_success = self.lock_handler._execute_db_operation_with_lock(
                 db_only_op, f"Deleting {len(checked_db_ids)} DB records (KMLs not checked)",
                 retry_callable_for_timer=self.handle_delete_checked_rows # Pass the public method for retry
             )
             if op_success: self.data_changed_signal.emit()
             return

        db_ids_to_delete = []
        kml_paths_to_delete = []
        skipped_locked_kmls_info = []

        for db_id in checked_db_ids:
            record_data = self.db_manager.get_polygon_data_by_id(db_id) # Fetches full record
            if not record_data:
                self.log_message_callback(f"Record with DB ID {db_id} not found for deletion. Skipping.", "warning")
                continue
            
            kml_file_name = record_data.get('kml_file_name')
            can_delete_this_record = True

            if kml_file_name and isinstance(kml_file_name, str) and kml_file_name.strip():
                lock_info = self.lock_handler.kml_file_lock_manager.get_kml_lock_info(kml_file_name)
                if lock_info:
                    current_device_id = self.credential_manager.get_device_id()
                    if lock_info.get('holder_device_id') != current_device_id:
                        # Check for staleness (simplified check, real KMLFileLockManager has more robust logic)
                        is_stale = False # Assume KMLFileLockManager handles staleness on acquire
                        try:
                            heartbeat_dt = datetime.datetime.fromisoformat(lock_info.get('heartbeat_time_iso'))
                            if heartbeat_dt.tzinfo is None: heartbeat_dt = heartbeat_dt.replace(tzinfo=datetime.timezone.utc)
                            # Example: stale if older than 1 hour ( KML_LOCK_RETRY_TIMEOUT_MS * MAX_KML_LOCK_RETRIES could be a guide)
                            if heartbeat_dt + datetime.timedelta(seconds=3600) < datetime.datetime.now(datetime.timezone.utc):
                                is_stale = True
                        except: # Invalid date format
                            is_stale = True 
                        
                        if not is_stale: # Actively locked by other
                            skipped_locked_kmls_info.append((kml_file_name, lock_info.get('holder_nickname', 'Unknown')))
                            self.log_message_callback(f"Skipping KML '{kml_file_name}' (DB ID {db_id}), locked by {lock_info.get('holder_nickname', 'Unknown')}.", "warning")
                            can_delete_this_record = False
                        else:
                             self.log_message_callback(f"KML '{kml_file_name}' has a stale lock by {lock_info.get('holder_nickname', 'Unknown')}. Will attempt deletion.", "info")


            if can_delete_this_record:
                db_ids_to_delete.append(db_id)
                if kml_file_name and isinstance(kml_file_name, str) and kml_file_name.strip():
                     kml_paths_to_delete.append(os.path.join(kml_folder_path, kml_file_name.strip()))
        
        if skipped_locked_kmls_info:
            msg = "The following KML files (and their DB records) seem locked by other users/processes and were not included in this delete operation:\n"
            for name, holder in skipped_locked_kmls_info: msg += f"- '{name}' (locked by {holder})\n"
            QMessageBox.information(self.main_window_ref, "Some Deletions Skipped", msg)

        if not db_ids_to_delete:
            self.log_message_callback("No records eligible for deletion after KML lock checks.", "info")
            if not skipped_locked_kmls_info:
                 QMessageBox.information(self.main_window_ref, "Delete Checked", "No records were eligible for deletion (e.g. all locked or none found).")
            return

        def actual_delete_operation():
            confirm_msg = f"Delete {len(db_ids_to_delete)} DB record(s)"
            if kml_paths_to_delete: confirm_msg += f" and {len(kml_paths_to_delete)} associated KML file(s)"
            confirm_msg += " permanently?"

            if QMessageBox.question(self.main_window_ref, "Confirm Delete", confirm_msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                db_delete_success = True
                if db_ids_to_delete:
                    if not self.db_manager.delete_polygon_data(db_ids_to_delete):
                        self.log_message_callback("Failed to delete records from database.", "error")
                        QMessageBox.warning(self.main_window_ref, "DB Error", "Could not delete records from the database.")
                        db_delete_success = False
                    else:
                        self.log_message_callback(f"{len(db_ids_to_delete)} DB record(s) deleted.", "info")
                
                if not db_delete_success: return False

                kml_errors = 0
                for path in kml_paths_to_delete:
                    if os.path.exists(path):
                        kml_fname_only = os.path.basename(path)
                        # Attempt to acquire lock to ensure we are the one deleting it and can clean up .lock file
                        lock_op_desc_kml = f"Finalizing KML deletion for {kml_fname_only}"
                        # Using LockHandler's method, but this is nested. This specific call might be simplified
                        # as KMLFileLockManager itself handles lock files on delete if designed so.
                        # For now, explicit lock/release around os.remove.
                        kml_lock_status = self.lock_handler.kml_file_lock_manager.acquire_kml_lock(kml_fname_only, lock_op_desc_kml, 10)
                        
                        if kml_lock_status is True or kml_lock_status == "STALE_LOCK_DETECTED": # Allow deleting if stale
                            if kml_lock_status == "STALE_LOCK_DETECTED":
                                self.log_message_callback(f"Forcing acquire of stale lock for KML {kml_fname_only} for deletion.", "warning")
                                self.lock_handler.kml_file_lock_manager.force_acquire_kml_lock(kml_fname_only, lock_op_desc_kml, 10)

                            try:
                                os.remove(path)
                                self.log_message_callback(f"KML file '{kml_fname_only}' deleted.", "info")
                            except Exception as e_kml_del:
                                self.log_message_callback(f"Error deleting KML file '{kml_fname_only}': {e_kml_del}", "error")
                                kml_errors += 1
                            finally:
                                self.lock_handler.kml_file_lock_manager.release_kml_lock(kml_fname_only)
                        else: # Busy or Error
                            self.log_message_callback(f"Could not acquire lock for KML file '{kml_fname_only}' before deletion. Skipping file deletion.", "warning")
                            kml_errors +=1
                    else:
                         self.log_message_callback(f"KML file '{os.path.basename(path)}' not found for deletion.", "info")
                
                if kml_errors > 0:
                    QMessageBox.warning(self.main_window_ref, "KML Deletion Errors", f"{kml_errors} KML file(s) encountered issues during deletion. Check logs.")
                
                self.data_changed_signal.emit()
                return True
            else:
                self.log_message_callback("Delete operation cancelled by user.", "info")
                return False

        self.lock_handler._execute_db_operation_with_lock(
            actual_delete_operation, 
            f"Deleting {len(db_ids_to_delete)} DB records and KMLs",
            retry_callable_for_timer=self.handle_delete_checked_rows # Pass the public method for retry
        )
        
    def handle_clear_all_data(self):
        if not self.credential_manager or self.credential_manager.get_app_mode() != "Central App":
            self.log_message_callback("Clear all data attempted in non-Central App mode or missing CredentialManager.", "error")
            QMessageBox.warning(self.main_window_ref, "Operation Not Allowed", "Clearing all data is only permitted in 'Central App' mode.")
            return

        def do_clear_operation():
            if QMessageBox.question(self.main_window_ref, "Confirm Clear All Database Data",
                                    "Delete ALL polygon data from the database permanently?\nThis includes associated KML files if possible.\nThis cannot be undone.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                
                all_records = self.db_manager.get_all_polygon_data_for_display() # Get records before deleting from DB
                kml_deletion_errors = 0
                kml_folder_path = self.credential_manager.get_kml_folder_path()

                if not self.db_manager.delete_all_polygon_data():
                    self.log_message_callback("Failed to clear all data from database.", "error")
                    QMessageBox.warning(self.main_window_ref, "DB Error", "Could not clear all data from the database.")
                    return False
                
                self.log_message_callback("All polygon data deleted from database.", "info")
                if self.source_model: self.source_model._check_states.clear() # Clear checks in UI model

                if all_records and kml_folder_path and self.lock_handler.kml_file_lock_manager:
                    self.log_message_callback(f"Attempting to delete {len(all_records)} KML files...", "info")
                    for record_tuple in all_records:
                        kml_file_name = record_tuple[10] # kml_file_name is at index 10
                        if kml_file_name and isinstance(kml_file_name, str) and kml_file_name.strip():
                            full_kml_path = os.path.join(kml_folder_path, kml_file_name)
                            if os.path.exists(full_kml_path):
                                lock_op_desc_kml = f"Clearing KML {kml_file_name} during all data wipe"
                                kml_lock_status = self.lock_handler.kml_file_lock_manager.acquire_kml_lock(kml_file_name, lock_op_desc_kml, 10)
                                if kml_lock_status is True or kml_lock_status == "STALE_LOCK_DETECTED":
                                    if kml_lock_status == "STALE_LOCK_DETECTED":
                                         self.lock_handler.kml_file_lock_manager.force_acquire_kml_lock(kml_file_name, lock_op_desc_kml, 10)
                                    try:
                                        os.remove(full_kml_path)
                                        self.log_message_callback(f"Deleted KML: {kml_file_name}", "info")
                                    except Exception as e_del_kml:
                                        self.log_message_callback(f"Error deleting KML {kml_file_name}: {e_del_kml}", "error")
                                        kml_deletion_errors += 1
                                    finally:
                                        self.lock_handler.kml_file_lock_manager.release_kml_lock(kml_file_name)
                                else:
                                    self.log_message_callback(f"Could not acquire lock for KML {kml_file_name}. It may not be deleted.", "warning")
                                    kml_deletion_errors +=1
                
                if kml_deletion_errors > 0:
                     QMessageBox.warning(self.main_window_ref, "KML Deletion Issues", f"{kml_deletion_errors} KML file(s) encountered issues during deletion. Check logs.")

                self.data_changed_signal.emit()
                return True
            else:
                self.log_message_callback("Clear all data operation cancelled by user.", "info")
                return False

        self.lock_handler._execute_db_operation_with_lock(
            do_clear_operation, 
            "Clearing all KML files and database records",
            lock_duration=120, # Longer duration for potentially many KML files
            retry_callable_for_timer=self.handle_clear_all_data
        )

    def handle_generate_kml(self, output_mode_dialog_class, kml_output_mode=None):
        checked_db_ids = self.source_model.get_checked_item_db_ids()
        if not checked_db_ids:
            QMessageBox.information(self.main_window_ref, "Export KMLs", "No records checked.")
            return

        primary_kml_storage_path = self.credential_manager.get_kml_folder_path()
        if not primary_kml_storage_path:
            self.log_message_callback("Primary KML storage path not configured. Cannot export KMLs.", "error")
            QMessageBox.critical(self.main_window_ref, "Configuration Error", "Primary KML storage path is not configured.")
            return

        records_with_kml_files = []
        missing_kml_info = []
        for db_id in checked_db_ids:
            record = self.db_manager.get_polygon_data_by_id(db_id)
            if record:
                kml_file_name = record.get('kml_file_name')
                if kml_file_name and isinstance(kml_file_name, str) and kml_file_name.strip():
                    source_kml_path = os.path.join(primary_kml_storage_path, kml_file_name)
                    if os.path.exists(source_kml_path):
                        records_with_kml_files.append({
                            'id': record.get('id'), # DB ID
                            'uuid': record.get('uuid'),
                            'kml_file_name': kml_file_name,
                            'source_path': source_kml_path
                        })
                    else:
                        missing_kml_info.append(f"DB ID {db_id} (UUID: {record.get('uuid', 'N/A')}): File '{kml_file_name}' not found.")
                else:
                    missing_kml_info.append(f"DB ID {db_id} (UUID: {record.get('uuid', 'N/A')}): KML file name missing in database.")
            else:
                missing_kml_info.append(f"DB ID {db_id}: Record not found in database.")
        
        if missing_kml_info:
            self.log_message_callback(f"KML Export: Some checked records are missing KML files or data: {'; '.join(missing_kml_info)}", "warning")
            QMessageBox.warning(self.main_window_ref, "KML Files Missing",
                                "Could not find KML files for some checked records:\n- " + "\n- ".join(missing_kml_info) +
                                "\n\nOnly records with existing KML files will be processed.")

        if not records_with_kml_files:
            QMessageBox.information(self.main_window_ref, "Export KMLs", "No valid KML files found for the selected records.")
            return

        if kml_output_mode is None:
            dialog = output_mode_dialog_class(self.main_window_ref)
            kml_output_mode = dialog.get_selected_mode()
            if not kml_output_mode:
                self.log_message_callback("KML export cancelled (mode selection).", "info")
                return
        
        output_folder = QFileDialog.getExistingDirectory(self.main_window_ref, "Select Output Folder for KML Files", os.path.expanduser("~/Documents"))
        if not output_folder:
            self.log_message_callback("KML export cancelled (folder selection).", "info")
            return

        # Need to import shutil for file copying
        import shutil

        def do_kml_export_operation():
            self.log_message_callback(f"Exporting KMLs to: {output_folder} (Mode: {kml_output_mode})", "info")
            files_exported_count = 0
            ids_for_db_update = []

            if kml_output_mode == "multiple":
                for record_info in records_with_kml_files:
                    if self.lock_handler.db_lock_manager: self.lock_handler.db_lock_manager.update_heartbeat()
                    dest_kml_path = os.path.join(output_folder, record_info['kml_file_name'])
                    try:
                        shutil.copy2(record_info['source_path'], dest_kml_path)
                        files_exported_count += 1
                        ids_for_db_update.append(record_info['id'])
                        self.log_message_callback(f"Copied '{record_info['kml_file_name']}' to '{dest_kml_path}'", "info")
                    except Exception as e:
                        self.log_message_callback(f"Error copying KML '{record_info['kml_file_name']}': {e}", "error")
                
            elif kml_output_mode == "single":
                source_kml_paths = [record['source_path'] for record in records_with_kml_files]
                if not source_kml_paths:
                    self.log_message_callback("No source KML paths found for merging.", "warning")
                    # QMessageBox.information(self.main_window_ref, "KML Export", "No KML files available to merge.") # Already handled by records_with_kml_files check
                    # return False # This would prevent the generic message at the end.
                else:
                    timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    count_str = len(source_kml_paths)
                    merged_kml_filename = f"Consolidated_KML_{timestamp_str}_{count_str}files.kml"
                    full_output_path = os.path.join(output_folder, merged_kml_filename)

                    self.log_message_callback(f"Attempting to merge {len(source_kml_paths)} KML files into '{full_output_path}'.", "info")
                    
                    merge_successful = merge_kml_files(source_kml_paths, full_output_path)
                    
                    if merge_successful:
                        files_exported_count = 1 # One consolidated file is created
                        # Add all DB IDs of the records that contributed to the merged file
                        ids_for_db_update.extend([record['id'] for record in records_with_kml_files])
                        self.log_message_callback(f"Successfully merged KMLs into '{merged_kml_filename}'.", "success")
                    else:
                        self.log_message_callback(f"Failed to merge KML files into '{merged_kml_filename}'. Check console/logs for details from kml_utils.", "error")
                        # QMessageBox.warning(self.main_window_ref, "KML Merge Error", f"Could not merge KML files. See logs for details.")
                        # No files_exported_count increment, no ids_for_db_update

            # Update export status in DB only if files were actually processed
            if ids_for_db_update:
                for record_id in ids_for_db_update:
                    if self.lock_handler.db_lock_manager: self.lock_handler.db_lock_manager.update_heartbeat()
                    self.db_manager.update_kml_export_status(record_id)
                self.data_changed_signal.emit()
                
            msg = f"{files_exported_count} KML file(s) exported for {len(ids_for_db_update)} records." if files_exported_count > 0 else "No KML files were exported."
            if kml_output_mode == "single" and files_exported_count == 0 : # Adjust message if single mode was placeholder
                 msg = "Single KML export (merging) is pending implementation. No files were exported."

            self.log_message_callback(msg, "success" if files_exported_count > 0 and not (kml_output_mode == "single" and files_exported_count == 0) else "info")
            QMessageBox.information(self.main_window_ref, "KML Export", msg)
            return True

        estimated_duration = min(max(len(records_with_kml_files) * 1, 10), 300) # Copying is faster
        self.lock_handler._execute_db_operation_with_lock(
            do_kml_export_operation,
            f"Exporting {len(records_with_kml_files)} KML files",
            lock_duration=estimated_duration,
            retry_callable_for_timer=lambda: self.handle_generate_kml(output_mode_dialog_class, kml_output_mode)
        )

    def handle_export_csv_template(self):
        """
        Handles the export of a CSV template file.
        The template contains headers based on core.data_processor.CSV_HEADERS.
        """
        self.log_message_callback("CSV template export initiated.", "info")
        
        # CSV_HEADERS is already imported at the top of the file
        # from core.data_processor import CSV_HEADERS
        
        if not CSV_HEADERS:
            self.log_message_callback("CSV_HEADERS not found or empty in core.data_processor.", "error")
            QMessageBox.warning(self.main_window_ref, "Template Error", "Could not load CSV headers for the template.")
            return

        header_list = list(CSV_HEADERS.values())

        default_filename = "v5_data_template.csv"
        filepath, _ = QFileDialog.getSaveFileName(
            self.main_window_ref,
            "Save CSV Template As",
            os.path.join(os.path.expanduser("~/Documents"), default_filename), # Suggest a path and filename
            "CSV files (*.csv);;All files (*.*)"
        )

        if not filepath:
            self.log_message_callback("CSV template export cancelled by user (file dialog).", "info")
            return

        try:
            with open(filepath, mode='w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(header_list)
            
            self.log_message_callback(f"CSV template successfully exported to: {filepath}", "success")
            QMessageBox.information(self.main_window_ref, "Export Successful", f"CSV template saved to:\n{filepath}")

        except Exception as e:
            self.log_message_callback(f"Error exporting CSV template to '{filepath}': {e}", "error")
            QMessageBox.warning(self.main_window_ref, "Export Error", f"Could not save CSV template:\n{e}")
