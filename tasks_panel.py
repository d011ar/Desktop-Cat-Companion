from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from reminder_store import Reminder, ReminderStore


class TasksPanel(QWidget):
    tasks_changed = Signal()

    def __init__(self, reminder_store: ReminderStore, parent=None) -> None:
        super().__init__(parent)
        self.reminder_store = reminder_store

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.list_container)

        self.empty_label = QLabel()
        self.empty_label.setWordWrap(True)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)

        clear_button = QPushButton("Clear Completed")
        clear_button.clicked.connect(self.clear_completed)

        button_layout = QHBoxLayout()
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addLayout(button_layout)
        layout.addWidget(self.empty_label)
        layout.addWidget(scroll, 1)

        self.refresh()

    def refresh(self) -> None:
        self._clear_layout()
        items = self.reminder_store.list_all()
        self.empty_label.setText("" if items else "No reminders or todos.")

        for item in items:
            self.list_layout.addWidget(self._build_item(item))
        self.list_layout.addStretch(1)

    def clear_completed(self) -> None:
        self.reminder_store.clear_completed()
        self.refresh()
        self.tasks_changed.emit()

    def _build_item(self, item: Reminder) -> QWidget:
        frame = QFrame()
        frame.setObjectName("taskItem")
        frame.setStyleSheet(
            """
            QFrame#taskItem {
                background: rgba(255, 255, 255, 210);
                border: 1px solid rgba(190, 190, 190, 180);
                border-radius: 6px;
            }
            """
        )

        title = QLabel(self._title(item))
        title.setWordWrap(True)

        complete_button = QPushButton("Done" if not item.completed else "Completed")
        complete_button.setEnabled(not item.completed)
        complete_button.clicked.connect(lambda _checked=False, id=item.id: self._complete(id))

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda _checked=False, id=item.id: self._delete(id))

        buttons = QHBoxLayout()
        buttons.addWidget(complete_button)
        buttons.addWidget(delete_button)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(title)
        layout.addLayout(buttons)
        return frame

    def _complete(self, id: str) -> None:
        self.reminder_store.complete(id)
        self.refresh()
        self.tasks_changed.emit()

    def _delete(self, id: str) -> None:
        self.reminder_store.delete(id)
        self.refresh()
        self.tasks_changed.emit()

    def _clear_layout(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _title(self, item: Reminder) -> str:
        status = "Completed" if item.completed else "Open"
        if item.is_reminder:
            trigger_at = item.trigger_datetime
            when = trigger_at.strftime("%Y-%m-%d %H:%M") if isinstance(trigger_at, datetime) else "no time"
            return f"Reminder - {status} - {when}\n{item.text}"
        return f"Todo - {status}\n{item.text}"
