"""Custom-painted visualizer canvas: 9 modes, gradients, particles, images."""
from __future__ import annotations

import math
import random
from typing import Optional

import numpy as np
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPen, QBrush, QPixmap
from PySide6.QtWidgets import QWidget

from .config import Config
from .audio_engine import AudioEngine


class VisualizerWidget(QWidget):
    def __init__(self, config: Config, audio: AudioEngine, parent=None):
        super().__init__(parent)
        self.config = config
        self.audio = audio
        self.phase = 0.0
        self.background_image: Optional[QPixmap] = None
        self._particles = [
            {
                "x": random.random(),
                "y": random.random(),
                "vx": (random.random() - 0.5) * 0.006,
                "vy": (random.random() - 0.5) * 0.006,
            }
            for _ in range(180)
        ]

        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.apply_fps(config.fps)

    # ------------------------------------------------------------------ #
    def apply_fps(self, fps: int) -> None:
        self.timer.start(max(1, int(1000 / max(1, fps))))

    def set_background_image(self, path: str) -> None:
        self.background_image = QPixmap(path) if path else None

    def _tick(self) -> None:
        self.phase += 0.018
        self.audio.compute_frequency_data(self.config.smoothing)
        self.update()

    # ------------------------------------------------------------------ #
    def _audio_value(self, index: float, total: float, freq: Optional[np.ndarray]) -> float:
        cfg = self.config
        if freq is not None and len(freq):
            bin_index = int((index / max(1.0, total)) ** 1.7 * len(freq) * 0.8)
            bin_index = min(max(bin_index, 0), len(freq) - 1)
            v = float(freq[bin_index])
            if cfg.bass_boost and bin_index < len(freq) * 0.12:
                v *= 1.25
            return min(1.0, v * cfg.sensitivity)
        # deterministic demo signal, independent from real audio
        return (
            0.08
            + 0.44 * math.sin(self.phase * 2.1 + index * 0.47) ** 2
            + 0.18 * math.sin(self.phase * 4.2 + index * 0.11) ** 2
        )

    # ------------------------------------------------------------------ #
    def paintEvent(self, event) -> None:  # noqa: N802
        cfg = self.config
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        self._draw_background(p, w, h)
        freq = self.audio.snapshot()

        drawers = {
            "spectrum": self._draw_spectrum,
            "bars": self._draw_bars,
            "wave": self._draw_wave,
            "circle": self._draw_circle,
            "radial": self._draw_radial,
            "particles": self._draw_particles,
            "dots": self._draw_dots,
            "spiral": self._draw_spiral,
            "kaleidoscope": self._draw_kaleidoscope,
        }
        drawers.get(cfg.mode, self._draw_spectrum)(p, w, h, freq)
        p.end()

    # background ---------------------------------------------------------
    def _draw_background(self, p: QPainter, w: int, h: int) -> None:
        cfg = self.config
        if cfg.background == "transparent":
            p.fillRect(0, 0, w, h, Qt.transparent)
            return

        if cfg.background == "image" and self.background_image and not self.background_image.isNull():
            p.drawPixmap(self.rect(), self.background_image)
            p.fillRect(0, 0, w, h, QColor(9, 9, 15, 130))
        else:
            alpha = 60 if cfg.trails else 255
            p.fillRect(0, 0, w, h, QColor(9, 9, 15, alpha))

        if cfg.background == "gradient":
            g = QRadialGradient(w / 2, h / 2, max(w, h) * 0.7)
            c1 = QColor(cfg.accent)
            c1.setAlpha(36)
            g.setColorAt(0.0, c1)
            g.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(0, 0, w, h, QBrush(g))

    # style helpers --------------------------------------------------------
    def _pen(self) -> QPen:
        cfg = self.config
        pen = QPen(QColor(cfg.accent))
        pen.setWidthF(cfg.thickness)
        pen.setCapStyle(Qt.RoundCap)
        return pen

    def _accent(self, alpha: float) -> QColor:
        cfg = self.config
        c = QColor(cfg.accent)
        c.setAlphaF(max(0.0, min(1.0, cfg.opacity * alpha)))
        return c

    # modes ------------------------------------------------------------- #
    def _draw_spectrum(self, p, w, h, freq) -> None:
        cfg = self.config
        n = max(16, int(cfg.count))
        gap = w / n
        p.setPen(Qt.NoPen)
        for i in range(n):
            q = self._audio_value(i, n, freq)
            hh = 5 + q * h * 0.72
            x = i * gap + gap * 0.5
            p.setBrush(self._accent(0.22 + 0.78 * q))
            if cfg.mirror in ("vertical", "both"):
                p.drawRect(QRectF(x - gap * 0.24, h / 2 - hh, gap * 0.48, hh * 2))
            else:
                p.drawRect(QRectF(x - gap * 0.24, h - hh, gap * 0.48, hh))

    def _draw_bars(self, p, w, h, freq) -> None:
        cfg = self.config
        n = max(12, int(cfg.count / 2))
        gap = (w / 2) / n
        p.setPen(Qt.NoPen)
        for i in range(n):
            q = self._audio_value(i, n, freq)
            hh = 5 + q * h * 0.7
            for side in (-1, 1):
                x = w / 2 + side * i * gap
                rx = x - gap * 0.65 if side < 0 else x
                p.setBrush(self._accent(0.28 + 0.72 * q))
                p.drawRect(QRectF(rx, h / 2 - hh, gap * 0.48, hh))
                if cfg.mirror in ("vertical", "both"):
                    p.drawRect(QRectF(rx, h / 2, gap * 0.48, hh))

    def _draw_wave(self, p, w, h, freq) -> None:
        pen = self._pen()
        pen.setColor(self._accent(1.0))
        p.setPen(pen)
        step = 3
        prev = None
        x = 0.0
        while x <= w:
            q = self._audio_value(x / step, max(1.0, w / step), freq)
            y = (
                h / 2
                + math.sin(x * 0.027 + self.phase * 3) * q * h * 0.23
                + math.sin(x * 0.074 - self.phase * 2) * q * h * 0.08
            )
            pt = QPointF(x, y)
            if prev is not None:
                p.drawLine(prev, pt)
            prev = pt
            x += step

    def _draw_circle(self, p, w, h, freq) -> None:
        cfg = self.config
        cx, cy = w / 2, h / 2
        R = min(w, h) * 0.19
        n = max(24, int(cfg.count))
        pen = self._pen()
        for i in range(n):
            a = i / n * math.pi * 2
            q = self._audio_value(i, n, freq)
            rr = R + q * min(w, h) * 0.32
            pen.setColor(self._accent(0.18 + 0.82 * q))
            p.setPen(pen)
            p.drawLine(
                QPointF(cx + math.cos(a) * R, cy + math.sin(a) * R),
                QPointF(cx + math.cos(a) * rr, cy + math.sin(a) * rr),
            )

    def _draw_radial(self, p, w, h, freq) -> None:
        cfg = self.config
        cx, cy = w / 2, h / 2
        R = min(w, h) * 0.28
        n = max(24, int(cfg.count))
        pen = self._pen()
        pen.setColor(self._accent(1.0))
        p.setPen(pen)
        prev = None
        first = None
        for i in range(n + 1):
            a = i / n * math.pi * 2
            r = R + self._audio_value(i, n, freq) * min(w, h) * 0.24
            pt = QPointF(cx + math.cos(a) * r, cy + math.sin(a) * r)
            if first is None:
                first = pt
            if prev is not None:
                p.drawLine(prev, pt)
            prev = pt
        if prev is not None and first is not None:
            p.drawLine(prev, first)

    def _draw_particles(self, p, w, h, freq) -> None:
        cfg = self.config
        q = self._audio_value(0.25, 1, freq)
        speed = 1 + q * 18 * cfg.sensitivity
        p.setPen(Qt.NoPen)
        for particle in self._particles:
            particle["x"] += particle["vx"] * speed
            particle["y"] += particle["vy"] * speed
            if particle["x"] < 0 or particle["x"] > 1:
                particle["vx"] *= -1
            if particle["y"] < 0 or particle["y"] > 1:
                particle["vy"] *= -1
            r = 1 + q * 5 * cfg.sensitivity
            p.setBrush(self._accent(0.10 + q * 0.72))
            p.drawEllipse(QPointF(particle["x"] * w, particle["y"] * h), r, r)

    def _draw_dots(self, p, w, h, freq) -> None:
        cfg = self.config
        n = max(16, int(cfg.count))
        gap = w / n
        p.setPen(Qt.NoPen)
        r = max(2.0, cfg.thickness * 1.3)
        for i in range(n):
            q = self._audio_value(i, n, freq)
            x = i * gap + gap * 0.5
            y = h - (10 + q * h * 0.8)
            p.setBrush(self._accent(0.3 + 0.7 * q))
            p.drawEllipse(QPointF(x, y), r, r)
            if cfg.mirror in ("vertical", "both"):
                p.drawEllipse(QPointF(x, h - y), r, r)

    def _draw_spiral(self, p, w, h, freq) -> None:
        cfg = self.config
        cx, cy = w / 2, h / 2
        n = max(60, int(cfg.count) * 2)
        max_r = min(w, h) * 0.46
        pen = self._pen()
        prev_pt = None
        for i in range(n):
            t = i / n
            q = self._audio_value(i, n, freq)
            a = t * math.pi * 10 + self.phase
            r = t * max_r + q * 22 * cfg.sensitivity
            pt = QPointF(cx + math.cos(a) * r, cy + math.sin(a) * r)
            if prev_pt is not None:
                pen.setColor(self._accent(0.15 + 0.85 * q))
                p.setPen(pen)
                p.drawLine(prev_pt, pt)
            prev_pt = pt

    def _draw_kaleidoscope(self, p, w, h, freq) -> None:
        cfg = self.config
        cx, cy = w / 2, h / 2
        segments = 8
        n = max(16, int(cfg.count) // segments + 8)
        R = min(w, h) * 0.06
        pen = self._pen()
        for s in range(segments):
            base_angle = s / segments * math.pi * 2
            prev_pt = None
            for i in range(n):
                q = self._audio_value(i, n, freq)
                a = base_angle + (i / n) * (math.pi * 2 / segments)
                r = R + q * min(w, h) * 0.42
                pt = QPointF(cx + math.cos(a) * r, cy + math.sin(a) * r)
                if prev_pt is not None:
                    pen.setColor(self._accent(0.2 + 0.8 * q))
                    p.setPen(pen)
                    p.drawLine(prev_pt, pt)
                prev_pt = pt
