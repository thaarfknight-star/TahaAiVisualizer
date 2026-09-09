"""Left control panel: audio source, visual style and full customization."""
from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QScrollArea, QSizePolicy, QSlider, QVBoxLayout, QWidget,
)

from .config import Config, PALETTE, MODES, BACKGROUNDS, MIRROR_MODES, PRESETS, GRADIENT_PRESETS


def _hline() -> QFrame:
    line = QFrame()
    line.setObjectName("Divider")
    line.setFixedHeight(1)
    return line


def _label(text: str, object_name: str = "SectionLabel") -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName(object_name)
    return lbl


class SliderRow(QWidget):
    """A labeled slider with a live numeric readout, like the web version."""

    changed = Signal(float)

    def __init__(self, title: str, minimum: float, maximum: float, step: float,
                 value: float, decimals: int = 2, parent=None):
        super().__init__(parent)
        self._scale = int(round(1 / step)) if step < 1 else 1
        self._decimals = decimals

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.addWidget(_label(title))

        row = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(int(minimum * self._scale))
        self.slider.setMaximum(int(maximum * self._scale))
        self.slider.setValue(int(value * self._scale))
        self.readout = QLabel()
        self.readout.setFixedWidth(46)
        self.readout.setAlignment(Qt.AlignCenter)
        self.readout.setObjectName("SmallMuted")

        row.addWidget(self.slider)
        row.addWidget(self.readout)
        layout.addLayout(row)

        self.slider.valueChanged.connect(self._on_change)
        self._on_change(self.slider.value())

    def _on_change(self, raw: int) -> None:
        value = raw / self._scale
        self.readout.setText(f"{value:.{self._decimals}f}")
        self.changed.emit(value)

    def set_value(self, value: float) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(int(value * self._scale))
        self.slider.blockSignals(False)
        self._on_change(self.slider.value())


