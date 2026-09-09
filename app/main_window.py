"""Main application window: top bar, stage (visualizer), bottom bar, sidebar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget,
)

from .config import Config
from .audio_engine import AudioEngine
from .visualizer_widget import VisualizerWidget
from .sidebar import Sidebar
from .styles import DARK_QSS, LIGHT_QSS


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TahaAi Visualizer — Python Edition")
        self.resize(1440, 900)
        self.setMinimumSize(1000, 650)

        self.config = Config()
        self.audio = AudioEngine()

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- sidebar (created first so it can wire into the visualizer) ---
        self.visualizer = VisualizerWidget(self.config, self.audio)
        self.sidebar = Sidebar(self.config, self.audio, self.visualizer)
        self.sidebar.request_toggle_collapse.connect(self.toggle_sidebar)
        root.addWidget(self.sidebar)

        # ---- floating reopen button, shown only while collapsed ----------
        self.open_sidebar_btn = QPushButton("☰", central)
        self.open_sidebar_btn.setObjectName("IconBtn")
        self.open_sidebar_btn.setFixedSize(34, 34)
        self.open_sidebar_btn.move(14, 14)
        self.open_sidebar_btn.hide()
        self.open_sidebar_btn.clicked.connect(self.toggle_sidebar)
        self.open_sidebar_btn.raise_()

        # ---- main column: top bar / stage / bottom bar --------------------
        main_col = QWidget()
        main_layout = QVBoxLayout(main_col)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        root.addWidget(main_col, 1)

        self.top_bar = self._build_top_bar()
        main_layout.addWidget(self.top_bar)

        self.stage = QFrame()
        self.stage.setObjectName("Stage")
        stage_layout = QVBoxLayout(self.stage)
        stage_layout.setContentsMargins(15, 15, 15, 15)

        self.visual_frame = QFrame()
        self.visual_frame.setObjectName("VisualFrame")
        visual_layout = QVBoxLayout(self.visual_frame)
        visual_layout.setContentsMargins(0, 0, 0, 0)
        visual_layout.addWidget(self.visualizer)
        stage_layout.addWidget(self.visual_frame)

        self.fullscreen_btn = QPushButton("Fullscreen", self.visual_frame)
        self.fullscreen_btn.setObjectName("Ghost")
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.fullscreen_btn.move(12, 12)
        self.fullscreen_btn.raise_()

        main_layout.addWidget(self.stage, 1)
        main_layout.addWidget(self._build_bottom_bar())

        self.main_col = main_col
        self._is_fullscreen_ui = False
        self.apply_theme(self.config.theme)

    # ------------------------------------------------------------------ #
    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(62)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(17, 0, 17, 0)

        title_col = QVBoxLayout()
        title = QLabel("LIVE VISUALIZER")
        title.setObjectName("TitleLabel")
        self.source_label = QLabel("DEMO MODE")
        self.source_label.setObjectName("SmallMuted")
        title_col.addWidget(title)
        title_col.addWidget(self.source_label)
        layout.addLayout(title_col)
        layout.addStretch(1)

        status_row = QHBoxLayout()
        self.status_dot = QLabel()
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setProperty("live", True)
        self.status_dot.setFixedSize(10, 10)
        self.status_text = QLabel("DEMO")
        self.status_text.setObjectName("SmallMuted")
        status_row.addWidget(self.status_dot)
        status_row.addWidget(self.status_text)
        layout.addLayout(status_row)
        return bar

    def _build_bottom_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("BottomBar")
        bar.setFixedHeight(46)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(17, 0, 17, 0)
        layout.addStretch(1)
        tiny = QLabel("Real FFT • 2048 bins • adjustable FPS")
        tiny.setObjectName("SmallMuted")
        layout.addWidget(tiny)
        return bar

    # ------------------------------------------------------------------ #
    def apply_theme(self, theme: str) -> None:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        app.setStyleSheet(DARK_QSS if theme == "dark" else LIGHT_QSS)

    # ------------------------------------------------------------------ #
    def toggle_sidebar(self) -> None:
        collapsed = self.sidebar.isVisible()
        self.sidebar.setVisible(not collapsed)
        self.open_sidebar_btn.setVisible(collapsed)

    # ------------------------------------------------------------------ #
    def toggle_fullscreen(self) -> None:
        self.set_ui_fullscreen(not self._is_fullscreen_ui)

    def set_ui_fullscreen(self, on: bool) -> None:
        self._is_fullscreen_ui = on

        if on:
            self._sidebar_was_visible = self.sidebar.isVisible()
            self.sidebar.setVisible(False)
            self.open_sidebar_btn.setVisible(False)
        else:
            was_visible = getattr(self, "_sidebar_was_visible", True)
            self.sidebar.setVisible(was_visible)
            self.open_sidebar_btn.setVisible(not was_visible)

        self.top_bar.setVisible(not on)
        self.fullscreen_btn.setVisible(not on)

        margins = (0, 0, 0, 0) if on else (15, 15, 15, 15)
        self.stage.layout().setContentsMargins(*margins)

        self.visual_frame.setProperty("fullscreen", "true" if on else "false")
        self.visual_frame.style().unpolish(self.visual_frame)
        self.visual_frame.style().polish(self.visual_frame)

        # bottom bar is main_layout's 3rd item (top bar, stage, bottom bar)
        self.main_col.layout().itemAt(2).widget().setVisible(not on)

        if on:
            self.showFullScreen()
        else:
            self.showNormal()
        self.fullscreen_btn.setText("Exit fullscreen" if on else "Fullscreen")

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key_Escape and self._is_fullscreen_ui:
            self.set_ui_fullscreen(False)
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.open_sidebar_btn.move(14, 14)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.audio.stop()
        super().closeEvent(event)
