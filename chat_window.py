from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from agent_core import AgentCore, AgentResult


class ChatWorker(QObject):
    finished = Signal(object)

    def __init__(self, agent: AgentCore, message: str) -> None:
        super().__init__()
        self.agent = agent
        self.message = message

    @Slot()
    def run(self) -> None:
        result = self.agent.handle_message(self.message)
        self.finished.emit(result)


class ChatPanel(QWidget):
    message_started = Signal()
    message_finished = Signal()
    tasks_changed = Signal()

    def __init__(self, agent: AgentCore | None = None, parent=None) -> None:
        super().__init__(parent)
        self.agent = agent or AgentCore()
        self.thread = None
        self.worker = None

        self.status_label = QLabel(self._status_text())
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setPlaceholderText("The cat is waiting for your message...")

        self.input = QLineEdit()
        self.input.setPlaceholderText("Say something to the cat...")
        self.input.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.addWidget(self.input, 1)
        input_layout.addWidget(self.send_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self.status_label)
        layout.addWidget(self.history, 1)
        layout.addLayout(input_layout)

    def _status_text(self) -> str:
        if self.agent.llm_client.available:
            return f"Connected model: {self.agent.llm_client.model}"
        return "Local cat mode: OPENAI_API_KEY was not found"

    @Slot()
    def send_message(self) -> None:
        message = self.input.text().strip()
        if not message or self.thread is not None:
            return

        self.input.clear()
        self._append("You", message)
        self._set_busy(True)
        self.message_started.emit()

        self.thread = QThread(self)
        self.worker = ChatWorker(self.agent, message)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._handle_reply)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._clear_thread)
        self.thread.start()

    @Slot(object)
    def _handle_reply(self, result: AgentResult) -> None:
        self._append("Cat", result.reply)
        self._set_busy(False)
        if result.changed:
            self.tasks_changed.emit()
        self.message_finished.emit()

    @Slot()
    def _clear_thread(self) -> None:
        self.thread = None
        self.worker = None

    def _append(self, speaker: str, text: str) -> None:
        self.history.append(f"<b>{speaker}:</b> {self._escape(text)}")

    def append_system_message(self, text: str) -> None:
        self._append("Cat", text)

    def _set_busy(self, busy: bool) -> None:
        self.input.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        self.send_button.setText("Thinking..." if busy else "Send")

    @staticmethod
    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
