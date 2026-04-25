import json
from typing import Callable

from PySide6.QtCore import QObject, Slot


class MapBridge(QObject):
    """Bridge object for receiving BBOX from JavaScript."""

    def __init__(self, callback: Callable[[list], None]):
        super().__init__()
        self._callback = callback

    @Slot(str)
    def receiveBBox(self, bbox_json: str) -> None:
        """Receive BBOX from the web view."""
        bbox = json.loads(bbox_json)
        self._callback(bbox)
