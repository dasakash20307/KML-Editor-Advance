from PySide6.QtWidgets import QStyledItemDelegate, QComboBox
from PySide6.QtCore import Qt

class EvaluationStatusDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.options = ["Not Evaluated Yet", "Eligible", "Not Eligible"]

    def createEditor(self, parent_widget, option, index):
        editor = QComboBox(parent_widget)
        editor.addItems(self.options)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        editor.setCurrentText(value if value in self.options else "Not Evaluated Yet")

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)
