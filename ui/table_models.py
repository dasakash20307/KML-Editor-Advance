from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QMessageBox # For PolygonTableModel.setData

import datetime

# Forward declaration for type hinting if needed, or handle through duck typing.
# class MainWindow: pass # Avoid direct import of MainWindow to prevent circular dependencies initially.
# The model's setData method calls self.parent().log_message and self.parent().db_lock_manager.
# This assumes parent() is MainWindow. This will be stored in self.main_window_ref.

# --- Table Model with Checkbox Support ---
class PolygonTableModel(QAbstractTableModel): # QAbstractTableModel inherits QObject, so signals are fine
    evaluation_status_changed = Signal(int, str) # db_id, new_status

    CHECKBOX_COL = 0
    DB_ID_COL = 1
    UUID_COL = 2
    RESPONSE_CODE_COL = 3
    EVALUATION_STATUS_COL = 4
    FARMER_NAME_COL = 5
    VILLAGE_COL = 6
    DATE_ADDED_COL = 7
    KML_FILE_NAME_COL = 8
    PLACEMARK_NAME_COL = 9 # <<<< NEW CONSTANT (adjust index based on actual position)
    KML_FILE_STATUS_COL = 10 # <<<< Indices of subsequent columns will shift
    EDIT_COUNT_COL = 11
    LAST_EDIT_DATE_COL = 12
    EDITOR_DEVICE_ID_COL = 13
    EDITOR_NICKNAME_COL = 14
    DEVICE_CODE_COL = 15
    EXPORT_COUNT_COL = 16
    LAST_EXPORTED_COL = 17
    LAST_MODIFIED_COL = 18

    def __init__(self, data_list=None, parent=None, db_manager_instance=None):
        super().__init__(parent)
        self.db_manager = db_manager_instance
        self.main_window_ref = parent # To access log_message, db_lock_manager from MainWindow for now
        self._data = []
        self._check_states = {}
        self._headers = ["", "DB ID", "UUID", "Response Code", "Evaluation Status", "Farmer Name", "Village", "Date Added", "KML File Name", "Placemark Name", "KML File Status", "Times Edited", "Last Edit Date", "Editor Device ID", "Editor Nickname", "Device Code (Creator)", "Export Count", "Last Exported", "Last Modified"]
        if data_list: self.update_data(data_list)

    def rowCount(self, parent=QModelIndex()): return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        row, col = index.row(), index.column()
        if row >= len(self._data): return None
        record = self._data[row]
        db_id = record[0]

        if role == Qt.ItemDataRole.CheckStateRole and col == self.CHECKBOX_COL:
            return self._check_states.get(db_id, Qt.CheckState.Unchecked)

        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.CHECKBOX_COL: return None
            value = None
            if col == self.DB_ID_COL: value = record[0]
            elif col == self.UUID_COL: value = record[1]
            elif col == self.RESPONSE_CODE_COL: value = record[2]
            elif col == self.EVALUATION_STATUS_COL: value = record[8]
            elif col == self.FARMER_NAME_COL: value = record[3]
            elif col == self.VILLAGE_COL: value = record[4]
            elif col == self.DATE_ADDED_COL: value = record[5]
            elif col == self.KML_FILE_NAME_COL: value = record[10]
            elif col == self.PLACEMARK_NAME_COL: value = record[11] # NEW INDEX
            elif col == self.KML_FILE_STATUS_COL: value = record[12] # Shifted from 11
            elif col == self.EDIT_COUNT_COL: value = record[13] # Shifted from 12
            elif col == self.LAST_EDIT_DATE_COL: value = record[14] # Shifted from 13
            elif col == self.EDITOR_DEVICE_ID_COL: value = record[15] # Shifted from 14
            elif col == self.EDITOR_NICKNAME_COL: value = record[16] # Shifted from 15
            elif col == self.DEVICE_CODE_COL: value = record[9]
            elif col == self.EXPORT_COUNT_COL: value = record[6]
            elif col == self.LAST_EXPORTED_COL: value = record[7]
            elif col == self.LAST_MODIFIED_COL: value = record[18] # Shifted from 16
            else: return None

            if col == self.EXPORT_COUNT_COL and value is None: return "0"
            if col == self.LAST_EXPORTED_COL and value is None: return ""
            if isinstance(value, (datetime.datetime, datetime.date)):
                return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime.datetime) else value.strftime("%Y-%m-%d")
            return str(value) if value is not None else ""

        elif role == Qt.ItemDataRole.BackgroundRole:
            status_value = record[8]
            if status_value == "Eligible": return QColor(144, 238, 144, int(255 * 0.7))
            elif status_value == "Not Eligible": return QColor(255, 182, 193, int(255 * 0.7))
            elif status_value == "Not Evaluated Yet": return QColor(255, 255, 255)
            else: return QColor(255, 255, 255)

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter if col != self.CHECKBOX_COL else Qt.AlignmentFlag.AlignCenter
        elif role == Qt.ItemDataRole.ForegroundRole:
            if col == self.KML_FILE_STATUS_COL and record[11] and \
               ("error" in str(record[11]).lower() or "deleted" in str(record[11]).lower()):
                return QColor("red")
        elif role == Qt.ItemDataRole.FontRole and col != self.CHECKBOX_COL:
             return QFont("Segoe UI", 9)
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid(): return False
        row, col = index.row(), index.column()
        if row >= len(self._data) or not self._data[row]: return False
        
        db_id_any_type = self._data[row][0] # This is the DB ID
        try:
            db_id = int(db_id_any_type)
        except (ValueError, TypeError):
            # Handle error: db_id is not convertible to int. Log or raise.
            if self.main_window_ref and hasattr(self.main_window_ref, 'log_message_callback'):
                 self.main_window_ref.log_message_callback(f"Invalid db_id type: {db_id_any_type}", "error")
            else:
                print(f"Invalid db_id type: {db_id_any_type}")
            return False


        if role == Qt.ItemDataRole.CheckStateRole and col == self.CHECKBOX_COL:
            self._check_states[db_id] = Qt.CheckState(value)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True

        if role == Qt.ItemDataRole.EditRole and col == self.EVALUATION_STATUS_COL:
            new_status = str(value)
            # Emit signal instead of direct DB update.
            # The actual DB update will be handled by DataHandler after connecting to this signal.
            self.evaluation_status_changed.emit(db_id, new_status)
            
            # Optimistically update internal data and UI. 
            # If DB fails, MainWindow/DataHandler should refresh/revert.
            # This provides immediate feedback to the user.
            updated_record_list = list(self._data[row])
            updated_record_list[8] = new_status # EVALUATION_STATUS is at index 8
            self._data[row] = tuple(updated_record_list)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.BackgroundRole])
            return True # Successfully emitted signal and updated UI optimistically

        return False

    def flags(self, index):
        flags = super().flags(index)
        if index.column() == self.CHECKBOX_COL: flags |= Qt.ItemFlag.ItemIsUserCheckable
        elif index.column() == self.EVALUATION_STATUS_COL:
            flags |= Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        else: flags |= Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        return flags

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal: return self._headers[section]
        if role == Qt.ItemDataRole.FontRole and orientation == Qt.Orientation.Horizontal: return QFont("Segoe UI", 9, QFont.Weight.Bold)
        return None

    def update_data(self, new_data_list):
        self.beginResetModel()
        self._data = new_data_list if new_data_list is not None else []
        current_ids = {row[0] for row in self._data if row}
        # Ensure db_id is int for keys in _check_states
        self._check_states = {int(db_id_key): state for db_id_key, state in self._check_states.items() if int(db_id_key) in current_ids}
        self.endResetModel()

    def get_checked_item_db_ids(self): 
        # Ensure db_id is int
        return [int(db_id) for db_id, state in self._check_states.items() if state == Qt.CheckState.Checked]

    def set_all_checkboxes(self, state=Qt.CheckState.Checked):
        self.beginResetModel()
        for row_data in self._data:
            if row_data and len(row_data) > 0:
                 # Ensure db_id is int for keys in _check_states
                self._check_states[int(row_data[0])] = state
        self.endResetModel()

