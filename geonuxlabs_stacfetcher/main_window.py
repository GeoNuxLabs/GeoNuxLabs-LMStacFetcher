import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

import requests
from requests.auth import HTTPBasicAuth

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QProgressBar,
    QApplication,
    QDialog,
)

from geonuxlabs_stacfetcher.constants import DEFAULT_DOWNLOAD_DIR, MAX_TILES, LOG_FILE
from geonuxlabs_stacfetcher.login_dialog import LoginDialog
from geonuxlabs_stacfetcher.map_dialog import MapDialog


class MainWindow(QMainWindow):
    """Main GUI window for the Lantmäteriet STAC downloader."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("GeoNuxLabs - LM STAC Downloader")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)

        self.email: Optional[str] = None
        self.password: Optional[str] = None
        self.bbox: Optional[list] = None
        self.download_dir: str = DEFAULT_DOWNLOAD_DIR
        self.last_preview_items: Optional[List[Dict]] = None

        self._login()
        self._ensure_download_dir()

        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(central)

        # ------------------------------------------------------------------
        # Top bar
        # ------------------------------------------------------------------
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        main_layout.addLayout(top_bar)

        button_style = "font-size: 18px; padding: 8px 16px;"

        self.api_edit = QLineEdit()
        self.api_edit.setPlaceholderText(
            "Paste Lantmäteriet STAC search URL (e.g. /stac-*/v1/search)"
        )
        self.api_edit.setStyleSheet("font-size: 16px;")
        top_bar.addWidget(self.api_edit, stretch=1)

        self.btn_folder = QPushButton("Select folder")
        self.btn_folder.setStyleSheet(button_style)
        self.btn_folder.clicked.connect(self.choose_download_dir)
        top_bar.addWidget(self.btn_folder)

        self.btn_open_map = QPushButton("Open map (draw BBOX)")
        self.btn_open_map.setStyleSheet(button_style)
        self.btn_open_map.clicked.connect(self.open_map_dialog)
        top_bar.addWidget(self.btn_open_map)

        self.btn_preview = QPushButton("Preview")
        self.btn_preview.setStyleSheet(button_style)
        self.btn_preview.clicked.connect(self.preview_download)
        self.btn_preview.setEnabled(False)
        top_bar.addWidget(self.btn_preview)

        self.btn_download = QPushButton("Start download")
        self.btn_download.setStyleSheet(button_style)
        self.btn_download.clicked.connect(self.start_download)
        self.btn_download.setEnabled(False)
        top_bar.addWidget(self.btn_download)

        top_bar.addStretch()

        # ------------------------------------------------------------------
        # Progress bar (always visible)
        # ------------------------------------------------------------------
        self.progress_container = QWidget()
        pc_layout = QVBoxLayout(self.progress_container)
        pc_layout.setContentsMargins(0, 0, 0, 0)
        pc_layout.setSpacing(0)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)

        pc_layout.addWidget(self.progress)

        # Always visible
        self.progress_container.setVisible(True)

        main_layout.addWidget(self.progress_container)


        # ------------------------------------------------------------------
        # Tight text block (status + info + folder)
        # ------------------------------------------------------------------
        self.text_block_widget = QWidget()
        text_block_layout = QVBoxLayout(self.text_block_widget)
        text_block_layout.setContentsMargins(0, 5, 0, 5)
        text_block_layout.setSpacing(0)

        tight_style = """
            QLabel {
                padding: 0px;
                margin: 0px;
            }
        """

        self.status_label = QLabel("No BBOX selected. Open the map to draw one.")
        self.status_label.setStyleSheet(tight_style + "font-size: 16px; color: white;")

        self.info_label = QLabel(
            "NOTE: Downloading data may have implications according to your "
            "agreement with Lantmäteriet. Avoid unnecessary large downloads."
        )
        self.info_label.setStyleSheet(tight_style + "font-size: 13px; color: orange;")

        self.folder_label = QLabel(self.download_dir)
        self.folder_label.setStyleSheet(tight_style + "font-size: 12px; color: #aaaaaa;")

        text_block_layout.addWidget(self.status_label)
        text_block_layout.addWidget(self.info_label)
        text_block_layout.addWidget(self.folder_label)

        main_layout.addWidget(self.text_block_widget)

        # ------------------------------------------------------------------
        # Splash (ASCII)
        # ------------------------------------------------------------------
        self.splash_widget = QWidget()
        splash_layout = QHBoxLayout(self.splash_widget)
        splash_layout.setContentsMargins(0, 0, 20, 10)
        splash_layout.setSpacing(0)

        splash_layout.addStretch()

        try:
            with open(
                "geonuxlabs_stacfetcher/resources/splash.txt",
                "r",
                encoding="utf-8",
            ) as f:
                splash_text = f.read()
        except FileNotFoundError:
            splash_text = "Splash file missing"

        self.splash_label = QLabel(splash_text)
        self.splash_label.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.splash_label.setStyleSheet("font-size: 14px; color: cyan;")
        self.splash_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.splash_label.setWordWrap(False)

        splash_layout.addWidget(self.splash_label)
        main_layout.addWidget(self.splash_widget)

        # ------------------------------------------------------------------
        # Viewer container (MÅSTE ligga sist)
        # ------------------------------------------------------------------
        self.viewer_container = QVBoxLayout()
        main_layout.addLayout(self.viewer_container)


    # ------------------------------------------------------------------
    # Login and setup
    # ------------------------------------------------------------------
    def _login(self) -> None:
        """Prompt user for credentials; keep only in memory."""
        dialog = LoginDialog(self)
        if dialog.exec() != QDialog.Accepted:
            QMessageBox.warning(self, "Aborted", "No login provided.")
            sys.exit(0)

        email, password = dialog.get_credentials()
        if not email or not password:
            QMessageBox.warning(
                self,
                "Error",
                "Email and password are required.",
            )
            sys.exit(0)

        self.email = email
        self.password = password

    def _ensure_download_dir(self) -> None:
        """Ensure that the download directory exists."""
        os.makedirs(self.download_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Map / BBOX handling
    # ------------------------------------------------------------------
    def open_map_dialog(self) -> None:
        """Open the Leaflet map dialog for BBOX selection."""
        dialog = MapDialog(self.set_bbox, self)
        dialog.exec()

    def set_bbox(self, bbox: list) -> None:
        """Store BBOX and enable preview."""
        self.bbox = bbox
        self.status_label.setText(
            "BBOX selected. Click 'Preview' to inspect tiles."
        )
        self.btn_preview.setEnabled(True)
        self.btn_download.setEnabled(False)
        self.last_preview_items = None

    # ------------------------------------------------------------------
    # Folder selection
    # ------------------------------------------------------------------
    def choose_download_dir(self) -> None:
        """Let the user choose a download directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select download folder",
            self.download_dir,
        )
        if directory:
            self.download_dir = directory
            self.folder_label.setText(directory)

    # ------------------------------------------------------------------
    # STAC search and preview
    # ------------------------------------------------------------------
    def _stac_search(self) -> Optional[List[Dict]]:
        """Run a STAC search for the current BBOX."""
        if not self.bbox:
            QMessageBox.warning(
                self,
                "No BBOX",
                "Draw a BBOX in the map first.",
            )
            return None

        search_url = self.api_edit.text().strip()
        if not search_url:
            QMessageBox.warning(
                self,
                "No STAC URL",
                "Paste the STAC search URL from Lantmäteriet first.",
            )
            return None

        payload = {
            "bbox": self.bbox,
            "limit": 10000,
        }

        self.status_label.setText("Searching STAC...")
        QApplication.processEvents()

        try:
            response = requests.post(search_url, json=payload, timeout=60)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "STAC search error",
                str(exc),
            )
            return None

        if response.status_code != 200:
            QMessageBox.critical(
                self,
                "STAC search error",
                f"{response.status_code}: {response.text[:500]}",
            )
            return None

        data = response.json()
        items = data.get("features", [])
        return items

    def preview_download(self) -> None:
        """Preview number of tiles and enforce limits."""
        items = self._stac_search()
        if items is None:
            return

        count = len(items)
        if count == 0:
            QMessageBox.information(
                self,
                "No tiles",
                "No tiles were found in the selected area.",
            )
            self.status_label.setText("No tiles found.")
            self.last_preview_items = None
            self.btn_download.setEnabled(False)
            return

        if count > MAX_TILES:
            QMessageBox.warning(
                self,
                "Too many tiles",
                (
                    f"STAC search returned {count} tiles.\n\n"
                    f"The maximum allowed in this tool is {MAX_TILES} to "
                    "avoid unintended mass downloads.\n"
                    "Please narrow your BBOX and try again."
                ),
            )
            self.status_label.setText(
                f"Too many tiles ({count}). Narrow your BBOX."
            )
            self.last_preview_items = None
            self.btn_download.setEnabled(False)
            return

        self.last_preview_items = items
        self.status_label.setText(
            f"Preview: {count} tiles found. Ready for confirmation."
        )
        self.btn_download.setEnabled(True)

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Preview")
        msg.setText(
            f"STAC search found {count} tiles within your BBOX.\n\n"
            "Downloading data may have implications according to your "
            "agreement with Lantmäteriet.\n"
            "Do you want to proceed to download?"
        )
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        result = msg.exec()

        if result == QMessageBox.Cancel:
            self.status_label.setText(
                "Download cancelled after preview."
            )
            self.btn_download.setEnabled(False)
        else:
            self.status_label.setText(
                "Preview confirmed. Click 'Start download' to continue."
            )

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------
    def start_download(self) -> None:
        """Download tiles after explicit user confirmation."""
        if not self.last_preview_items:
            QMessageBox.warning(
                self,
                "No preview",
                "Run 'Preview' before starting the download.",
            )
            return

        items = self.last_preview_items
        count = len(items)

        confirm = QMessageBox.question(
            self,
            "Confirm download",
            (
                f"You are about to download {count} tiles.\n\n"
                "Are you sure you want to continue?"
            ),
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            self.status_label.setText("Download cancelled by user.")
            return

        auth = HTTPBasicAuth(self.email, self.password)
        preferred_asset_keys = [
            "data",
            "elevation",
            "dtm",
            "dsm",
            "image",
            "ortho",
            "laz",
            "las",
            "pointcloud",
            "pc",
        ]

        self.status_label.setText("Starting download...")
        self.progress_container.setVisible(True)
        self.progress.setValue(0)
        QApplication.processEvents()

        downloaded = 0
        failures = 0
        total = len(items)

        for index, item in enumerate(items):
            assets = item.get("assets", {})
            if not assets:
                failures += 1
                continue

            asset = None
            for key in preferred_asset_keys:
                if key in assets:
                    asset = assets[key]
                    break

            if asset is None:
                asset = list(assets.values())[0]

            url = asset.get("href")
            if not url:
                failures += 1
                continue

            self.status_label.setText(
                f"Downloading tile {index + 1}/{total}..."
            )
            progress_percent = int((index + 1) / total * 100)
            self.progress.setValue(progress_percent)
            QApplication.processEvents()

            try:
                response = requests.get(
                    url,
                    auth=auth,
                    stream=True,
                    timeout=120,
                )
            except Exception:
                failures += 1
                continue

            if response.status_code != 200:
                failures += 1
                continue

            collection = item.get("collection", "lm_data")
            ext = os.path.splitext(url)[1] or ".dat"
            filename = f"{collection}_tile_{index}{ext}"
            out_path = os.path.join(self.download_dir, filename)

            try:
                with open(out_path, "wb") as file_obj:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file_obj.write(chunk)
                downloaded += 1
            except Exception:
                failures += 1
        
        self.progress.setValue(0)
        self.progress.setFormat("")

        self._log_download(items, downloaded, failures)

        self.status_label.setText(
            f"Download finished. Success: {downloaded}, failures: {failures}."
        )
        QMessageBox.information(
            self,
            "Done",
            (
                "Download finished.\n\n"
                f"Success: {downloaded}\n"
                f"Failures: {failures}\n\n"
                f"Log written to: {os.path.abspath(LOG_FILE)}"
            ),
        )

        self.btn_download.setEnabled(False)

    def _log_download(
        self,
        items: List[Dict],
        downloaded: int,
        failures: int,
    ) -> None:
        """Append a simple log entry for this download session."""
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as log_file:
                log_file.write(
                    "------------------------------------------------------------\n"
                )
                log_file.write(
                    f"Timestamp: {datetime.utcnow().isoformat()}Z\n"
                )
                log_file.write(
                    f"STAC URL: {self.api_edit.text().strip()}\n"
                )
                log_file.write(f"BBOX: {self.bbox}\n")
                log_file.write(
                    f"Download folder: {self.download_dir}\n"
                )
                log_file.write(f"Total tiles: {len(items)}\n")
                log_file.write(
                    f"Success: {downloaded}, Failures: {failures}\n"
                )
        except Exception as exc:
            print("Could not write log:", exc)
