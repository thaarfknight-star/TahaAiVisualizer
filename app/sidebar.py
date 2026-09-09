"""Left control panel: audio source, visual style and full customization."""
from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QSlider, QVBoxLayout, QWidget,
)

from .config import Config, PALETTE, MODES, BACKGROUNDS, MIRROR_MODES, PRESETS


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
        self.setFixedWidth(360)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        self.col = QVBoxLayout(content)
        self.col.setContentsMargins(18, 18, 18, 18)
        self.col.setSpacing(4)

        self._build_header()
        self._build_spotify_section()
        self._build_audio_section()
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
        choose_btn = QPushButton("Choose audio")
        choose_btn.setObjectName("Primary")
        choose_btn.clicked.connect(self._choose_audio_file)
        sys_btn = QPushButton("System audio")
        sys_btn.clicked.connect(self._start_system_audio)
        row.addWidget(choose_btn)
        row.addWidget(sys_btn)
        self.col.addLayout(row)

        self.audio_info = QLabel("Demo فعال است. منبع صوتی متصل نیست.")
        self.audio_info.setObjectName("Box")
        self.audio_info.setWordWrap(True)
        self.col.addWidget(self.audio_info)

        stop_btn = QPushButton("قطع صدا و بازگشت به Demo")
        stop_btn.clicked.connect(self._stop_audio)
        self.col.addWidget(stop_btn)

    def _choose_audio_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل صوتی", "",
            "Audio files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac)"
        )
        if not path:
            return
        ok = self.audio.play_file(path)
        if ok:
            self.config.demo_mode = False
            self.audio_info.setText(f"در حال پخش: {self.audio.file_name}")
        else:
            self.audio_info.setText(self.audio.error or "خطا در پخش فایل.")

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
        self.col.addWidget(_label("Accent color", ))
        colors_row = QGridLayout()
        colors_row.setSpacing(5)
        self._color_buttons = []
        for i, color in enumerate(PALETTE):
            btn = QPushButton()
            btn.setFixedHeight(27)
            btn.setStyleSheet(f"background:{color};border-radius:6px;border:2px solid transparent;")
            btn.clicked.connect(lambda _=False, c=color: self._set_accent(c))
            colors_row.addWidget(btn, 0, i)
            self._color_buttons.append((btn, color))
        self.col.addLayout(colors_row)

        custom_btn = QPushButton("انتخاب رنگ دلخواه…")
        custom_btn.clicked.connect(self._pick_custom_color)
        self.col.addWidget(custom_btn)

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
            btn.clicked.connect(lambda _=False, n=name: self._apply_preset(n))
            grid.addWidget(btn, i // 3, i % 3)
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
