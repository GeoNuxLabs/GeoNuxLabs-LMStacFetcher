from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QDialog, QVBoxLayout

from geonuxlabs_stacfetcher.map_bridge import MapBridge
from geonuxlabs_stacfetcher.map_view import HTML


class MapDialog(QDialog):
    """Dialog containing the Leaflet map for BBOX selection."""

    def __init__(self, bbox_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select BBOX")
        self.resize(900, 600)

        layout = QVBoxLayout(self)
        self.view = QWebEngineView()
        layout.addWidget(self.view)

        profile = self.view.page().profile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )

        self.channel = QWebChannel()
        self.bridge = MapBridge(bbox_callback)
        self.channel.registerObject("pyObj", self.bridge)
        self.view.page().setWebChannel(self.channel)

        self.view.setHtml(HTML, QUrl("qrc:///"))
