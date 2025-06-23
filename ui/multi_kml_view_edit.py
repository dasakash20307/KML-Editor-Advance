import os
import json
import xml.etree.ElementTree as ET
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QMessageBox, QWidget

class MultiKmlViewEdit(QObject):
    """
    Handles the multi-KML view and edit functionality.
    This class manages the selection, loading, editing and saving of multiple KML files.
    """
    # Signal to notify when multiple KMLs have been saved
    multi_kml_saved_signal = Signal()
    
    def __init__(self, main_window_ref, credential_manager, kml_handler):
        """
        Initialize the Multi KML View and Edit manager.
        
        Args:
            main_window_ref: Reference to the main window
            credential_manager: Instance of CredentialManager
            kml_handler: Instance of KMLHandler
        """
        super().__init__()
        self.main_window = main_window_ref
        self.credential_manager = credential_manager
        self.kml_handler = kml_handler
        self.selected_kml_ids = []  # List of DB IDs for selected KML files
        self.selected_kml_files = []  # List of dictionaries with KML file info
        self.original_kml_contents = {}  # Dictionary mapping DB ID to original KML content
        self.current_mode = "single"  # 'single' or 'multi'
        self.edited_kmls = {}  # Dictionary mapping DB ID to edited KML data
    
    def enable_multi_kml_mode(self):
        """Switch the UI to multi-KML mode"""
        self.current_mode = "multi"
        
        # Hide single-KML editor buttons (those on the KML Editor Widget itself)
        if hasattr(self.main_window, 'kml_editor_widget'):
            self.main_window.kml_editor_widget.save_button.hide()
            self.main_window.kml_editor_widget.cancel_button.hide()
            self.main_window.kml_editor_widget.edit_button.hide()
        
        # Show multi-KML buttons (from the Multi-KML Operations GroupBox)
        self.main_window.multi_kml_editor_button.show()
        self.main_window.multi_kml_save_button.show()
        self.main_window.multi_kml_cancel_button.show()
        self.main_window.single_kml_editor_button.show() # This is "Exit Multi-KML Mode"
        
        # Update mode indicator and button states
        self.main_window.multi_kml_view_button.setChecked(True)
        self.main_window.multi_kml_editor_button.setEnabled(True) # Should be true if KMLs are loaded
        self.main_window.multi_kml_save_button.setEnabled(False) # Enabled after entering edit mode
        self.main_window.multi_kml_cancel_button.setEnabled(False) # Enabled after entering edit mode
        
        # Log the mode change
        self.main_window.log_message("Switched to Multi-KML mode", "info")
        
        # Reset selections - KMLs will be loaded by MainWindow._toggle_multi_kml_mode calling load_selected_kmls
        self.selected_kml_ids = []
        self.selected_kml_files = []
        # self.update_table_checkboxes_visibility(True) # REMOVED - Checkboxes always visible
        
        # Display empty map or instruction - this will be handled by load_selected_kmls
        # self.main_window.kml_editor_widget.clear_map()
    
    def enable_single_kml_mode(self):
        """Switch the UI back to single-KML mode"""
        self.current_mode = "single"
        
        # Show single-KML editor buttons (on the KML Editor Widget itself)
        if hasattr(self.main_window, 'kml_editor_widget'):
            self.main_window.kml_editor_widget.save_button.show() # Or hide based on edit state
            self.main_window.kml_editor_widget.cancel_button.show() # Or hide based on edit state
            self.main_window.kml_editor_widget.edit_button.show()
            # Initial state for single KML editor buttons
            self.main_window.kml_editor_widget.save_button.setEnabled(False)
            self.main_window.kml_editor_widget.cancel_button.setEnabled(False)
            self.main_window.kml_editor_widget.edit_button.setEnabled(True) # Assuming a KML might be loaded or can be

        # Hide multi-KML buttons (from the Multi-KML Operations GroupBox)
        self.main_window.multi_kml_editor_button.hide()
        self.main_window.multi_kml_save_button.hide()
        self.main_window.multi_kml_cancel_button.hide()
        self.main_window.single_kml_editor_button.hide() # This is "Exit Multi-KML Mode"
        
        # Update mode indicator
        self.main_window.multi_kml_view_button.setChecked(False)
        
        # Log the mode change
        self.main_window.log_message("Switched to Single-KML mode", "info")
        
        # Reset selections
        self.selected_kml_ids = []
        self.selected_kml_files = []
        # self.update_table_checkboxes_visibility(False) # REMOVED
        
        # Display empty map or instruction if no single KML is selected
        # Consider the state: if a KML was selected in the table, should it load?
        # For now, just clear. MainWindow selection logic will handle reloading if necessary.
        self.main_window.kml_editor_widget.clear_map()
    
    def load_selected_kmls(self):
        """
        Load selected KML files based on checkbox selection in the table.
        """
        # Clear previous selections
        self.selected_kml_ids = []
        self.selected_kml_files = []
        self.original_kml_contents = {}
        self.edited_kmls = {}
        
        # Get all rows with checked status from the source model
        selected_rows = self.main_window.source_model.get_checked_rows()
        
        if not selected_rows:
            QMessageBox.warning(self.main_window, "No Selection", 
                               "Please select at least one KML file using the checkboxes.")
            return False
        
        # Extract database IDs and fetch KML file paths
        kml_root_path = self.credential_manager.get_kml_folder_path()
        if not kml_root_path:
            QMessageBox.critical(self.main_window, "Configuration Error",
                               "KML root path not configured.")
            return False
        
        self.main_window.log_message(f"Loading {len(selected_rows)} KML files...", "info")
        
        # Process each selected row
        for row_data in selected_rows:
            db_id = row_data.get('id')
            kml_file_name = row_data.get('kml_file_name')
            
            if not kml_file_name or not db_id:
                continue
            
            full_kml_path = os.path.join(kml_root_path, kml_file_name)
            
            if not os.path.exists(full_kml_path):
                self.main_window.log_message(f"KML file not found: {full_kml_path}", "warning")
                continue
            
            try:
                # Read KML file content
                with open(full_kml_path, 'r', encoding='utf-8') as f:
                    kml_content = f.read()
                
                # Parse KML for placemark details
                name, desc = self._parse_kml_for_name_desc(kml_content)
                
                # Add to our tracking collections
                self.selected_kml_ids.append(db_id)
                self.selected_kml_files.append({
                    'db_id': db_id,
                    'kml_file_name': kml_file_name,
                    'kml_path': full_kml_path,
                    'name': name or row_data.get('uuid', "Unnamed Polygon"),
                    'description': desc or ""
                })
                self.original_kml_contents[db_id] = kml_content
                
            except Exception as e:
                self.main_window.log_message(f"Error reading KML file {kml_file_name}: {str(e)}", "error")
        
        if not self.selected_kml_files:
            QMessageBox.warning(self.main_window, "No Valid KML Files", 
                               "No valid KML files found in your selection.")
            return False
        
        # Load the KMLs into the combined view
        self._display_combined_kmls()
        return True
    
    def _display_combined_kmls(self):
        """Display all selected KMLs in the editor view"""
        if not self.selected_kml_files:
            self.main_window.kml_editor_widget.clear_map()
            return
        
        # Create a combined KML string for display
        combined_kml_root = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
        document_el = ET.SubElement(combined_kml_root, "Document")
        doc_name_el = ET.SubElement(document_el, "name")
        doc_name_el.text = f"Combined KML View ({len(self.selected_kml_files)} files)"
        
        # Extract and add Placemark elements from each KML file
        for kml_file_info in self.selected_kml_files: # Iterate through file info list
            db_id = kml_file_info['db_id']
            kml_content = self.original_kml_contents.get(db_id)
            if not kml_content:
                self.main_window.log_message(f"Original KML content not found for db_id {db_id} during display.", "warning")
                continue

            try:
                # Parse the individual KML content string
                individual_kml_root = ET.fromstring(kml_content)
                # Find the Placemark element, accounting for namespaces
                placemark_el = individual_kml_root.find('.//{http://www.opengis.net/kml/2.2}Placemark')
                if placemark_el is None: # Fallback for no namespace or different default
                    placemark_el = individual_kml_root.find('.//Placemark')
                
                if placemark_el is not None:
                    # IMPORTANT: Set the db_id as the id attribute of the Placemark
                    # This ID will be read by OpenLayers and accessible via feature.getId()
                    placemark_el.set('id', str(db_id)) 
                    document_el.append(placemark_el)
                else:
                    self.main_window.log_message(f"No Placemark found in KML for ID {db_id}.", "warning")
            except ET.ParseError as e:
                self.main_window.log_message(f"XML ParseError for KML ID {db_id}: {str(e)}", "error")
            except Exception as e:
                self.main_window.log_message(f"Error processing KML for ID {db_id} for combined view: {str(e)}", "error")
        
        combined_kml_string = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(combined_kml_root, encoding='unicode')
        
        # Display the combined KML in the editor
        self.main_window.kml_editor_widget.display_kml(
            combined_kml_string, 
            f"Multiple KMLs ({len(self.selected_kml_files)})", 
            f"Viewing {len(self.selected_kml_files)} KML files. Edit features on map and save all."
        )
    
    def enter_multi_edit_mode(self):
        """Enable editing mode for multiple KMLs"""
        if not self.selected_kml_files:
            QMessageBox.warning(self.main_window, "No KMLs Selected", 
                               "Please select KML files using the checkboxes first.")
            return
        
        # Enable editing in the KML editor widget
        self.main_window.kml_editor_widget.enter_edit_mode()
        
        # Update button states
        self.main_window.multi_kml_editor_button.setEnabled(False)
        self.main_window.multi_kml_save_button.setEnabled(True)
        self.main_window.multi_kml_cancel_button.setEnabled(True)
        
        # Prevent new selections while editing
        # self.update_table_checkboxes_visibility(False) # REMOVED
        
        self.main_window.log_message(f"Editing {len(self.selected_kml_files)} KML files", "info")
    
    def save_multi_kml_edits(self):
        """Save edits to all selected KML files"""
        if not self.selected_kml_files:
            QMessageBox.warning(self.main_window, "No KMLs Loaded", "No KMLs are currently loaded for editing.")
            return
        
        self.main_window.log_message(f"Attempting to save {len(self.selected_kml_files)} KML files...", "info")
        # Get edited data from editor - this now expects a FeatureCollection JSON string
        self.main_window.kml_editor_widget.get_edited_data_from_js(self._handle_multi_save_geometry)
    
    def _handle_multi_save_geometry(self, geometry_data_str):
        """
        Handle the FeatureCollection geometry data returned from JavaScript for saving multiple KMLs.
        Args:
            geometry_data_str: GeoJSON FeatureCollection as a JSON string from JavaScript.
        """
        try:
            if not geometry_data_str:
                self.main_window.log_message("Received empty geometry data from JS for multi-save.", "error")
                QMessageBox.critical(self.main_window, "Save Error", "No geometry data received from the map.")
                self._revert_ui_after_save_attempt(success=False)
                return

            feature_collection = json.loads(geometry_data_str)

            if not isinstance(feature_collection, dict) or feature_collection.get("type") != "FeatureCollection":
                self.main_window.log_message(f"Unexpected geometry data format from JS. Expected FeatureCollection, got: {type(feature_collection)}", "error")
                QMessageBox.critical(self.main_window, "Save Error", "Invalid geometry data format received from map.")
                self._revert_ui_after_save_attempt(success=False)
                return

            edited_features_map = {}
            for feature in feature_collection.get("features", []):
                props = feature.get("properties", {})
                # db_id in JS is stringified if it came from feature.getId(), ensure consistent type if needed
                # KMLHandler expects db_id as int.
                try:
                    db_id_val = props.get("db_id")
                    if db_id_val is not None:
                        db_id = int(db_id_val) # Convert to int for matching
                        edited_features_map[db_id] = feature
                    else:
                        self.main_window.log_message(f"Feature found without 'db_id' in properties: {props}", "warning")
                except ValueError:
                     self.main_window.log_message(f"Feature found with non-integer 'db_id' in properties: {props.get('db_id')}", "warning")

            saved_any = False
            failed_any = False

            for kml_info in self.selected_kml_files:
                original_db_id = kml_info['db_id'] # This is an int
                kml_file_name = kml_info['kml_file_name']
                
                edited_feature_data = edited_features_map.get(original_db_id)

                if not edited_feature_data:
                    self.main_window.log_message(f"No corresponding edited feature data found for DB ID {original_db_id} ({kml_file_name}). Skipping save for this file.", "warning")
                    # Not necessarily a failure of the whole process, but this file won't be updated.
                    # Consider if this should mark failed_any = True if an update was expected.
                    continue

                individual_geometry_json = json.dumps(edited_feature_data.get("geometry"))
                
                # Use name/description from the JS feature properties if available, otherwise from original kml_info
                feature_props = edited_feature_data.get("properties", {})
                edited_name = feature_props.get('name') if feature_props.get('name') is not None else kml_info.get('name', "Unnamed Polygon")
                edited_description = feature_props.get('description') if feature_props.get('description') is not None else kml_info.get('description', "")
                
                self.main_window.log_message(f"Preparing to save KML ID {original_db_id}: Name='{edited_name}'", "info")

                success = self.kml_handler.save_edited_kml(
                    db_id=original_db_id,
                    original_kml_filename=kml_file_name,
                    edited_geometry_json=individual_geometry_json,
                    edited_name=edited_name,
                    edited_description=edited_description
                )
                
                if success:
                    self.main_window.log_message(f"Successfully saved KML: {kml_file_name}", "info")
                    saved_any = True
                else:
                    self.main_window.log_message(f"Failed to save KML: {kml_file_name}", "error")
                    failed_any = True
            
            self._revert_ui_after_save_attempt(success=saved_any and not failed_any, num_saved=sum(1 for i in edited_features_map if i in [k['db_id'] for k in self.selected_kml_files]), num_failed=failed_any)
            
            if saved_any or not failed_any: # Emit signal if anything was attempted or no failures if nothing to save
                self.multi_kml_saved_signal.emit() 

        except json.JSONDecodeError as e:
            self.main_window.log_message(f"JSON decoding error in _handle_multi_save_geometry: {str(e)}. Data: '{geometry_data_str}'", "error")
            QMessageBox.critical(self.main_window, "Save Error", f"Error processing geometry data from map: {str(e)}")
            self._revert_ui_after_save_attempt(success=False)
        except Exception as e:
            self.main_window.log_message(f"Error saving multi-KML edits: {str(e)}", "error")
            QMessageBox.critical(self.main_window, "Save Error", f"An unexpected error occurred while saving: {str(e)}")
            self._revert_ui_after_save_attempt(success=False)

    def _revert_ui_after_save_attempt(self, success=True, num_saved=0, num_failed=0):
        """Helper to revert UI states after a save attempt."""
        self.main_window.kml_editor_widget.exit_edit_mode(reload_original_kml=False) 
        self.main_window.multi_kml_editor_button.setEnabled(True) 
        self.main_window.multi_kml_save_button.setEnabled(False)
        self.main_window.multi_kml_cancel_button.setEnabled(False)

        if num_failed > 0 and num_saved > 0:
            QMessageBox.warning(self.main_window, "Partial Save", f"{num_saved} KML file(s) saved successfully. {num_failed} KML file(s) failed. Please check logs.")
        elif num_failed > 0:
            QMessageBox.critical(self.main_window, "Save Failed", f"All {num_failed} KML file(s) failed to save. Please check logs.")
        elif num_saved > 0:
            QMessageBox.information(self.main_window, "Save Successful", f"All {num_saved} KML file(s) saved successfully.")
        elif not success: # General failure before individual saves
            pass # Message was already shown by caller
        else: # No files to save, or no changes made that resulted in a save call
             QMessageBox.information(self.main_window, "Save Complete", "Multi-KML save process finished. No changes detected or no files selected for update.")

    def cancel_multi_edit(self):
        """Cancel editing mode for multiple KMLs"""
        self.main_window.kml_editor_widget.exit_edit_mode(reload_original_kml=True) # Reload original combined KML
        
        self.main_window.multi_kml_editor_button.setEnabled(True)
        self.main_window.multi_kml_save_button.setEnabled(False)
        self.main_window.multi_kml_cancel_button.setEnabled(False)
        
        self.main_window.log_message("Multi-KML edit canceled", "info")
    
    @staticmethod
    def _parse_kml_for_name_desc(kml_content_string: str) -> tuple:
        """
        Parses KML content string to extract Placemark name and description.
        
        Args:
            kml_content_string: KML content as string
            
        Returns:
            tuple: (name, description) or (None, None) on failure
        """
        try:
            if not kml_content_string:
                return None, None
                
            root = ET.fromstring(kml_content_string)
            namespaces = {
                'kml': 'http://www.opengis.net/kml/2.2',
                'gx': 'http://www.google.com/kml/ext/2.2' # Google extensions
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
        except Exception:
            return None, None
    
    @staticmethod
    def _extract_placemark_from_kml(kml_content: str) -> str:
        """
        Extract the Placemark element from a KML string
        
        Args:
            kml_content: The KML content as a string
            
        Returns:
            str: The Placemark element as a string, or empty string if not found
        """
        try:
            # Parse the KML string
            root = ET.fromstring(kml_content)
            
            # Find the first Placemark element
            placemark = root.find('.//{http://www.opengis.net/kml/2.2}Placemark')
            if placemark is None:
                placemark = root.find('.//Placemark')  # Fallback
            
            if placemark is not None:
                return ET.tostring(placemark, encoding='unicode')
            return ""
        except Exception:
            return "" 
