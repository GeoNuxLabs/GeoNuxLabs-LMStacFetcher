from typing import Tuple

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)


class LoginDialog(QDialog):
    """Dialog for collecting Lantmäteriet credentials."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lantmäteriet – Login")

        self.email_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Email:", self.email_edit)
        form.addRow("Password:", self.password_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_credentials(self) -> Tuple[str, str]:
        """Return trimmed email and password."""
        return (
            self.email_edit.text().strip(),
            self.password_edit.text().strip(),
        )
