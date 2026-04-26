from typing import Tuple

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)


class LoginDialog(QDialog):
    """
    Dialog for collecting Lantmäteriet credentials.

    This dialog is responsible only for UI input and does not perform
    any network operations. It returns the email and password as plain
    strings to the caller, which is then responsible for handling them
    securely.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Lantmäteriet – Login")

        # Email input field
        self.email_edit = QLineEdit()
        # Password input field, masked for privacy
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)

        # Form layout to align labels and fields
        form = QFormLayout()
        form.addRow("Email:", self.email_edit)
        form.addRow("Password:", self.password_edit)

        # OK/Cancel buttons for the dialog
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # Main layout for the dialog
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_credentials(self) -> Tuple[str, str]:
        """
        Return trimmed email and password.

        The caller is responsible for:
        - Using HTTPS when sending these credentials.
        - Not storing them on disk.
        - Clearing them from memory when no longer needed.
        """
        return (
            self.email_edit.text().strip(),
            self.password_edit.text().strip(),
        )
