# File: DilasaKMLTool_v4/ui/widgets/google_earth_webview_widget.py
# ----------------------------------------------------------------------
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings # Corrected import
from PySide6.QtCore import QUrl, Slot, Qt # Added Qt import here

class GoogleEarthWebViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.web_view = QWebEngineView()

        # Configure WebEngineSettings if necessary (e.g., enabling JavaScript, plugins)
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True) # Useful for some web content
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True) # For smoother scrolling

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view)
        self.setLayout(layout)

        # Load Google Earth Web
        self.web_view.setUrl(QUrl("https://earth.google.com/web/"))

    @Slot()
    def set_focus_on_webview(self):
        '''
        Attempts to set focus to the web view component.
        '''
        self.web_view.setFocus(Qt.FocusReason.OtherFocusReason)

    def get_web_view(self):
        '''
        Returns the QWebEngineView instance.
        '''
        return self.web_view

    def cleanup(self):
        """
        Placeholder for any cleanup logic needed for the web view.
        For example, stopping media, clearing cache, or other resource releases.
        """
        # self.web_view.stop() # Example: stop loading
        # self.web_view.setUrl(QUrl("about:blank")) # Example: clear page
        # No specific cleanup needed for QWebEngineView itself unless page-specific actions.
        pass

if __name__ == '__main__':
    # This part is for basic testing if you run this file directly
    # It won't be used when MainWindow imports the widget
    import sys
    from PySide6.QtWidgets import QApplication
    # Qt is already imported at the top level, so no need for a separate import here for the test.
    # from PySide6.QtCore import Qt 

    app = QApplication(sys.argv) # QApplication instance needed for QWebEngineView
    widget = GoogleEarthWebViewWidget()
    widget.setWindowTitle("Google Earth Web View Test")
    widget.setGeometry(100, 100, 800, 600)
    widget.show()
    
    # Example of calling set_focus_on_webview (though focus might be immediate on show)
    # from PySide6.QtCore import QTimer # Requires QTimer import
    # QTimer.singleShot(1000, widget.set_focus_on_webview) 

    sys.exit(app.exec())
