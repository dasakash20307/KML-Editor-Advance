from PySide6.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel, QApplication, QPushButton

class APIImportProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Import Progress")
        self.setModal(True)
        self.setMinimumWidth(400)
        self._was_cancelled = False

        layout = QVBoxLayout(self)
        self.total_label = QLabel("Total Records to Process: 0")
        layout.addWidget(self.total_label)

        self.processed_label = QLabel("Records Processed (Attempted): 0")
        layout.addWidget(self.processed_label)

        self.new_added_label = QLabel("New Records Added: 0")
        layout.addWidget(self.new_added_label)

        self.skipped_label = QLabel("Records Skipped (Duplicates/Errors): 0")
        layout.addWidget(self.skipped_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Will be updated by set_total_records
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._perform_cancel)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)

    def _perform_cancel(self):
        self._was_cancelled = True
        self.reject() # Rejects the dialog

    def set_total_records(self, count):
        self.total_label.setText(f"Total Records to Process: {count}")
        self.progress_bar.setRange(0, count if count > 0 else 100) # Ensure range is not 0-0

    def update_progress(self, processed_count, skipped_count, new_added_count):
        self.processed_label.setText(f"Records Processed (Attempted): {processed_count}")
        self.new_added_label.setText(f"New Records Added: {new_added_count}")
        self.skipped_label.setText(f"Records Skipped (Duplicates/Errors): {skipped_count}")
        self.progress_bar.setValue(processed_count)
        QApplication.processEvents() # Allow UI to update

    def was_cancelled(self):
        return self._was_cancelled