# --- Filter Proxy Model ---
class PolygonFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_uuid_text = ""
        self.filter_export_status = "All"
        self.filter_error_status = "All"

    def set_uuid_filter(self, text): self.filter_uuid_text = text.lower(); self.invalidateFilter()
    def set_export_status_filter(self, status): self.filter_export_status = status; self.invalidateFilter()
    def set_error_status_filter(self, status): self.filter_error_status = status; self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        source_model = self.sourceModel()
        if not isinstance(source_model, PolygonTableModel): 
            return False
            
        if not source_model or source_row >= len(source_model._data): return False
        record = source_model._data[source_row]
        if not record or len(record) < 17: return False 

        if self.filter_uuid_text:
            uuid_val_from_record = record[1] 
            if uuid_val_from_record is None or self.filter_uuid_text not in str(uuid_val_from_record).lower(): return False

        export_count_from_record = record[6] 
        export_count = export_count_from_record if export_count_from_record is not None else 0
        if self.filter_export_status == "Exported" and export_count == 0: return False
        if self.filter_export_status == "Not Exported" and export_count > 0: return False

        kml_status_val_from_record = record[11] 
        kml_status_val = str(kml_status_val_from_record).lower() if kml_status_val_from_record is not None else ""
        if self.filter_error_status == "Error Records" and not ("error" in kml_status_val or "deleted" in kml_status_val): return False
        elif self.filter_error_status == "Valid Records" and ("error" in kml_status_val or "deleted" in kml_status_val): return False

        return True