class Sidebar(QWidget):
    request_toggle_collapse = Signal()

    def __init__(self, config: Config, audio, visualizer, parent=None):
        super().__init__(parent)
        self.config = config
        self.audio = audio
        self.visualizer = visualizer
        self.setObjectName("Sidebar")
        self.setFixedWidth(400)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        self.col = QVBoxLayout(content)
        self.col.setContentsMargins(18, 18, 18, 18)
        self.col.setSpacing(4)

        self._build_header()
        self._build_spotify_section()
        self._build_audio_section()
        self._build_playlist_section()
        self.col.addWidget(_hline())
        self._build_style_section()
        self._build_customization_section()
        self._build_toggles_section()
        self._build_presets_section()
        self._build_io_section()
        self._build_hint()
        self.col.addStretch(1)

    # ------------------------------------------------------------------ #
    def _build_header(self) -> None:
        row = QHBoxLayout()
        brand = QLabel("TAHAAI / VISUALIZER")
        brand.setObjectName("Brand")
        row.addWidget(brand)
        row.addStretch(1)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("IconBtn")
        close_btn.setToolTip("بستن منو")
        close_btn.clicked.connect(self.request_toggle_collapse.emit)
        row.addWidget(close_btn)
        self.col.addLayout(row)

        desc = QLabel(
            "ویژولایزر دسکتاپ مستقل. پیش‌نمایش بلافاصله اجرا می‌شود؛ برای هماهنگی "
            "واقعی با صدا، فایل صوتی یا خروجی صدای سیستم را وصل کنید."
        )
        desc.setObjectName("Desc")
        desc.setWordWrap(True)
        self.col.addWidget(desc)

    def _build_spotify_section(self) -> None:
        self.col.addWidget(_label("Spotify track"))
        self.spotify_input = QLineEdit()
        self.spotify_input.setPlaceholderText("https://open.spotify.com/track/...")
        self.col.addWidget(self.spotify_input)

        row = QHBoxLayout()
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self._open_spotify)
        row.addWidget(open_btn)
        self.col.addLayout(row)

        self.spotify_info = QLabel("لینک ترک اسپاتیفای را وارد کنید.")
        self.spotify_info.setObjectName("Box")
        self.spotify_info.setWordWrap(True)
        self.col.addWidget(self.spotify_info)

    def _open_spotify(self) -> None:
        url = self.spotify_input.text().strip()
        if url:
            webbrowser.open(url)
            self.spotify_info.setText(
                "اسپاتیفای باز شد. سپس از بخش «Audio source» گزینه System audio را بزنید."
            )

    def _build_audio_section(self) -> None:
        self.col.addWidget(_label("Audio source"))
        row = QHBoxLayout()
        sys_btn = QPushButton("System audio")
        sys_btn.setObjectName("Primary")
        sys_btn.clicked.connect(self._start_system_audio)
        row.addWidget(sys_btn)
        self.col.addLayout(row)

        self.audio_info = QLabel("Demo فعال است. منبع صوتی متصل نیست.")
        self.audio_info.setObjectName("Box")
        self.audio_info.setWordWrap(True)
        self.col.addWidget(self.audio_info)

        stop_btn = QPushButton("قطع صدا و بازگشت به Demo")
        stop_btn.clicked.connect(self._stop_audio)
        self.col.addWidget(stop_btn)

    def _start_system_audio(self) -> None:
        ok = self.audio.start_system_audio()
        if ok:
            self.config.demo_mode = False
            self.audio_info.setText("در حال دریافت صدای سیستم (System audio loopback).")
        else:
            self.audio_info.setText(self.audio.error or "خطا در دریافت صدای سیستم.")

    def _stop_audio(self) -> None:
        self.audio.stop()
        self.config.demo_mode = True
        self.audio_info.setText("Demo فعال است. منبع صوتی متصل نیست.")
        self._refresh_playlist_ui()

    # ------------------------------------------------------------------ #
    def _build_playlist_section(self) -> None:
        self.col.addWidget(_hline())
        self.col.addWidget(_label("Playlist"))

        add_btn = QPushButton("افزودن آهنگ (یک یا چند فایل)")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_tracks)
        self.col.addWidget(add_btn)

        self.playlist_widget = QListWidget()
        self.playlist_widget.setFixedHeight(140)
        self.playlist_widget.itemDoubleClicked.connect(self._play_selected_track)
        self.col.addWidget(self.playlist_widget)

        controls = QHBoxLayout()
        self.prev_btn = QPushButton("⏮")
        self.play_pause_btn = QPushButton("⏯")
        self.next_btn = QPushButton("⏭")
        for b in (self.prev_btn, self.play_pause_btn, self.next_btn):
            b.setObjectName("IconBtn")
            b.setFixedWidth(46)
        self.prev_btn.clicked.connect(self._on_prev)
        self.play_pause_btn.clicked.connect(self._on_play_pause)
        self.next_btn.clicked.connect(self._on_next)
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_pause_btn)
        controls.addWidget(self.next_btn)
        controls.addStretch(1)
        self.col.addLayout(controls)

        manage_row = QGridLayout()
        manage_row.setSpacing(6)
        remove_btn = QPushButton("حذف انتخاب‌شده")
        remove_btn.clicked.connect(self._remove_selected_track)
        clear_btn = QPushButton("پاک کردن لیست")
        clear_btn.clicked.connect(self._clear_playlist)
        manage_row.addWidget(remove_btn, 0, 0)
        manage_row.addWidget(clear_btn, 0, 1)
        manage_row.setColumnStretch(0, 1)
        manage_row.setColumnStretch(1, 1)
        self.col.addLayout(manage_row)

        toggles_row = QHBoxLayout()
        self.repeat_check = QCheckBox("تکرار پلی‌لیست")
        self.repeat_check.setChecked(self.audio.repeat_all)
        self.repeat_check.toggled.connect(lambda v: setattr(self.audio, "repeat_all", v))
        self.shuffle_check = QCheckBox("پخش تصادفی")
        self.shuffle_check.setChecked(self.audio.shuffle)
        self.shuffle_check.toggled.connect(lambda v: setattr(self.audio, "shuffle", v))
        toggles_row.addWidget(self.repeat_check)
        toggles_row.addWidget(self.shuffle_check)
        self.col.addLayout(toggles_row)

        # Polls for natural track-end (to auto-advance) and keeps the
        # playlist UI (bold current item, play/pause icon, status text) fresh.
        self._playlist_timer = QTimer(self)
        self._playlist_timer.timeout.connect(self._poll_playlist)
        self._playlist_timer.start(250)

    def _add_tracks(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "انتخاب یک یا چند فایل آهنگ", "",
            "Audio files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac)"
        )
        if not paths:
            return
        for path in paths:
            name = path.replace("\\", "/").split("/")[-1]
            self.playlist_widget.addItem(QListWidgetItem(name))
        ok = self.audio.add_to_playlist(paths)
        if ok:
            self.config.demo_mode = False
            self.audio_info.setText(f"در حال پخش: {self.audio.file_name}")
        else:
            self.audio_info.setText(self.audio.error or "خطا در افزودن فایل.")
        self._refresh_playlist_ui()

    def _play_selected_track(self, item: QListWidgetItem) -> None:
        index = self.playlist_widget.row(item)
        if self.audio.play_index(index):
            self.config.demo_mode = False
        self._refresh_playlist_ui()

    def _on_prev(self) -> None:
        self.audio.prev_track()
        self._refresh_playlist_ui()

    def _on_next(self) -> None:
        if not self.audio.next_track():
            self.audio_info.setText("پایان پلی‌لیست.")
        self._refresh_playlist_ui()

    def _on_play_pause(self) -> None:
        self.audio.play_pause_toggle()
        if self.audio.mode == "file":
            self.config.demo_mode = False
        self._refresh_playlist_ui()

    def _remove_selected_track(self) -> None:
        row = self.playlist_widget.currentRow()
        if row < 0:
            return
        self.audio.remove_from_playlist(row)
        self.playlist_widget.takeItem(row)
        self._refresh_playlist_ui()

    def _clear_playlist(self) -> None:
        self.audio.clear_playlist()
        self.playlist_widget.clear()
        self.config.demo_mode = True
        self.audio_info.setText("Demo فعال است. منبع صوتی متصل نیست.")

    def _poll_playlist(self) -> None:
        if self.audio.poll_track_finished():
            self._refresh_playlist_ui()
        if self.audio.mode == "file" and self.audio.playlist:
            state = "مکث" if self.audio._paused else "پخش"
            pos = f"{self.audio.playlist_index + 1}/{len(self.audio.playlist)}"
            self.audio_info.setText(f"{state}: {self.audio.file_name} ({pos})")

    def _refresh_playlist_ui(self) -> None:
        for i in range(self.playlist_widget.count()):
            item = self.playlist_widget.item(i)
            font = item.font()
            font.setBold(self.audio.mode == "file" and i == self.audio.playlist_index)
            item.setFont(font)
        playing = self.audio.mode == "file" and not self.audio._paused
        self.play_pause_btn.setText("⏸" if playing else "⏯")

    # ------------------------------------------------------------------ #
    def _build_style_section(self) -> None:
        self.col.addWidget(_label("Visualizer style"))
        self.mode_combo = QComboBox()
        for value, label in MODES:
            self.mode_combo.addItem(label, value)
        self.mode_combo.setCurrentIndex([m[0] for m in MODES].index(self.config.mode))
        self.mode_combo.currentIndexChanged.connect(
            lambda i: setattr(self.config, "mode", self.mode_combo.itemData(i))
        )
        self.col.addWidget(self.mode_combo)

    def _build_customization_section(self) -> None:
        self.col.addWidget(_label("Color mode"))
        self.colormode_combo = QComboBox()
        self.colormode_combo.addItem("تک‌رنگ (Solid)", "solid")
        self.colormode_combo.addItem("گرادیان (Gradient)", "gradient")
        self.colormode_combo.setCurrentIndex(0 if self.config.color_mode == "solid" else 1)
        self.colormode_combo.currentIndexChanged.connect(self._on_color_mode_changed)
        self.col.addWidget(self.colormode_combo)

        self.col.addWidget(_label("Accent color", ))
        colors_row = QGridLayout()
        colors_row.setSpacing(5)
        cols = 4
        self._color_buttons = []
        for i, color in enumerate(PALETTE):
            btn = QPushButton()
            btn.setFixedHeight(27)
            btn.setMinimumWidth(0)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet(f"background:{color};border-radius:6px;border:2px solid transparent;")
            btn.clicked.connect(lambda _=False, c=color: self._set_accent(c))
            colors_row.addWidget(btn, i // cols, i % cols)
            self._color_buttons.append((btn, color))
        for c in range(cols):
            colors_row.setColumnStretch(c, 1)
        self.col.addLayout(colors_row)

        custom_btn = QPushButton("انتخاب رنگ دلخواه…")
        custom_btn.clicked.connect(self._pick_custom_color)
        self.col.addWidget(custom_btn)
        self.solid_widgets = [custom_btn]

        # ---- gradient editor ------------------------------------------- #
        self.gradient_box = QWidget()
        grad_col = QVBoxLayout(self.gradient_box)
        grad_col.setContentsMargins(0, 6, 0, 0)
        grad_col.setSpacing(6)

        grad_col.addWidget(_label("Gradient presets"))
        self.gradient_preset_combo = QComboBox()
        for name, colors in GRADIENT_PRESETS:
            self.gradient_preset_combo.addItem(name, colors)
        self.gradient_preset_combo.currentIndexChanged.connect(self._apply_gradient_preset)
        grad_col.addWidget(self.gradient_preset_combo)

        grad_col.addWidget(_label("Gradient stops"))
        self.gradient_stops_layout = QGridLayout()
        self.gradient_stops_layout.setSpacing(5)
        grad_col.addLayout(self.gradient_stops_layout)

        stop_btns = QHBoxLayout()
        add_stop_btn = QPushButton("+ افزودن رنگ")
        add_stop_btn.clicked.connect(self._add_gradient_stop)
        remove_stop_btn = QPushButton("- حذف آخرین")
        remove_stop_btn.clicked.connect(self._remove_gradient_stop)
        stop_btns.addWidget(add_stop_btn)
        stop_btns.addWidget(remove_stop_btn)
        grad_col.addLayout(stop_btns)

        self.col.addWidget(self.gradient_box)
        self._rebuild_gradient_stops()
        self._update_color_mode_visibility()

        self.col.addWidget(_label("Background"))
        self.bg_combo = QComboBox()
        for value, label in BACKGROUNDS:
            self.bg_combo.addItem(label, value)
        self.bg_combo.setCurrentIndex([b[0] for b in BACKGROUNDS].index(self.config.background))
        self.bg_combo.currentIndexChanged.connect(self._on_bg_changed)
        self.col.addWidget(self.bg_combo)

        self.bg_image_btn = QPushButton("انتخاب تصویر پس‌زمینه…")
        self.bg_image_btn.clicked.connect(self._choose_bg_image)
        self.bg_image_btn.setVisible(self.config.background == "image")
        self.col.addWidget(self.bg_image_btn)

        self.col.addWidget(_label("Mirror mode"))
        self.mirror_combo = QComboBox()
        for value, label in MIRROR_MODES:
            self.mirror_combo.addItem(label, value)
        self.mirror_combo.setCurrentIndex([m[0] for m in MIRROR_MODES].index(self.config.mirror))
        self.mirror_combo.currentIndexChanged.connect(
            lambda i: setattr(self.config, "mirror", self.mirror_combo.itemData(i))
        )
        self.col.addWidget(self.mirror_combo)

        sliders = [
            ("Sensitivity", 0.2, 3.0, 0.05, self.config.sensitivity, "sensitivity", 2),
            ("Smoothing", 0.05, 0.95, 0.01, self.config.smoothing, "smoothing", 2),
            ("Detail count", 16, 180, 4, self.config.count, "count", 0),
            ("Thickness", 1, 12, 0.5, self.config.thickness, "thickness", 1),
            ("Opacity", 0.05, 1.0, 0.05, self.config.opacity, "opacity", 2),
            ("Glow", 0, 50, 1, self.config.glow, "glow", 0),
        ]
        self._sliders = {}
        for title, lo, hi, step, val, attr, decimals in sliders:
            row = SliderRow(title, lo, hi, step, val, decimals)
            row.changed.connect(lambda v, a=attr: setattr(self.config, a, v))
            self.col.addWidget(row)
            self._sliders[attr] = row

    def _set_accent(self, color: str) -> None:
        self.config.accent = color
        for btn, c in self._color_buttons:
            border = "2px solid #fff" if c == color else "2px solid transparent"
            btn.setStyleSheet(f"background:{c};border-radius:6px;border:{border};")

    def _pick_custom_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.config.accent), self, "انتخاب رنگ")
        if color.isValid():
            self._set_accent(color.name())

    # ---- gradient / color-mode helpers -------------------------------- #
    def _on_color_mode_changed(self, index: int) -> None:
        self.config.color_mode = self.colormode_combo.itemData(index)
        self._update_color_mode_visibility()

    def _update_color_mode_visibility(self) -> None:
        is_gradient = self.config.color_mode == "gradient"
        self.gradient_box.setVisible(is_gradient)
        for w in self.solid_widgets:
            w.setVisible(not is_gradient)
        for btn, _c in self._color_buttons:
            btn.setVisible(not is_gradient)

    def _rebuild_gradient_stops(self) -> None:
        while self.gradient_stops_layout.count():
            item = self.gradient_stops_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        cols = 4
        for i, color in enumerate(self.config.gradient_colors):
            btn = QPushButton()
            btn.setFixedHeight(27)
            btn.setMinimumWidth(0)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet(f"background:{color};border-radius:6px;border:2px solid #fff;")
            btn.setToolTip(f"استاپ {i + 1} — کلیک برای تغییر رنگ")
            btn.clicked.connect(lambda _=False, idx=i: self._pick_gradient_stop_color(idx))
            self.gradient_stops_layout.addWidget(btn, i // cols, i % cols)
        for c in range(cols):
            self.gradient_stops_layout.setColumnStretch(c, 1)

    def _pick_gradient_stop_color(self, idx: int) -> None:
        current = self.config.gradient_colors[idx]
        color = QColorDialog.getColor(QColor(current), self, "انتخاب رنگ گرادیان")
        if color.isValid():
            self.config.gradient_colors[idx] = color.name()
            self._rebuild_gradient_stops()

    def _add_gradient_stop(self) -> None:
        if len(self.config.gradient_colors) >= 6:
            return
        self.config.gradient_colors.append(self.config.accent)
        self._rebuild_gradient_stops()

    def _remove_gradient_stop(self) -> None:
        if len(self.config.gradient_colors) <= 2:
            return
        self.config.gradient_colors.pop()
        self._rebuild_gradient_stops()

    def _apply_gradient_preset(self, index: int) -> None:
        colors = self.gradient_preset_combo.itemData(index)
        if not colors:
            return
        self.config.gradient_colors = list(colors)
        self._rebuild_gradient_stops()

    def _on_bg_changed(self, index: int) -> None:
        value = self.bg_combo.itemData(index)
        self.config.background = value
        self.bg_image_btn.setVisible(value == "image")

    def _choose_bg_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب تصویر پس‌زمینه", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.config.background_image = path
            self.visualizer.set_background_image(path)

    # ------------------------------------------------------------------ #
    def _build_toggles_section(self) -> None:
        self.bass_check = QCheckBox("Bass boost")
        self.bass_check.setChecked(self.config.bass_boost)
        self.bass_check.toggled.connect(lambda v: setattr(self.config, "bass_boost", v))
        self.col.addWidget(self.bass_check)

        self.trails_check = QCheckBox("Motion trails")
        self.trails_check.setChecked(self.config.trails)
        self.trails_check.toggled.connect(lambda v: setattr(self.config, "trails", v))
        self.col.addWidget(self.trails_check)

        self.demo_check = QCheckBox("Demo when no audio")
        self.demo_check.setChecked(self.config.demo_mode)
        self.demo_check.toggled.connect(lambda v: setattr(self.config, "demo_mode", v))
        self.col.addWidget(self.demo_check)

        self.ontop_check = QCheckBox("Always on top")
        self.ontop_check.setChecked(self.config.always_on_top)
        self.ontop_check.toggled.connect(self._toggle_always_on_top)
        self.col.addWidget(self.ontop_check)

        self.col.addWidget(_label("Frame rate"))
        self.fps_combo = QComboBox()
        for fps in (24, 30, 60, 120):
            self.fps_combo.addItem(f"{fps} FPS", fps)
        self.fps_combo.setCurrentIndex([24, 30, 60, 120].index(self.config.fps)
                                        if self.config.fps in (24, 30, 60, 120) else 2)
        self.fps_combo.currentIndexChanged.connect(
            lambda i: (setattr(self.config, "fps", self.fps_combo.itemData(i)),
                       self.visualizer.apply_fps(self.config.fps))
        )
        self.col.addWidget(self.fps_combo)

        self.col.addWidget(_label("Theme"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("تیره (Dark)", "dark")
        self.theme_combo.addItem("روشن (Light)", "light")
        self.theme_combo.setCurrentIndex(0 if self.config.theme == "dark" else 1)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.col.addWidget(self.theme_combo)

    def _toggle_always_on_top(self, checked: bool) -> None:
        self.config.always_on_top = checked
        window = self.window()
        flags = window.windowFlags()
        if checked:
            window.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            window.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        window.show()

    def _on_theme_changed(self, index: int) -> None:
        self.config.theme = self.theme_combo.itemData(index)
        main_window = self.window()
        if hasattr(main_window, "apply_theme"):
            main_window.apply_theme(self.config.theme)

    # ------------------------------------------------------------------ #
    def _build_presets_section(self) -> None:
        self.col.addWidget(_hline())
        self.col.addWidget(_label("Presets"))
        grid = QGridLayout()
        grid.setSpacing(6)
        for i, name in enumerate(PRESETS):
            btn = QPushButton(name)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _=False, n=name: self._apply_preset(n))
            grid.addWidget(btn, i // 2, i % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.col.addLayout(grid)

        reset_btn = QPushButton("Reset customization")
        reset_btn.clicked.connect(self._reset)
        self.col.addWidget(reset_btn)

    def _apply_preset(self, name: str) -> None:
        self.config.apply_preset(name)
        self.sync_from_config()

    def _reset(self) -> None:
        fresh = Config()
        fresh.mode = self.config.mode
        self.config.__dict__.update(fresh.__dict__)
        self.sync_from_config()

    # ------------------------------------------------------------------ #
    def _build_io_section(self) -> None:
        self.col.addWidget(_hline())
        self.col.addWidget(_label("Save / load settings"))
        row = QHBoxLayout()
        save_btn = QPushButton("ذخیره تنظیمات")
        save_btn.clicked.connect(self._save_settings)
        load_btn = QPushButton("بارگذاری تنظیمات")
        load_btn.clicked.connect(self._load_settings)
        row.addWidget(save_btn)
        row.addWidget(load_btn)
        self.col.addLayout(row)

    def _save_settings(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره تنظیمات", "preset.json", "JSON (*.json)")
        if path:
            self.config.save(path)

    def _load_settings(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "بارگذاری تنظیمات", "", "JSON (*.json)")
        if not path:
            return
        loaded = Config.load(path)
        self.config.__dict__.update(loaded.__dict__)
        self.sync_from_config()

    # ------------------------------------------------------------------ #
    def _build_hint(self) -> None:
        hint = QLabel(
            "OBS / Meld: از Window Capture استفاده کنید. برای اسپاتیفای، ابتدا اسپاتیفای "
            "را باز کنید سپس System audio را انتخاب کرده و پنجره اسپاتیفای را برگزینید."
        )
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        self.col.addWidget(hint)

    # ------------------------------------------------------------------ #
    def sync_from_config(self) -> None:
        """Reflect the current Config values back onto every control."""
        cfg = self.config
        self.mode_combo.setCurrentIndex([m[0] for m in MODES].index(cfg.mode))
        self.bg_combo.setCurrentIndex([b[0] for b in BACKGROUNDS].index(cfg.background))
        self.bg_image_btn.setVisible(cfg.background == "image")
        self.mirror_combo.setCurrentIndex([m[0] for m in MIRROR_MODES].index(cfg.mirror))
        self._set_accent(cfg.accent)
        self.colormode_combo.setCurrentIndex(0 if cfg.color_mode == "solid" else 1)
        self._rebuild_gradient_stops()
        self._update_color_mode_visibility()

        self._sliders["sensitivity"].set_value(cfg.sensitivity)
        self._sliders["smoothing"].set_value(cfg.smoothing)
        self._sliders["count"].set_value(cfg.count)
        self._sliders["thickness"].set_value(cfg.thickness)
        self._sliders["opacity"].set_value(cfg.opacity)
        self._sliders["glow"].set_value(cfg.glow)

        self.bass_check.setChecked(cfg.bass_boost)
        self.trails_check.setChecked(cfg.trails)
        self.demo_check.setChecked(cfg.demo_mode)
        self.ontop_check.setChecked(cfg.always_on_top)

        if cfg.fps in (24, 30, 60, 120):
            self.fps_combo.setCurrentIndex([24, 30, 60, 120].index(cfg.fps))
        self.theme_combo.setCurrentIndex(0 if cfg.theme == "dark" else 1)
