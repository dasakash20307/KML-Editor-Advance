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
                 log_message_callback, lock_handler,
                 map_stack, kml_editor_view_widget, google_earth_view_widget,
                 table_view, source_model, filter_proxy_model, parent=None):
        super().__init__(parent)
        self.main_window_ref = main_window_ref
        self.db_manager = db_manager
        self.credential_manager = credential_manager
        self.log_message_callback = log_message_callback
        self.lock_handler = lock_handler
        
        self.map_stack = map_stack
        self.kml_editor_widget = kml_editor_view_widget
        self.google_earth_view_widget = google_earth_view_widget
        
        if self.kml_editor_widget and hasattr(self.kml_editor_widget, 'set_credential_manager'):
            self.kml_editor_widget.set_credential_manager(self.credential_manager)

        self.table_view = table_view
        self.source_model = source_model
        self.filter_proxy_model = filter_proxy_model

        # Attributes for Google Earth KML generation
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
        
        # Get the first selected row's data
        polygon_record = None
        db_id = None
        
        if selected_proxy_indexes:
            proxy_index = selected_proxy_indexes[0]  # Get first selected row
            source_index = self.filter_proxy_model.mapToSource(proxy_index)
            db_id = self.source_model.data(
                self.source_model.index(source_index.row(), PolygonTableModel.DB_ID_COL),
                Qt.ItemDataRole.DisplayRole
            )
            
            if db_id is not None:
                try:
                    db_id = int(db_id)
                    polygon_record = self.db_manager.get_polygon_data_by_id(db_id)
                except (ValueError, TypeError) as e:
                    self.log_message_callback(f"Error parsing DB ID {db_id}: {e}", "error")
                    db_id = None
                except Exception as e:
                    self.log_message_callback(f"Error fetching record for DB ID {db_id}: {e}", "error")
                    db_id = None
        
        if self.map_stack.currentIndex() == 1:  # GE View is active
            if polygon_record:
                kml_file_name = polygon_record.get('kml_file_name')
                main_kml_folder_path = self.credential_manager.get_kml_folder_path()

                if kml_file_name and isinstance(kml_file_name, str) and kml_file_name.strip() and main_kml_folder_path:
                    full_kml_path = os.path.join(main_kml_folder_path, kml_file_name.strip())
                    if os.path.exists(full_kml_path):
                        self.google_earth_view_widget.display_kml_and_show_instructions(full_kml_path, kml_file_name)
                        if self.show_ge_instructions_popup_again:
                            self._show_ge_instructions_popup()
                    else:
                        self.log_message_callback(f"GE View: KML file '{kml_file_name}' not found at '{full_kml_path}'. Updating status.", "warning")
                        self.google_earth_view_widget.clear_view()
                        if db_id is not None:
                            self.db_manager.update_kml_file_status(db_id, "File Deleted")
                            self.kml_data_updated_signal.emit()
                else:
                    log_msg = "Cannot process for Google Earth. "
                    if not main_kml_folder_path:
                        log_msg += "KML folder path not configured. "
                    else:
                        log_msg += f"KML file name missing or invalid in DB for DB ID {db_id if db_id is not None else 'Unknown'}. "
                    self.log_message_callback(f"GE View: {log_msg}", "info")
                    self.google_earth_view_widget.clear_view()
            else:
                self.log_message_callback("GE View: No valid record selected or record fetch failed. GE view cleared.", "info")
                self.google_earth_view_widget.clear_view()

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
        
        original_db_record = self.db_manager.get_polygon_data_by_id(db_id)
        if not original_db_record:
            self.log_message_callback(f"Could not find original DB record for ID: {db_id} before starting save op.", "error")
            QMessageBox.critical(self.main_window_ref, "Save Error", f"Original database record (ID: {db_id}) not found.")
            return False

        new_kml_content_str = None

        def _perform_save_operations():
            nonlocal new_kml_content_str, edited_name, edited_description
            if not self.lock_handler.kml_file_lock_manager.acquire_kml_lock(original_kml_filename):
                return False
            
            self.log_message_callback(f"KML lock acquired for {original_kml_filename}", "info")
            try:
                kml_root_path = self.credential_manager.get_kml_folder_path()
                if not kml_root_path:
                    QMessageBox.critical(self.main_window_ref, "Error", "KML root path not configured.")
                    return False
                full_kml_path = os.path.join(kml_root_path, original_kml_filename)

                parsed_simplekml_coords = []
                geom_type_from_geojson = None

                if edited_geometry_json:
                    try:
                        geojson_data = json.loads(edited_geometry_json)
                        
                        # Check if the data is a FeatureCollection (from multi-edit) or a single geometry (from single edit)
                        if isinstance(geojson_data, dict) and geojson_data.get("type") == "FeatureCollection":
                            features = geojson_data.get("features", [])
                            if not features:
                                self.log_message_callback("Received empty FeatureCollection from map edit.", "warning")
                                # If no features, maybe the polygon was deleted? Or no changes?
                                # For now, treat as no valid geometry to save.
                                return False # Indicate no save operation performed due to lack of features

                            # In single KML edit mode, we expect only one feature in the FeatureCollection
                            # Find the feature corresponding to the current db_id
                            single_feature = None
                            for feature in features:
                                props = feature.get("properties", {})
                                try:
                                    feature_db_id = int(props.get("db_id"))
                                    if feature_db_id == db_id:
                                        single_feature = feature
                                        break
                                except (ValueError, TypeError):
                                    self.log_message_callback(f"Skipping feature with invalid or missing db_id in FeatureCollection: {props.get('db_id')}", "warning")
                                    continue

                            if not single_feature:
                                # Attempt to get the first feature if we can't find the specific ID
                                # This is a fallback for single KML editing when the ID doesn't match
                                if len(features) == 1 and self.main_window_ref.current_mode != "multi":
                                    self.log_message_callback(f"Using first and only feature for db_id {db_id} despite ID mismatch.", "warning")
                                    single_feature = features[0]
                                else:
                                    self.log_message_callback(f"Could not find feature with matching db_id {db_id} in the received FeatureCollection.", "error")
                                    QMessageBox.critical(self.main_window_ref, "Save Error", f"Edited geometry data for ID {db_id} not found in map data.")
                                    return False # Indicate failure

                            geojson_geom = single_feature.get("geometry")
                            if not geojson_geom:
                                self.log_message_callback(f"Feature with db_id {db_id} has no geometry.", "error")
                                QMessageBox.critical(self.main_window_ref, "Save Error", f"Edited feature for ID {db_id} has no geometry data.")
                                return False # Indicate failure

                            # Update name/description from the feature properties if available
                            feature_props = single_feature.get("properties", {})
                            edited_name = feature_props.get('name') if feature_props.get('name') is not None else edited_name # Use existing edited_name if not in feature
                            edited_description = feature_props.get('description') if feature_props.get('description') is not None else edited_description # Use existing edited_description if not in feature

                        elif isinstance(geojson_data, dict) and geojson_data.get("type") in ["Polygon", "LineString", "Point"]:
                             # This case handles the old single-geometry format (though JS now sends FeatureCollection)
                             # Keep for robustness or if JS logic changes back
                             self.log_message_callback("Received single geometry object (non-FeatureCollection). Processing.", "info")
                             geojson_geom = geojson_data
                        else:
                            raise ValueError(f"Unsupported or unexpected top-level GeoJSON type: {geojson_data.get('type')}")

                        # Now process the single geometry object (either extracted from FC or received directly)
                        geom_type_from_geojson = geojson_geom.get("type")
                        raw_coordinates = geojson_geom.get("coordinates")

                        if geom_type_from_geojson == "Polygon":
                            if not (raw_coordinates and isinstance(raw_coordinates, list) and len(raw_coordinates) > 0):
                                raise ValueError("Polygon coordinates missing or invalid structure.")
                            outer_ring = raw_coordinates[0]
                            if not isinstance(outer_ring, list):
                                raise ValueError("Polygon outer ring is not a list.")
                            for point in outer_ring:
                                if isinstance(point, list) and len(point) >= 2:
                                    alt = point[2] if len(point) > 2 and point[2] is not None else 0.0
                                    parsed_simplekml_coords.append((point[0], point[1], alt))
                                else:
                                    raise ValueError("Invalid point structure in Polygon outer ring.")
                        elif geom_type_from_geojson in ["LineString", "Point"]:
                            self.log_message_callback(f"Received geometry type '{geom_type_from_geojson}' from map edit. Processing.", "info")
                            if geom_type_from_geojson == "LineString":
                                if not (raw_coordinates and isinstance(raw_coordinates, list)):
                                    raise ValueError("LineString coordinates missing or invalid structure.")
                                for point in raw_coordinates:
                                    if isinstance(point, list) and len(point) >= 2:
                                        alt = point[2] if len(point) > 2 and point[2] is not None else 0.0
                                        parsed_simplekml_coords.append((point[0], point[1], alt))
                                    else:
                                        raise ValueError("Invalid point structure in LineString.")
                            elif geom_type_from_geojson == "Point":
                                if not (raw_coordinates and isinstance(raw_coordinates, list) and len(raw_coordinates) >=2):
                                    raise ValueError("Point coordinates missing or invalid.")
                                alt = raw_coordinates[2] if len(raw_coordinates) > 2 and raw_coordinates[2] is not None else 0.0
                                parsed_simplekml_coords.append((raw_coordinates[0], raw_coordinates[1], alt))
                        else:
                            # This case should ideally not be reached if the FeatureCollection/single geometry check is thorough
                            raise ValueError(f"Unsupported or unexpected GeoJSON geometry type for polygon saving: {geom_type_from_geojson}")

                    except json.JSONDecodeError as e_json:
                        self.log_message_callback(f"JSONDecodeError parsing edited_geometry_json: {e_json}", "error")
                        QMessageBox.critical(self.main_window_ref, "Save Error", f"Invalid geometry data format: {e_json}")
                        return False
                    except ValueError as e_val:
                        self.log_message_callback(f"ValueError processing GeoJSON geometry: {e_val}", "error")
                        QMessageBox.critical(self.main_window_ref, "Save Error", f"Invalid geometry data: {e_val}")
                        return False
                else:
                    # Handle case where edited_geometry_json is empty or None
                    self.log_message_callback("edited_geometry_json is empty or None.", "warning")
                    # Depending on requirements, this might mean the feature was deleted or no geometry exists.
                    # For now, treat as no valid geometry to save.
                    return False # Indicate no save operation performed

                if not parsed_simplekml_coords:
                    self.log_message_callback("Coordinates list is empty after processing GeoJSON.", "error")
                    QMessageBox.critical(self.main_window_ref, "Save Error", "No valid coordinates found in the edited geometry.")
                    return False

                final_coordinates_for_kml_object = parsed_simplekml_coords

                kml_doc = simplekml.Kml()
                
                metadata_for_kml_gen = {
                    'uuid': original_db_record.get('uuid'),
                    'response_code': original_db_record.get('response_code'),
                    'farmer_name': edited_name,
                    'village_name': original_db_record.get('village_name')
                }
                for key, value in original_db_record.items():
                    if key not in metadata_for_kml_gen and key not in ['coordinates', 'geom_type']:
                        metadata_for_kml_gen[key] = value

                if not add_polygon_to_kml_object(kml_doc, 
                                                 metadata_for_kml_gen, 
                                                 edited_coordinates_list=final_coordinates_for_kml_object):
                    self.log_message_callback("Failed to generate KML polygon object with new coordinates.", "error")
                    QMessageBox.critical(self.main_window_ref, "Save Error", "Failed to generate KML polygon data.")
                    return False

                if kml_doc.document and kml_doc.document.features:
                    placemark_to_update = None
                    if kml_doc.document.features:
                        placemark_to_update = kml_doc.document.features[0]

                    if placemark_to_update:
                        placemark_to_update.name = edited_name
                        if edited_description is not None:
                            placemark_to_update.description = edited_description
                    else:
                        self.log_message_callback("No feature found in generated KML to update name/description.", "warning")
                else:
                     self.log_message_callback("KML Document or features list is empty after generation.", "warning")

                kml_doc.document.name = edited_name 
                kml_doc.save(full_kml_path)
                new_kml_content_str = kml_doc.kml() 
                self.log_message_callback(f"Successfully saved updated KML to: {full_kml_path}", "info")

                device_id, device_nickname = self.credential_manager.get_device_id(), self.credential_manager.get_device_nickname()
                update_data = {
                    'last_edit_date': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'edit_count': original_db_record.get('edit_count', 0) + 1,
                    'editor_device_id': device_id,
                    'editor_device_nickname': device_nickname,
                    'kml_file_status': 'Edited',
                    'kml_placemark_name': edited_name
                }
                if not self.db_manager.update_polygon_data_by_id(db_id, update_data):
                    self.log_message_callback(f"Failed to update database for DB ID: {db_id}", "error")
                    QMessageBox.critical(self.main_window_ref, "DB Update Error", "Failed to update database record after saving KML.")
                    return False

                self.log_message_callback(f"Successfully updated DB for ID: {db_id}", "info")
                return True

            except Exception as e:
                self.log_message_callback(f"General error in _perform_save_operations: {e}", "error")
                QMessageBox.critical(self.main_window_ref, "Save Error", f"An unexpected error occurred: {e}")
                return False
            finally:
                self.lock_handler.kml_file_lock_manager.release_kml_lock(original_kml_filename)
                self.log_message_callback(f"KML lock released for {original_kml_filename}", "info")

        lock_and_attempt_succeeded, perform_save_result = self.lock_handler._execute_db_operation_with_lock(
            _perform_save_operations, "Save Edited KML"
        )

        if lock_and_attempt_succeeded and perform_save_result:
            try:
                with open(os.path.join(self.credential_manager.get_kml_folder_path(), original_kml_filename), 'r', encoding='utf-8') as f:
                    saved_kml_content = f.read()
                self.kml_editor_widget.display_kml(saved_kml_content, edited_name, edited_description)
            except Exception as e_read:
                self.log_message_callback(f"Error reading back saved KML for display: {e_read}", "error")
                self.kml_editor_widget.clear_map()

            self.kml_data_updated_signal.emit()
            self.log_message_callback(f"KML Edit Save process completed successfully for DB ID: {db_id}.", "info")
            QMessageBox.information(self.main_window_ref, "Save Successful", f"Changes to '{original_kml_filename}' saved.")
            return True
        else:
            self.log_message_callback(f"KML Edit Save process failed or was rolled back for DB ID: {db_id}.", "error")
            if original_db_record:
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
                    self.kml_editor_widget.clear_map()
            else:
                self.kml_editor_widget.clear_map()

            return False

    def _trigger_ge_polygon_upload(self, polygon_record):
        # This method generates a KML file from DB P1-P4 coordinates (and other basic metadata)
        # for temporary viewing in Google Earth.
        # IMPORTANT: As of recent changes (around KML-first paradigm and GE path copying),
        # this method is NO LONGER CALLED by on_table_selection_changed for the primary
        # Google Earth mode interaction when a user selects a row in the table.
        # That interaction now focuses on providing the path to the *persistent* KML file.
        #
        # This method MIGHT STILL BE USEFUL for:
        #  - Other specific features that require a quick, on-the-fly KML from basic DB coordinates.
        #  - Debugging purposes.
        #  - A fallback if a persistent KML is missing but P1-P4 data exists (though current logic doesn't use it this way).
        # If no such uses remain, it could be considered for deprecation in the future.
        self.log_message_callback(f"KMLHandler: _trigger_ge_polygon_upload called for RC: {polygon_record.get('response_code')}. Note its changed role.", "debug")
        kml = simplekml.Kml()
        
        # data_for_kml_gen should contain only what's needed for add_polygon_to_kml_object
        # when creating a temporary KML from DB coordinates (P1-P4, etc.)
        data_for_kml_gen = {
            'uuid': polygon_record.get('uuid'),
            'coordinates': [], # This will be populated by P1-P4 if add_polygon_to_kml_object handles it
            'response_code': polygon_record.get('response_code'),
            # Potentially add P1_utm_str to P4_utm_str if add_polygon_to_kml_object uses them directly
            'p1_utm_str': polygon_record.get('p1_utm_str'),
            'p2_utm_str': polygon_record.get('p2_utm_str'),
            'p3_utm_str': polygon_record.get('p3_utm_str'),
            'p4_utm_str': polygon_record.get('p4_utm_str'),
            # Add other fields if simplekml description generation needs them from this dict
            'farmer_name': polygon_record.get('farmer_name', 'N/A'),
            'village_name': polygon_record.get('village_name', 'N/A')
        } # This closing brace was the source of the previous SyntaxError. Ensure it's correct.

        # Assuming add_polygon_to_kml_object can derive coordinates from pX_utm_str if 'coordinates' is empty
        # and can generate a description from the provided dict.
        if not add_polygon_to_kml_object(kml, data_for_kml_gen): # Pass the concise dict
            self.log_message_callback("Failed to add polygon object to KML for GE (temporary).", "error")
            return

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
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(
            "Instructions:<br>"
            "1. Click inside the Google Earth window to give it focus.<br>"
            "2. Press Ctrl+O (Windows) or Cmd+O (Mac) to open file.<br>"
            "3. Paste the KML file path (Ctrl+V or Cmd+V) into the file name box.<br>"
            "4. Press Enter or click Open to load the polygon.<br><br>"
            "<i>(Tip: You might use Ctrl+H to access GE's history/temporary places)</i>."
        )
        
        checkbox = QCheckBox("Do not show this message again for this session.")
        msg_box.setCheckBox(checkbox)
        
        msg_box.exec()
        
        if checkbox.isChecked():
            self.show_ge_instructions_popup_again = False
            self.log_message_callback("Google Earth instructions popup disabled for this session.", "info")

    def cleanup_temp_kml(self):
        if hasattr(self.google_earth_view_widget, 'cleanup'):
            self.google_earth_view_widget.cleanup()
