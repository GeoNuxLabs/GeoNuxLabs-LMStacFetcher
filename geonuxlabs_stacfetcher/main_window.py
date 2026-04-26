import os
import sys
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests.auth import HTTPBasicAuth

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from geonuxlabs_stacfetcher.constants import (
    DEFAULT_DOWNLOAD_DIR,
    MAX_TILES,
    LOG_FILE,
)
from geonuxlabs_stacfetcher.map_dialog import MapDialog
from geonuxlabs_stacfetcher.login_dialog import LoginDialog

class MainWindow(QMainWindow):
    """
    Main GUI window for the Lantmäteriet STAC downloader.

    This class handles:
    - Login and in-memory storage of credentials.
    - BBOX selection via a map dialog.
    - STAC search and preview of tiles.
    - Download of selected tiles with HTTP Basic Auth.
    - Logging of download sessions (without credentials).
    """

    # Allowed STAC hostnames for security checks.
    # This prevents credentials from being sent to arbitrary domains.
    ALLOWED_STAC_HOSTS = {
        "api.lantmateriet.se",
    }

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("GeoNuxLabs - STAC Downloader (Lantmäteriet)")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)

        # Credentials are kept only in memory and never written to disk.
        self.email: Optional[str] = None
        self.password: Optional[str] = None

        # Current BBOX (set via map dialog)
        self.bbox: Optional[list] = None

        # Download directory for tiles
        self.download_dir: str = DEFAULT_DOWNLOAD_DIR

        # Cached STAC items from the last preview
        self.last_preview_items: Optional[List[Dict]] = None

        # Prompt user for credentials and ensure download directory exists
        self._login()
        self._ensure_download_dir()

        # Build the main UI layout
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(central)

        # ------------------------------------------------------------------
        # Top bar with URL, folder selection, map, preview, and download
        # ------------------------------------------------------------------
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        main_layout.addLayout(top_bar)

        button_style = "font-size: 18px; padding: 8px 16px;"

        # STAC search URL input
        self.api_edit = QLineEdit()
        self.api_edit.setPlaceholderText(
            "Paste Lantmäteriet STAC search URL "
            "(e.g. https://api.lantmateriet.se/stac-hojd/v1/search)"
        )
        self.api_edit.setStyleSheet("font-size: 16px;")
        top_bar.addWidget(self.api_edit, stretch=1)

        # Folder selection button
        self.btn_folder = QPushButton("Select folder")
        self.btn_folder.setStyleSheet(button_style)
        self.btn_folder.clicked.connect(self.choose_download_dir)
        top_bar.addWidget(self.btn_folder)

        # Open map dialog for BBOX selection
        self.btn_open_map = QPushButton("Open map (draw BBOX)")
        self.btn_open_map.setStyleSheet(button_style)
        self.btn_open_map.clicked.connect(self.open_map_dialog)
        top_bar.addWidget(self.btn_open_map)

        # Preview button (enabled after BBOX is set)
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.setStyleSheet(button_style)
        self.btn_preview.clicked.connect(self.preview_download)
        self.btn_preview.setEnabled(False)
        top_bar.addWidget(self.btn_preview)

        # Download button (enabled after preview)
        self.btn_download = QPushButton("Start download")
        self.btn_download.setStyleSheet(button_style)
        self.btn_download.clicked.connect(self.start_download)
        self.btn_download.setEnabled(False)
        top_bar.addWidget(self.btn_download)

        top_bar.addStretch()

        # ------------------------------------------------------------------
        # Progress bar (always visible, but value updated during download)
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

        # Always visible, but may show 0% when idle
        self.progress_container.setVisible(True)
        main_layout.addWidget(self.progress_container)

        # ------------------------------------------------------------------
        # Status + info + folder labels
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

        # Status label for user feedback
        self.status_label = QLabel(
            "No BBOX selected. Open the map to draw one."
        )
        self.status_label.setStyleSheet(
            tight_style + "font-size: 16px; color: white;"
        )

        # Info label with usage note
        self.info_label = QLabel(
            "NOTE: Downloading data may have implications according to your "
            "agreement with Lantmäteriet. Avoid unnecessary large downloads."
        )
        self.info_label.setStyleSheet(
            tight_style + "font-size: 15px; color: orange;"
        )

        # Label showing the current download folder
        self.folder_label = QLabel(self.download_dir)
        self.folder_label.setStyleSheet(
            tight_style + "font-size: 12px; color: #aaaaaa;"
        )

        text_block_layout.addWidget(self.status_label)
        text_block_layout.addWidget(self.info_label)
        text_block_layout.addWidget(self.folder_label)

        main_layout.addWidget(self.text_block_widget)

        # ------------------------------------------------------------------
        # Splash (ASCII art)
        # ------------------------------------------------------------------
        self.splash_widget = QWidget()
        splash_layout = QHBoxLayout(self.splash_widget)
        splash_layout.setContentsMargins(0, 0, 20, 10)
        splash_layout.setSpacing(0)

        splash_layout.addStretch()

        # Load splash text from file if available
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
        self.splash_label.setFont(
            QFontDatabase.systemFont(QFontDatabase.FixedFont)
        )
        self.splash_label.setStyleSheet("font-size: 14px; color: cyan;")
        self.splash_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.splash_label.setWordWrap(False)

        splash_layout.addWidget(self.splash_label)
        main_layout.addWidget(self.splash_widget)

    # ------------------------------------------------------------------
    # Login and setup
    # ------------------------------------------------------------------
    def _login(self) -> None:
        """
        Prompt user for credentials; keep only in memory.

        This method:
        - Shows a modal login dialog.
        - Exits the application if no credentials are provided.
        - Stores email and password in instance attributes (RAM only).
        """
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

        # Credentials are stored only in memory for use with HTTPBasicAuth.
        self.email = email
        self.password = password

    def _ensure_download_dir(self) -> None:
        """
        Ensure that the download directory exists.

        If the directory does not exist, it is created. This avoids
        runtime errors when writing downloaded files.
        """
        os.makedirs(self.download_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Map / BBOX handling
    # ------------------------------------------------------------------
    def open_map_dialog(self) -> None:
        """
        Open the Leaflet map dialog for BBOX selection.

        The MapDialog is expected to call `set_bbox` with the selected
        bounding box when the user finishes drawing.
        """
        dialog = MapDialog(self.set_bbox, self)
        dialog.exec()

    def set_bbox(self, bbox: list) -> None:
        """
        Store BBOX and enable preview.

        Parameters
        ----------
        bbox : list
            The bounding box selected by the user in the map dialog.
        """
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
        """
        Let the user choose a download directory.

        The selected directory is stored and displayed in the UI.
        """
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
    def _validate_stac_url(self, url: str) -> bool:
        """
        Validate the STAC URL for security before use.

        This method enforces:
        - HTTPS scheme (no plain HTTP).
        - Hostname must be in the allowed list.

        Returns
        -------
        bool
            True if the URL is considered safe to use, False otherwise.
        """
        parsed = urlparse(url)

        # Require HTTPS to protect credentials in transit.
        if parsed.scheme.lower() != "https":
            QMessageBox.warning(
                self,
                "Insecure URL",
                (
                    "The STAC URL must use HTTPS to protect your "
                    "credentials.\n\n"
                    f"Current URL: {url}"
                ),
            )
            return False

        # Require the hostname to be in the allowed list.
        hostname = parsed.hostname or ""
        if hostname.lower() not in self.ALLOWED_STAC_HOSTS:
            QMessageBox.warning(
                self,
                "Untrusted STAC host",
                (
                    "The STAC URL does not point to a trusted host.\n\n"
                    f"Current host: {hostname}\n\n"
                    "To protect your Lantmäteriet credentials, this "
                    "tool only allows known hosts such as:\n"
                    "- https://api.lantmateriet.se"
                ),
            )
            return False

        return True

    def _stac_search(self) -> Optional[List[Dict]]:
        """
        Run a STAC search for the current BBOX.

        This method:
        - Validates that a BBOX is set.
        - Validates the STAC URL for HTTPS and allowed host.
        - Sends a POST request with a simple JSON payload containing
          the BBOX and a limit on the number of items.
        - Returns the list of STAC items (features) or None on error.
        """
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

        # Security check: ensure HTTPS and trusted host before sending
        # credentials or any request.
        if not self._validate_stac_url(search_url):
            return None

        # Payload for STAC search: BBOX and a limit on number of items.
        payload = {
            "bbox": self.bbox,
            "limit": 100,
        }

        self.status_label.setText("Searching STAC...")
        QApplication.processEvents()

        try:
            response = requests.post(
                search_url,
                json=payload,
                timeout=60,
            )
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
        """
        Preview number of tiles and enforce limits.

        This method:
        - Runs a STAC search for the current BBOX.
        - Checks the number of returned tiles.
        - Enforces a maximum tile limit to avoid mass downloads.
        - Enables the download button if the user confirms.
        """
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

        # Ask the user if they want to proceed after seeing the count.
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
        """
        Download tiles after explicit user confirmation.

        This method:
        - Requires a successful preview (cached items).
        - Confirms the total number of tiles with the user.
        - Uses HTTP Basic Auth with the stored credentials.
        - Iterates over STAC items and downloads the preferred asset.
        - Updates a progress bar and status label.
        - Logs the session (without credentials).
        """
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

        # HTTP Basic Auth using in-memory credentials.
        auth = HTTPBasicAuth(self.email, self.password)

        # Preferred asset keys, in order of priority.
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

            # Select the first matching preferred asset key.
            asset = None
            for key in preferred_asset_keys:
                if key in assets:
                    asset = assets[key]
                    break

            # Fallback: use the first asset if no preferred key is found.
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

        # Reset progress bar after completion.
        self.progress.setValue(0)
        self.progress.setFormat("")

        # Log the download session (without credentials).
        self._log_download(items, downloaded, failures)

        self.status_label.setText(
            f"Download finished. Success: {downloaded}, "
            f"failures: {failures}."
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

        # Disable download button until a new preview is run.
        self.btn_download.setEnabled(False)

    def _log_download(
        self,
        items: List[Dict],
        downloaded: int,
        failures: int,
    ) -> None:
        """
        Append a simple log entry for this download session.

        The log contains:
        - Timestamp (UTC)
        - STAC URL (without credentials)
        - BBOX
        - Download folder
        - Total tiles, successes, and failures

        Credentials are never written to the log.
        """
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
            # Logging failures are printed to stdout/stderr but do not
            # interrupt the main workflow.
            print("Could not write log:", exc)

