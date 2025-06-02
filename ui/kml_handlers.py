import os
import tempfile
import utm
import simplekml

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QCheckBox

from core.kml_generator import add_polygon_to_kml_object
# Import PolygonTableModel to access its constants like DB_ID_COL
from ui.table_models import PolygonTableModel

class KMLHandler(QObject):
    # Signal to indicate KML status might have been updated in DB, so table might need refresh
    kml_data_updated_signal = Signal()

    def __init__(self, main_window_ref, db_manager, credential_manager,
                 log_message_callback,
                 map_stack, map_view_widget, google_earth_view_widget,
                 table_view, source_model, filter_proxy_model, parent=None):
        super().__init__(parent)
        self.main_window_ref = main_window_ref # For QMessageBox, QFileDialog parenting
        self.db_manager = db_manager
        self.credential_manager = credential_manager
        self.log_message_callback = log_message_callback

        self.map_stack = map_stack
        self.map_view_widget = map_view_widget
        self.google_earth_view_widget = google_earth_view_widget

        self.table_view = table_view
        self.source_model = source_model # This is PolygonTableModel instance
        self.filter_proxy_model = filter_proxy_model # This is PolygonFilterProxyModel instance

        self.current_temp_kml_path = None
        self.show_ge_instructions_popup_again = True


    def on_table_selection_changed(self, selected, deselected):
        selected_proxy_indexes = self.table_view.selectionModel().selectedRows()
        polygon_record = None
        db_id = None # Initialize db_id

        if selected_proxy_indexes:
            source_model_index = self.filter_proxy_model.mapToSource(selected_proxy_indexes[0])
            if source_model_index.isValid():
                # Use PolygonTableModel.DB_ID_COL directly
                db_id_item = self.source_model.data(source_model_index.siblingAtColumn(PolygonTableModel.DB_ID_COL))
                try:
                    db_id = int(db_id_item) # Store db_id for later use
                    polygon_record = self.db_manager.get_polygon_data_by_id(db_id)
                except (ValueError, TypeError):
                    self.log_message_callback(f"Map/GE: Invalid ID for selected row: {db_id_item}", "error")
                    polygon_record = None
                except Exception as e:
                    self.log_message_callback(f"Map/GE: Error fetching record: {e}", "error")
                    polygon_record = None

        if self.map_stack.currentIndex() == 1:  # GE View is active
            if polygon_record and polygon_record.get('status') == 'valid_for_kml':
                self._trigger_ge_polygon_upload(polygon_record)
            else:
                self.log_message_callback("GE View: No valid polygon record selected or record not valid for KML upload.", "warning")
        else:  # Map View is active
            if polygon_record and polygon_record.get('status') == 'valid_for_kml':
                coords_lat_lon, utm_valid = [], True
                for i in range(1, 5):
                    e, n = polygon_record.get(f'p{i}_easting'), polygon_record.get(f'p{i}_northing')
                    zn, zl = polygon_record.get(f'p{i}_zone_num'), polygon_record.get(f'p{i}_zone_letter')
                    if None in [e, n, zn, zl]:
                        utm_valid = False; break
                    try:
                        lat, lon = utm.to_latlon(e, n, int(zn), zl) # Ensure zone_num is int
                        coords_lat_lon.append((lat, lon))
                    except Exception as e_conv:
                        self.log_message_callback(f"Map: UTM conv fail {polygon_record.get('uuid')}, P{i}:{e_conv}", "error")
                        utm_valid = False; break
                if utm_valid and len(coords_lat_lon) == 4:
                    self.map_view_widget.display_polygon(coords_lat_lon, coords_lat_lon[0])
                elif hasattr(self.map_view_widget, 'clear_map'): # Check if method exists
                    self.map_view_widget.clear_map()
            elif polygon_record:  # Record exists, but might not be 'valid_for_kml' or UTM conversion failed
                kml_file_name = polygon_record.get('kml_file_name')
                main_kml_folder_path = self.credential_manager.get_kml_folder_path()

                if kml_file_name and isinstance(kml_file_name, str) and kml_file_name.strip() and main_kml_folder_path:
                    full_kml_path = os.path.join(main_kml_folder_path, kml_file_name.strip())
                    if os.path.exists(full_kml_path):
                        self.map_view_widget.load_kml_for_display(full_kml_path)
                    else:
                        self.log_message_callback(f"KML file '{kml_file_name}' not found at '{full_kml_path}'. Updating status.", "warning")
                        if hasattr(self.map_view_widget, 'clear_map'): self.map_view_widget.clear_map()
                        if db_id is not None: # db_id captured from earlier
                            self.db_manager.update_kml_file_status(db_id, "File Deleted")
                            self.kml_data_updated_signal.emit() # Signal that data needs refresh
                        else:
                            self.log_message_callback("DB ID not found for selected row, KML status not updated.", "error")
                else:
                    if hasattr(self.map_view_widget, 'clear_map'): self.map_view_widget.clear_map()
                    if not main_kml_folder_path: self.log_message_callback("KML folder path not configured. Cannot load KML.", "warning")
                    elif not kml_file_name or not isinstance(kml_file_name, str) or not kml_file_name.strip():
                         self.log_message_callback(f"No KML file name for selected record (DB ID: {db_id if db_id is not None else 'Unknown'}). Clearing map.", "info")
            elif hasattr(self.map_view_widget, 'clear_map'): # Default clear if no valid record
                self.map_view_widget.clear_map()

    def _trigger_ge_polygon_upload(self, polygon_record):
        self.log_message_callback(f"GE View: Processing polygon UUID {polygon_record.get('uuid')} for GE upload.", "info")
        kml_doc = simplekml.Kml(name=str(polygon_record.get('uuid', 'Polygon')))

        if add_polygon_to_kml_object(kml_doc, polygon_record):
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
        msg_box = QMessageBox(self.main_window_ref) # Parent to main_window_ref
        msg_box.setWindowTitle("Google Earth Instructions")
        msg_box.setTextFormat(Qt.TextFormat.PlainText) # Ensure plain text for reliable formatting
        msg_box.setText("Instructions:\n1. Click inside the Google Earth window to give it focus.\n2. Press Ctrl+O (Windows) or Cmd+O (Mac) to open file.\n3. Paste the KML file path (Ctrl+V or Cmd+V) into the file name box.\n4. Press Enter or click Open to load the polygon.\n(Tip: You might use Ctrl+H to access GE's history/temporary places).")
        checkbox = QCheckBox("Do not show this message again for this session.")
        msg_box.setCheckBox(checkbox)
        msg_box.exec()
        if checkbox.isChecked():
            self.show_ge_instructions_popup_again = False
            self.log_message_callback("Google Earth instructions popup disabled for this session.", "info")

    def cleanup_temp_kml(self): # Added method for explicit cleanup if needed
        if self.current_temp_kml_path and os.path.exists(self.current_temp_kml_path):
            try:
                os.remove(self.current_temp_kml_path)
                self.log_message_callback(f"Temp KML deleted: {self.current_temp_kml_path}", "info")
                self.current_temp_kml_path = None
            except Exception as e:
                self.log_message_callback(f"Error deleting temp KML {self.current_temp_kml_path}: {e}", "error")
