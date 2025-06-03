import os
import tempfile
import utm # Keep for GE view if it still uses P1-P4 directly
import simplekml
import json
import datetime
import xml.etree.ElementTree as ET

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QCheckBox

from core.kml_generator import add_polygon_to_kml_object
# Import PolygonTableModel to access its constants like DB_ID_COL
from ui.table_models import PolygonTableModel
# Assuming LockHandler is in a module, e.g., core.lock_handler
# from core.lock_handler import LockHandler # This will be passed in

class KMLHandler(QObject):
    # Signal to indicate KML status might have been updated in DB, so table might need refresh
    kml_data_updated_signal = Signal()

    def __init__(self, main_window_ref, db_manager, credential_manager,
                 log_message_callback, lock_handler, # Added lock_handler
                 map_stack, kml_editor_view_widget, google_earth_view_widget, # Renamed map_view_widget
                 table_view, source_model, filter_proxy_model, parent=None):
        super().__init__(parent)
        self.main_window_ref = main_window_ref
        self.db_manager = db_manager
        self.credential_manager = credential_manager
        self.log_message_callback = log_message_callback
        self.lock_handler = lock_handler # Store lock_handler
        
        self.map_stack = map_stack
        self.kml_editor_widget = kml_editor_view_widget # Updated attribute name
        self.google_earth_view_widget = google_earth_view_widget
        
        self.table_view = table_view
        self.source_model = source_model
        self.filter_proxy_model = filter_proxy_model

        # Attributes for Google Earth KML generation (kept for now)
        self.current_temp_kml_path = None
        self.show_ge_instructions_popup_again = True

    @staticmethod
    def _parse_kml_for_name_desc(kml_content_string: str) -> tuple[str | None, str | None]:
        """
        Parses KML content string to extract Placemark name and description.
        Returns (name, description) or (None, None) on failure or if not found.
        """
        try:
            if not kml_content_string:
                return None, None
            root = ET.fromstring(kml_content_string)
            namespaces = {
                'kml': 'http://www.opengis.net/kml/2.2',
                'gx': 'http://www.google.com/kml/ext/2.2' # Google extensions, if used
            }

            # Try to find Placemark -> name
            name_el = root.find('.//kml:Placemark/kml:name', namespaces)
            if name_el is None: # Fallback if default namespace is not kml:
                name_el = root.find('.//Placemark/name', namespaces)

            name_text = name_el.text.strip() if name_el is not None and name_el.text is not None else None

            # Try to find Placemark -> description
            desc_el = root.find('.//kml:Placemark/kml:description', namespaces)
            if desc_el is None: # Fallback
                desc_el = root.find('.//Placemark/description', namespaces)

            description_text = desc_el.text.strip() if desc_el is not None and desc_el.text is not None else None

            return name_text, description_text
        except ET.ParseError as e:
            # self.log_message_callback(f"KML Parsing Error for name/desc: {e}", "error") # Needs instance or passed logger
            print(f"KMLHandler._parse_kml_for_name_desc: XML ParseError: {e}")
            return None, None
        except Exception as e:
            # self.log_message_callback(f"Unexpected error parsing KML for name/desc: {e}", "error")
            print(f"KMLHandler._parse_kml_for_name_desc: Unexpected error: {e}")
            return None, None

    def on_table_selection_changed(self, selected, deselected):
        selected_proxy_indexes = self.table_view.selectionModel().selectedRows()
        polygon_record = None
        db_id = None

        if selected_proxy_indexes:
            source_model_index = self.filter_proxy_model.mapToSource(selected_proxy_indexes[0])
            if source_model_index.isValid():
                db_id_item = self.source_model.data(source_model_index.siblingAtColumn(PolygonTableModel.DB_ID_COL))
                try:
                    db_id = int(db_id_item)
                    polygon_record = self.db_manager.get_polygon_data_by_id(db_id)
                except (ValueError, TypeError) as e:
                    self.log_message_callback(f"TableSelection: Invalid DB ID '{db_id_item}': {e}", "error")
                    polygon_record = None
                except Exception as e:
                    self.log_message_callback(f"TableSelection: Error fetching record by ID {db_id_item}: {e}", "error")
                    polygon_record = None
        
        if self.map_stack.currentIndex() == 1:  # GE View is active
            if polygon_record and polygon_record.get('status') == 'valid_for_kml':
                # This part remains for GE, which uses P1-P4 from DB record directly for a temp KML
                self._trigger_ge_polygon_upload(polygon_record)
            else:
                # self.google_earth_view_widget.clear_view() # Assuming GE view has a clear method
                self.log_message_callback("GE View: No valid polygon selected or record not valid for KML. GE view not updated.", "info")

        else:  # KML Editor View is active
            if polygon_record:
                kml_file_name = polygon_record.get('kml_file_name')
                main_kml_folder_path = self.credential_manager.get_kml_folder_path()

                if kml_file_name and isinstance(kml_file_name, str) and kml_file_name.strip() and main_kml_folder_path:
                    full_kml_path = os.path.join(main_kml_folder_path, kml_file_name.strip())

                    if os.path.exists(full_kml_path):
                        try:
                            with open(full_kml_path, 'r', encoding='utf-8') as f:
                                kml_content = f.read()

                            parsed_name, parsed_desc = self._parse_kml_for_name_desc(kml_content)

                            display_name = parsed_name if parsed_name else polygon_record.get('uuid', "Unnamed Polygon")
                            display_desc = parsed_desc if parsed_desc is not None else "No description in KML."

                            self.kml_editor_widget.display_kml(kml_content, display_name, display_desc)
                            # Store original filename and db_id in the editor widget for save context
                            self.kml_editor_widget.current_kml_filename = kml_file_name
                            self.kml_editor_widget.current_db_id = db_id

                        except Exception as e:
                            self.log_message_callback(f"Error reading or parsing KML file {full_kml_path}: {e}", "error")
                            self.kml_editor_widget.clear_map()
                            if db_id is not None: # If we have DB ID, mark as error
                                self.db_manager.update_kml_file_status(db_id, "Error Loading") # Or some other status
                                self.kml_data_updated_signal.emit()
                    else:
                        self.log_message_callback(f"KML file '{kml_file_name}' not found at '{full_kml_path}'. Updating status.", "warning")
                        self.kml_editor_widget.clear_map()
                        if db_id is not None:
                            self.db_manager.update_kml_file_status(db_id, "File Deleted")
                            self.kml_data_updated_signal.emit()
                        else:
                            self.log_message_callback("DB ID not found for selected row, KML status not updated for missing file.", "error")
                else: # No KML filename or path issue
                    self.kml_editor_widget.clear_map()
                    default_message = "No KML file associated with this record."
                    if not main_kml_folder_path: default_message = "KML folder path not configured."
                    self.log_message_callback(f"Cannot display KML: {default_message} (DB ID: {db_id if db_id is not None else 'Unknown'}).", "info")
            else: # No polygon_record selected or found
                self.kml_editor_widget.clear_map()
                self.log_message_callback("No record selected or found. KML Editor cleared.", "info")

    def save_edited_kml(self, db_id: int, original_kml_filename: str,
                        edited_geometry_json: str, edited_name: str, edited_description: str) -> bool:
        self.log_message_callback(f"Attempting to save edited KML for DB ID: {db_id}, Filename: {original_kml_filename}", "info")

        try:
            edited_coordinates_lon_lat_alt = json.loads(edited_geometry_json)
            if not isinstance(edited_coordinates_lon_lat_alt, list):
                self.log_message_callback("Parsed edited_coordinates_lon_lat_alt is not a list.", "error")
                QMessageBox.critical(self.main_window_ref, "Save Error", "Edited geometry data is invalid (not a list).")
                return False
        except json.JSONDecodeError as e:
            self.log_message_callback(f"JSONDecodeError for edited_geometry_json: {e}. Data: {edited_geometry_json}", "error")
            QMessageBox.critical(self.main_window_ref, "Save Error", f"Could not parse edited geometry data: {e}")
            return False

        original_db_record = self.db_manager.get_polygon_data_by_id(db_id)
        if not original_db_record:
            self.log_message_callback(f"Could not find original DB record for ID: {db_id}", "error")
            QMessageBox.critical(self.main_window_ref, "Save Error", f"Original database record (ID: {db_id}) not found.")
            return False

        # Prepare data for KML generation - mostly for description, UUID for placemark if name not set by simplekml
        data_for_kml_regeneration = original_db_record.copy() # Start with a copy
        # Ensure UUID is present for add_polygon_to_kml_object if it relies on it for default name
        if 'uuid' not in data_for_kml_regeneration or not data_for_kml_regeneration['uuid']:
             data_for_kml_regeneration['uuid'] = original_db_record.get('uuid', f"polygon_{db_id}")


        def _perform_save_operations():
            kml_folder_path = self.credential_manager.get_kml_folder_path()
            if not kml_folder_path:
                self.log_message_callback("KML folder path not configured. Cannot save KML.", "error")
                QMessageBox.critical(self.main_window_ref, "Configuration Error", "KML output folder is not configured.")
                return False

            full_kml_path = os.path.join(kml_folder_path, original_kml_filename)

            # --- KML File Lock ---
            lock_acquired, status_msg, lock_info = self.lock_handler.kml_file_lock_manager.acquire_kml_lock(original_kml_filename, full_kml_path)
            if not lock_acquired:
                self.log_message_callback(f"Failed to acquire KML lock for {original_kml_filename}: {status_msg}", "error")
                QMessageBox.warning(self.main_window_ref, "File Lock Error", f"Could not lock KML file '{original_kml_filename}':\n{status_msg}")
                return False

            new_kml_content_str = None
            try:
                # Generate new KML content
                kml_doc = simplekml.Kml()

                # add_polygon_to_kml_object uses data_for_kml_regeneration for description fields and default placemark name (uuid)
                # It now uses edited_coordinates_list for geometry
                if not add_polygon_to_kml_object(kml_doc, data_for_kml_regeneration, edited_coordinates_list=edited_coordinates_lon_lat_alt):
                    self.log_message_callback("Failed to add polygon object during KML regeneration.", "error")
                    QMessageBox.critical(self.main_window_ref, "Save Error", "Failed to generate KML polygon data.")
                    return False # Release lock will happen in finally

                # Override name and description in the generated KML
                # Assuming add_polygon_to_kml_object creates one placemark in Document
                if kml_doc.Document and kml_doc.Document.features: # Check if features (Placemarks) exist
                    # Find the first placemark to modify its name and description
                    # This assumes add_polygon_to_kml_object adds one main placemark.
                    # If it adds multiple, logic needs to identify the correct one.
                    placemark_to_update = None
                    for feature in kml_doc.Document.features:
                        if isinstance(feature, simplekml.placemark.Placemark):
                            placemark_to_update = feature
                            break

                    if placemark_to_update:
                        placemark_to_update.name = edited_name
                        placemark_to_update.description = edited_description
                    else:
                        self.log_message_callback("No Placemark found in generated KML to update name/description.", "warning")
                else:
                     self.log_message_callback("KML Document or features list is empty after generation.", "warning")


                kml_doc.Document.name = edited_name # Set overall KML document name as well

                kml_doc.save(full_kml_path)
                new_kml_content_str = kml_doc.kml() # Get string content for display
                self.log_message_callback(f"Successfully saved updated KML to: {full_kml_path}", "info")

                # DB Update
                device_id, device_nickname = self.credential_manager.get_device_id(), self.credential_manager.get_device_nickname()
                update_data = {
                    'last_edit_date': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'edit_count': original_db_record.get('edit_count', 0) + 1,
                    'editor_device_id': device_id,
                    'editor_device_nickname': device_nickname,
                    'kml_file_status': 'Edited'
                    # Potentially update fields like 'kml_placemark_name', 'kml_placemark_description' if they exist in DB
                }
                if not self.db_manager.update_polygon_data_by_id(db_id, update_data): # Assuming this method exists
                    self.log_message_callback(f"Failed to update database for DB ID: {db_id}", "error")
                    QMessageBox.critical(self.main_window_ref, "DB Update Error", "Failed to update database record after saving KML.")
                    # Consider if KML file save should be rolled back or handled
                    return False # Release lock will happen in finally

                self.log_message_callback(f"Successfully updated DB for ID: {db_id}", "info")
                return True # Success

            except Exception as e:
                self.log_message_callback(f"Error during KML save or DB update for {original_kml_filename}: {e}", "error")
                QMessageBox.critical(self.main_window_ref, "Save Error", f"An error occurred while saving KML: {e}")
                return False # Release lock will happen in finally
            finally:
                self.lock_handler.kml_file_lock_manager.release_kml_lock(original_kml_filename)
                self.log_message_callback(f"KML lock released for {original_kml_filename}", "info")

        # --- DB Lock for the entire save operation (including KML file lock and DB update) ---
        save_successful, result_data = self.lock_handler._execute_db_operation_with_lock(
            _perform_save_operations, "Save Edited KML"
        )

        if save_successful and result_data: # result_data from _perform_save_operations is boolean
            # Refresh the editor with the newly saved content
            # Need to re-fetch KML content as kml_doc.kml() might not be available here
            # Or, _perform_save_operations could return the new kml_content_str
            try:
                with open(os.path.join(self.credential_manager.get_kml_folder_path(), original_kml_filename), 'r', encoding='utf-8') as f:
                    saved_kml_content = f.read()
                self.kml_editor_widget.display_kml(saved_kml_content, edited_name, edited_description)
            except Exception as e_read:
                self.log_message_callback(f"Error reading back saved KML for display: {e_read}", "error")
                self.kml_editor_widget.clear_map() # Fallback

            self.kml_data_updated_signal.emit()
            self.log_message_callback(f"KML Edit Save process completed successfully for DB ID: {db_id}.", "info")
            QMessageBox.information(self.main_window_ref, "Save Successful", f"Changes to '{original_kml_filename}' saved.")
            return True
        else:
            self.log_message_callback(f"KML Edit Save process failed or was rolled back for DB ID: {db_id}.", "error")
            # QMessageBox for error already shown within _perform_save_operations or by _execute_db_operation_with_lock
            # Reload original state in editor as save failed
            if original_db_record: # Ensure record exists
                kml_file_name = original_db_record.get('kml_file_name')
                full_kml_path = os.path.join(self.credential_manager.get_kml_folder_path(), kml_file_name)
                if os.path.exists(full_kml_path):
                    try:
                        with open(full_kml_path, 'r', encoding='utf-8') as f:
                            kml_content = f.read()
                        parsed_name, parsed_desc = self._parse_kml_for_name_desc(kml_content)
                        display_name = parsed_name if parsed_name else original_db_record.get('uuid', "Unnamed Polygon")
                        display_desc = parsed_desc if parsed_desc is not None else "No description in KML."
                        self.kml_editor_widget.display_kml(kml_content, display_name, display_desc)
                    except Exception as e_reload:
                         self.log_message_callback(f"Error reloading original KML after failed save: {e_reload}", "error")
                         self.kml_editor_widget.clear_map()
                else:
                    self.kml_editor_widget.clear_map() # KML file seems to be gone
            else:
                self.kml_editor_widget.clear_map()

            return False

    def _trigger_ge_polygon_upload(self, polygon_record):
        # This method is for Google Earth and remains largely unchanged,
        # as it generates KML from DB P1-P4 for temporary viewing.
        self.log_message_callback(f"GE View: Processing polygon UUID {polygon_record.get('uuid')} for GE upload.", "info")
        kml_doc = simplekml.Kml(name=str(polygon_record.get('uuid', 'Polygon')))
        
        # For GE, add_polygon_to_kml_object will use P1-P4 from the DB record
        if add_polygon_to_kml_object(kml_doc, polygon_record): # No edited_coordinates_list here
            try:
                if self.current_temp_kml_path and os.path.exists(self.current_temp_kml_path):
                    try:
                        os.remove(self.current_temp_kml_path)
                        self.log_message_callback(f"Old temp KML deleted: {self.current_temp_kml_path}", "info")
                    except Exception as e_del:
                        self.log_message_callback(f"Error deleting old temp KML {self.current_temp_kml_path}: {e_del}", "error")
                
                fd, temp_kml_path = tempfile.mkstemp(suffix=".kml", prefix="ge_poly_")
                os.close(fd)
                kml_doc.save(temp_kml_path)
                self.current_temp_kml_path = temp_kml_path
                self.log_message_callback(f"Temp KML saved to: {self.current_temp_kml_path}", "info")
                
                QApplication.clipboard().setText(self.current_temp_kml_path)
                self.log_message_callback("KML path copied to clipboard.", "info")
                
                if self.show_ge_instructions_popup_again:
                    self._show_ge_instructions_popup()
            except Exception as e_kml_save:
                self.log_message_callback(f"Error saving temp KML: {e_kml_save}", "error")
                QMessageBox.warning(self.main_window_ref, "KML Error", f"Could not save temporary KML for Google Earth:\n{e_kml_save}")
        else:
            self.log_message_callback(f"Failed KML content generation for UUID {polygon_record.get('uuid')}.", "error")
            QMessageBox.warning(self.main_window_ref, "KML Generation Failed", "Could not generate KML content for Google Earth.")

    def _show_ge_instructions_popup(self):
        msg_box = QMessageBox(self.main_window_ref)
        msg_box.setWindowTitle("Google Earth Instructions")
        msg_box.setTextFormat(Qt.TextFormat.PlainText)
        msg_box.setText("Instructions:\n1. Click inside the Google Earth window to give it focus.\n2. Press Ctrl+O (Windows) or Cmd+O (Mac) to open file.\n3. Paste the KML file path (Ctrl+V or Cmd+V) into the file name box.\n4. Press Enter or click Open to load the polygon.\n(Tip: You might use Ctrl+H to access GE's history/temporary places).")
        checkbox = QCheckBox("Do not show this message again for this session.")
        msg_box.setCheckBox(checkbox)
        msg_box.exec()
        if checkbox.isChecked():
            self.show_ge_instructions_popup_again = False
            self.log_message_callback("Google Earth instructions popup disabled for this session.", "info")

    def cleanup_temp_kml(self):
        if self.current_temp_kml_path and os.path.exists(self.current_temp_kml_path):
            try:
                os.remove(self.current_temp_kml_path)
                self.log_message_callback(f"Temp KML deleted: {self.current_temp_kml_path}", "info")
                self.current_temp_kml_path = None
            except Exception as e:
                self.log_message_callback(f"Error deleting temp KML {self.current_temp_kml_path}: {e}", "error")
