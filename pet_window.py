import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QCursor, QMovie, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from agent_core import AgentCore
from chat_window import ChatPanel
from tasks_panel import TasksPanel


PET_SIZE = 128
BUBBLE_WIDTH = 360
BUBBLE_HEIGHT = 330
BUBBLE_GAP = 10
STEP_PIXELS = 4
MOVE_TICK_MS = 45
SPRITE_FRAME_SIZE = 32
SPRITE_TICK_MS = 180
AUTO_POSE_MS = 5000
CHAT_FACE_MS = 1800
REMINDER_CHECK_MS = 15000
PROACTIVE_CARE_MS = 45 * 60 * 1000


class CatPose(str, Enum):
    EAT = "eat"
    WALK_SIDE = "walk_side"
    SLEEP = "sleep"
    WALK_DOWN = "walk_down"
    WALK_UP = "walk_up"
    AUTO = "auto"


class CatColor(str, Enum):
    WHITE = "white"
    YELLOW = "yellow"
    BROWN = "brown"
    BLACK = "black"


@dataclass(frozen=True)
class AnimationSpec:
    row: int
    frames: tuple[int, ...]
    moves: bool = False
    flip_with_direction: bool = False


COLOR_OFFSETS = {
    CatColor.WHITE: 0,
    CatColor.YELLOW: 4,
    CatColor.BROWN: 8,
    CatColor.BLACK: 12,
}

POSE_SPECS = {
    CatPose.EAT: AnimationSpec(row=4, frames=(3, 2, 1, 0)),
    CatPose.WALK_SIDE: AnimationSpec(row=0, frames=(0, 1, 2), moves=True, flip_with_direction=True),
    CatPose.SLEEP: AnimationSpec(row=0, frames=(3,)),
    CatPose.WALK_DOWN: AnimationSpec(row=2, frames=(0, 1, 2)),
    CatPose.WALK_UP: AnimationSpec(row=1, frames=(0, 1, 2)),
}

AUTO_SEQUENCE = (
    CatPose.EAT,
    CatPose.WALK_SIDE,
    CatPose.SLEEP,
    CatPose.WALK_DOWN,
    CatPose.WALK_UP,
)


class PetWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.agent_core = AgentCore()
        self.assets_dir = Path(__file__).resolve().parent / "assets"
        self.idle_movie = self._load_movie("cat_idle.gif")
        self.walk_movie = self._load_movie("cat_walk.gif")
        self.sprite_sheet = self._load_sprite_sheet()
        self.placeholder = self._make_placeholder()

        self.drag_offset = QPoint()
        self.dragging = False
        self.paused = False
        self.bubble_visible = True
        self.direction = 1
        self.target = QPoint()
        self.sprite_frame_index = 0
        self.active_frames: tuple[int, ...] = ()
        self.active_row = 0
        self.active_flip_with_direction = False

        self.color = CatColor.WHITE
        self.selected_pose = CatPose.EAT
        self.current_pose = CatPose.EAT
        self.auto_index = 0
        self.chat_override = False
        self.last_interaction_at = datetime.now()

        self.cat_label = QLabel()
        self.cat_label.setAlignment(Qt.AlignCenter)
        self.cat_label.setFixedSize(PET_SIZE, PET_SIZE)
        self.cat_label.installEventFilter(self)

        self.bubble = self._build_bubble()
        self.bubble.installEventFilter(self)
        self._build_layout()
        self._configure_window()

        self._apply_pose(CatPose.EAT)
        self._move_to_start_position()

        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self._move_tick)
        self.move_timer.start(MOVE_TICK_MS)

        self.sprite_timer = QTimer(self)
        self.sprite_timer.timeout.connect(self._advance_sprite_frame)
        self.sprite_timer.start(SPRITE_TICK_MS)

        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self._advance_auto_pose)

        self.chat_restore_timer = QTimer(self)
        self.chat_restore_timer.setSingleShot(True)
        self.chat_restore_timer.timeout.connect(self._restore_after_chat)

        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self._check_due_reminders)
        self.reminder_timer.start(REMINDER_CHECK_MS)

        self.proactive_timer = QTimer(self)
        self.proactive_timer.timeout.connect(self._send_proactive_care)
        self.proactive_timer.start(PROACTIVE_CARE_MS)

    def _build_layout(self) -> None:
        self.root_layout = QHBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(BUBBLE_GAP)
        self.root_layout.addWidget(self.cat_label, 0, Qt.AlignBottom)
        self.root_layout.addWidget(self.bubble, 0, Qt.AlignVCenter)
        self._sync_window_size()

    def _configure_window(self) -> None:
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_menu)

    def _build_bubble(self) -> QFrame:
        bubble = QFrame()
        bubble.setObjectName("bubble")
        bubble.setFixedSize(BUBBLE_WIDTH, BUBBLE_HEIGHT)
        bubble.setStyleSheet(
            """
            QFrame#bubble {
                background: rgba(255, 255, 255, 235);
                border: 1px solid rgba(160, 160, 160, 170);
                border-radius: 16px;
            }
            QTabWidget::pane {
                border: 0;
            }
            QTabBar::tab {
                padding: 6px 12px;
                margin: 2px;
            }
            QPushButton, QRadioButton {
                min-height: 28px;
            }
            QTextEdit, QLineEdit {
                background: rgba(255, 255, 255, 245);
                border: 1px solid rgba(180, 180, 180, 180);
                border-radius: 6px;
                padding: 4px;
            }
            """
        )

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_chat_tab(), "Chat")
        self.tabs.addTab(self._build_tasks_tab(), "Tasks")
        self.tabs.addTab(self._build_action_tab(), "Actions")
        self.tabs.addTab(self._build_color_tab(), "Colors")

        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.tabs)
        return bubble

    def _build_chat_tab(self) -> QWidget:
        self.chat_panel = ChatPanel(self.agent_core)
        self.chat_panel.message_started.connect(self._face_user_for_chat)
        self.chat_panel.message_finished.connect(self._schedule_chat_restore)
        self.chat_panel.message_started.connect(self._mark_interaction)
        self.chat_panel.tasks_changed.connect(self._refresh_tasks)
        return self.chat_panel

    def _build_tasks_tab(self) -> QWidget:
        self.tasks_panel = TasksPanel(self.agent_core.reminder_store)
        self.tasks_panel.tasks_changed.connect(self._refresh_tasks)
        return self.tasks_panel

    def _build_action_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        actions = [
            ("Eat", CatPose.EAT),
            ("Walk Side", CatPose.WALK_SIDE),
            ("Sleep", CatPose.SLEEP),
            ("Walk Down", CatPose.WALK_DOWN),
            ("Walk Up", CatPose.WALK_UP),
            ("Auto Cycle", CatPose.AUTO),
        ]
        for index, (text, pose) in enumerate(actions):
            button = QPushButton(text)
            button.clicked.connect(lambda _checked=False, selected=pose: self.set_pose(selected))
            layout.addWidget(button, index // 2, index % 2)

        hint = QLabel("Choose an action to keep that pose. Auto Cycle changes pose every 5 seconds.")
        hint.setWordWrap(True)
        layout.addWidget(hint, 3, 0, 1, 2)
        layout.setRowStretch(4, 1)
        return tab

    def _build_color_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        group = QButtonGroup(tab)
        colors = [
            ("White", CatColor.WHITE),
            ("Yellow", CatColor.YELLOW),
            ("Brown", CatColor.BROWN),
            ("Black", CatColor.BLACK),
        ]
        for text, color in colors:
            button = QRadioButton(text)
            button.setChecked(color == self.color)
            button.clicked.connect(lambda _checked=False, selected=color: self.set_color(selected))
            group.addButton(button)
            layout.addWidget(button)

        layout.addStretch(1)
        return tab

    def _load_movie(self, filename: str) -> QMovie | None:
        path = self.assets_dir / filename
        if not path.exists():
            return None
        movie = QMovie(str(path))
        movie.setScaledSize(QSize(PET_SIZE, PET_SIZE))
        if not movie.isValid():
            return None
        return movie

    def _load_sprite_sheet(self) -> QPixmap | None:
        path = self.assets_dir / "cat.png"
        if not path.exists():
            return None
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return None
        return pixmap

    def _make_placeholder(self) -> QPixmap:
        pixmap = QPixmap(PET_SIZE, PET_SIZE)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        painter.setBrush(Qt.white)
        painter.drawEllipse(30, 36, 68, 62)
        painter.drawEllipse(42, 78, 46, 34)

        painter.drawPolygon([QPoint(40, 42), QPoint(48, 18), QPoint(58, 44)])
        painter.drawPolygon([QPoint(70, 44), QPoint(84, 18), QPoint(90, 45)])

        painter.setBrush(Qt.black)
        painter.drawEllipse(52, 58, 6, 8)
        painter.drawEllipse(76, 58, 6, 8)
        painter.drawEllipse(64, 70, 6, 4)

        painter.setPen(Qt.black)
        painter.drawLine(48, 72, 26, 66)
        painter.drawLine(48, 78, 24, 80)
        painter.drawLine(82, 72, 104, 66)
        painter.drawLine(82, 78, 106, 80)

        painter.end()
        return pixmap

    def set_pose(self, pose: CatPose) -> None:
        self.chat_override = False
        self.chat_restore_timer.stop()
        self.selected_pose = pose

        if pose == CatPose.AUTO:
            self.auto_index = 0
            self.auto_timer.start(AUTO_POSE_MS)
            self._advance_auto_pose()
            return

        self.auto_timer.stop()
        self._apply_pose(pose)

    def set_color(self, color: CatColor) -> None:
        self.color = color
        self.sprite_frame_index = 0
        self._render_current_frame()

    def _apply_pose(self, pose: CatPose) -> None:
        self.current_pose = pose
        spec = POSE_SPECS[pose]
        self.active_row = spec.row
        self.active_frames = spec.frames
        self.active_flip_with_direction = spec.flip_with_direction
        self.sprite_frame_index = 0

        if spec.moves:
            self._choose_next_target()
        else:
            self.target = self.pos()

        if self._try_apply_gif_pose(pose):
            return
        self._render_current_frame()

    def _try_apply_gif_pose(self, pose: CatPose) -> bool:
        movie = None
        if pose == CatPose.WALK_SIDE:
            movie = self.walk_movie or self.idle_movie
        elif pose == CatPose.EAT:
            movie = self.idle_movie

        if movie is None:
            if self.cat_label.movie():
                self.cat_label.movie().stop()
                self.cat_label.setMovie(None)
            return False

        self.cat_label.setMovie(movie)
        movie.start()
        return True

    def _render_current_frame(self) -> None:
        if self.cat_label.movie():
            self.cat_label.movie().stop()
            self.cat_label.setMovie(None)

        if not self.sprite_sheet or not self.active_frames:
            self.cat_label.setPixmap(self.placeholder)
            return

        columns = max(1, self.sprite_sheet.width() // SPRITE_FRAME_SIZE)
        rows = max(1, self.sprite_sheet.height() // SPRITE_FRAME_SIZE)
        frame_column = self.active_frames[self.sprite_frame_index % len(self.active_frames)]
        column = COLOR_OFFSETS[self.color] + frame_column
        column = max(0, min(columns - 1, column))
        row = max(0, min(rows - 1, self.active_row))

        frame = self.sprite_sheet.copy(
            column * SPRITE_FRAME_SIZE,
            row * SPRITE_FRAME_SIZE,
            SPRITE_FRAME_SIZE,
            SPRITE_FRAME_SIZE,
        )
        if self.active_flip_with_direction and self.direction < 0:
            frame = frame.transformed(QTransform().scale(-1, 1))

        self.cat_label.setPixmap(
            frame.scaled(
                PET_SIZE,
                PET_SIZE,
                Qt.KeepAspectRatio,
                Qt.FastTransformation,
            )
        )

    def _advance_sprite_frame(self) -> None:
        if self.cat_label.movie() or len(self.active_frames) <= 1:
            return
        self.sprite_frame_index += 1
        self._render_current_frame()

    def _advance_auto_pose(self) -> None:
        if self.chat_override:
            return
        pose = AUTO_SEQUENCE[self.auto_index % len(AUTO_SEQUENCE)]
        self.auto_index += 1
        self._apply_pose(pose)

    def _face_user_for_chat(self) -> None:
        self.chat_override = True
        self.chat_restore_timer.stop()
        self._apply_pose(CatPose.WALK_DOWN)

    def _schedule_chat_restore(self) -> None:
        self.chat_restore_timer.start(CHAT_FACE_MS)

    def _restore_after_chat(self) -> None:
        self.chat_override = False
        if self.selected_pose == CatPose.AUTO:
            self.auto_timer.start(AUTO_POSE_MS)
            self._advance_auto_pose()
        else:
            self._apply_pose(self.selected_pose)

    def _move_to_start_position(self) -> None:
        saved = self.agent_core.memory_store.all_memories().get("window_position")
        if isinstance(saved, str):
            try:
                x_text, y_text = saved.split(",", 1)
                self.move(self._clamp_position(QPoint(int(x_text), int(y_text))))
                self.target = self.pos()
                return
            except ValueError:
                pass

        screen = self._screen_rect()
        x = screen.right() - self.width() - 80
        y = screen.bottom() - self.height() - 80
        self.move(max(screen.left(), x), max(screen.top(), y))
        self.target = self.pos()

    def _screen_rect(self) -> QRect:
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        return screen.availableGeometry()

    def _choose_next_target(self) -> None:
        screen = self._screen_rect()
        current = self.pos()

        distance = random.randint(100, 280)
        if random.random() < 0.25:
            self.direction *= -1
        x = current.x() + distance * self.direction
        y = current.y() + random.randint(-30, 30)

        if x < screen.left() or x > screen.right() - self.width():
            self.direction *= -1
            x = current.x() + distance * self.direction

        x = max(screen.left(), min(screen.right() - self.width(), x))
        y = max(screen.top(), min(screen.bottom() - self.height(), y))
        self.target = QPoint(x, y)

    def _move_tick(self) -> None:
        if self.paused or self.dragging or self.chat_override:
            return
        if not POSE_SPECS[self.current_pose].moves:
            return

        current = self.pos()
        delta = self.target - current

        if abs(delta.x()) <= STEP_PIXELS and abs(delta.y()) <= STEP_PIXELS:
            self.move(self.target)
            self._choose_next_target()
            return

        self.move(current + QPoint(self._step(delta.x()), self._step(delta.y())))

    @staticmethod
    def _step(value: int) -> int:
        if value == 0:
            return 0
        return STEP_PIXELS if value > 0 else -STEP_PIXELS

    def _sync_window_size(self) -> None:
        if self.bubble_visible:
            self.bubble.show()
            self.setFixedSize(PET_SIZE + BUBBLE_GAP + BUBBLE_WIDTH, BUBBLE_HEIGHT)
        else:
            self.bubble.hide()
            self.setFixedSize(PET_SIZE, PET_SIZE)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._start_drag(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self.dragging:
            self._drag_to(event.globalPosition().toPoint())
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.target = self.pos()
            self._save_window_position()
            event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._toggle_bubble()
            event.accept()

    def eventFilter(self, watched, event) -> bool:
        if watched not in (self.cat_label, self.bubble):
            return super().eventFilter(watched, event)

        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._start_drag(event.globalPosition().toPoint())
            return True
        if event.type() == QEvent.MouseMove and self.dragging:
            self._drag_to(event.globalPosition().toPoint())
            return True
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            self.dragging = False
            self.target = self.pos()
            self._save_window_position()
            return True
        if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
            self._toggle_bubble()
            return True

        return super().eventFilter(watched, event)

    def _start_drag(self, global_pos: QPoint) -> None:
        self.dragging = True
        self.drag_offset = global_pos - self.frameGeometry().topLeft()

    def _drag_to(self, global_pos: QPoint) -> None:
        self.move(global_pos - self.drag_offset)
        self.target = self.pos()

    def _open_menu(self, _pos: QPoint) -> None:
        menu = QMenu(self)
        bubble_action = QAction("Hide Bubble" if self.bubble_visible else "Show Bubble", self)
        pause_action = QAction("Resume Movement" if self.paused else "Pause Movement", self)
        tasks_action = QAction("Show Tasks", self)
        clear_completed_action = QAction("Clear Completed", self)
        exit_action = QAction("Exit", self)

        bubble_action.triggered.connect(self._toggle_bubble)
        pause_action.triggered.connect(self._toggle_pause)
        tasks_action.triggered.connect(self._show_tasks)
        clear_completed_action.triggered.connect(self._clear_completed_tasks)
        exit_action.triggered.connect(QApplication.quit)

        menu.addAction(bubble_action)
        menu.addAction(pause_action)
        menu.addAction(tasks_action)
        menu.addAction(clear_completed_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        menu.exec(QCursor.pos())

    def _toggle_bubble(self) -> None:
        old_top_left = self.pos()
        self.bubble_visible = not self.bubble_visible
        self._sync_window_size()
        self.move(self._clamp_position(old_top_left))

    def _toggle_pause(self) -> None:
        self.paused = not self.paused
        if not self.paused and POSE_SPECS[self.current_pose].moves:
            self._choose_next_target()

    def _show_tasks(self) -> None:
        if not self.bubble_visible:
            self._toggle_bubble()
        self._refresh_tasks()
        self.tabs.setCurrentWidget(self.tasks_panel)

    def _clear_completed_tasks(self) -> None:
        self.agent_core.reminder_store.clear_completed()
        self._refresh_tasks()

    def _refresh_tasks(self) -> None:
        if hasattr(self, "tasks_panel"):
            self.tasks_panel.refresh()

    def _check_due_reminders(self) -> None:
        due = self.agent_core.reminder_store.due_reminders(datetime.now())
        if not due:
            return

        if not self.bubble_visible:
            self._toggle_bubble()
        self.tabs.setCurrentWidget(self.chat_panel)
        self.chat_override = True
        self.chat_restore_timer.stop()
        self._apply_pose(CatPose.EAT)

        for item in due:
            self.chat_panel.append_system_message(self.agent_core.reminder_due_message(item))
        self._refresh_tasks()
        self._schedule_chat_restore()

    def _send_proactive_care(self) -> None:
        idle_seconds = (datetime.now() - self.last_interaction_at).total_seconds()
        if idle_seconds < PROACTIVE_CARE_MS / 1000:
            return

        if not self.bubble_visible:
            self._toggle_bubble()
        self.tabs.setCurrentWidget(self.chat_panel)
        self.chat_panel.append_system_message(self.agent_core.proactive_message())
        self.chat_override = True
        self._apply_pose(CatPose.SLEEP)
        self._schedule_chat_restore()

    def _mark_interaction(self) -> None:
        self.last_interaction_at = datetime.now()

    def _save_window_position(self) -> None:
        pos = self.pos()
        self.agent_core.memory_store.remember("window_position", f"{pos.x()},{pos.y()}")

    def _clamp_position(self, pos: QPoint) -> QPoint:
        screen = self._screen_rect()
        x = max(screen.left(), min(screen.right() - self.width(), pos.x()))
        y = max(screen.top(), min(screen.bottom() - self.height(), pos.y()))
        return QPoint(x, y)
