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
            "bars3d": self._draw_bars3d,
            "ring": self._draw_ring,
            "starburst": self._draw_starburst,
            "wavefill": self._draw_wavefill,
            "equalizer": self._draw_equalizer,
            "orbit": self._draw_orbit,
            "flower": self._draw_flower,
            "fireworks": self._draw_fireworks,
            "tunnel": self._draw_tunnel,
            "polygon": self._draw_polygon,
            "grid": self._draw_grid,
            "vortex": self._draw_vortex,
            "constellation": self._draw_constellation,
            "ribbon": self._draw_ribbon,
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
    def _color_at(self, t: float, alpha: float = 1.0) -> QColor:
        """Color at position t in [0,1]: flat accent, or a sweep across the
        configured gradient stops when color_mode is 'gradient'."""
        cfg = self.config
        colors = cfg.gradient_colors
        if cfg.color_mode == "gradient" and colors and len(colors) >= 2:
            t = max(0.0, min(1.0, t))
            n = len(colors)
            seg = t * (n - 1)
            i = min(int(seg), n - 2)
            lt = seg - i
            c1, c2 = QColor(colors[i]), QColor(colors[i + 1])
            r = c1.red() + (c2.red() - c1.red()) * lt
            g = c1.green() + (c2.green() - c1.green()) * lt
            b = c1.blue() + (c2.blue() - c1.blue()) * lt
            c = QColor(int(r), int(g), int(b))
        else:
            c = QColor(cfg.accent)
        c.setAlphaF(max(0.0, min(1.0, cfg.opacity * alpha)))
        return c

    def _pen(self, t: float = 0.0) -> QPen:
        cfg = self.config
        pen = QPen(self._color_at(t, 1.0))
        pen.setWidthF(cfg.thickness)
        pen.setCapStyle(Qt.RoundCap)
        return pen

    def _accent(self, alpha: float, t: float = 0.0) -> QColor:
        return self._color_at(t, alpha)

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
            p.setBrush(self._accent(0.22 + 0.78 * q, i / n))
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
                p.setBrush(self._accent(0.28 + 0.72 * q, i / n))
                p.drawRect(QRectF(rx, h / 2 - hh, gap * 0.48, hh))
                if cfg.mirror in ("vertical", "both"):
                    p.drawRect(QRectF(rx, h / 2, gap * 0.48, hh))

    def _draw_wave(self, p, w, h, freq) -> None:
        pen = self._pen(0.5)
        pen.setColor(self._accent(1.0, 0.5))
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
                pen.setColor(self._accent(1.0, x / max(1.0, w)))
                p.setPen(pen)
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
            pen.setColor(self._accent(0.18 + 0.82 * q, i / n))
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
        prev = None
        first = None
        for i in range(n + 1):
            a = i / n * math.pi * 2
            r = R + self._audio_value(i, n, freq) * min(w, h) * 0.24
            pt = QPointF(cx + math.cos(a) * r, cy + math.sin(a) * r)
            if first is None:
                first = pt
            if prev is not None:
                pen.setColor(self._accent(1.0, i / n))
                p.setPen(pen)
                p.drawLine(prev, pt)
            prev = pt
        if prev is not None and first is not None:
            p.drawLine(prev, first)

    def _draw_particles(self, p, w, h, freq) -> None:
        cfg = self.config
        q = self._audio_value(0.25, 1, freq)
        speed = 1 + q * 18 * cfg.sensitivity
        p.setPen(Qt.NoPen)
        n = len(self._particles)
        for idx, particle in enumerate(self._particles):
            particle["x"] += particle["vx"] * speed
            particle["y"] += particle["vy"] * speed
            if particle["x"] < 0 or particle["x"] > 1:
                particle["vx"] *= -1
            if particle["y"] < 0 or particle["y"] > 1:
                particle["vy"] *= -1
            r = 1 + q * 5 * cfg.sensitivity
            p.setBrush(self._accent(0.10 + q * 0.72, idx / n))
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
            p.setBrush(self._accent(0.3 + 0.7 * q, i / n))
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
                pen.setColor(self._accent(0.15 + 0.85 * q, t))
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
                    pen.setColor(self._accent(0.2 + 0.8 * q, s / segments))
                    p.setPen(pen)
                    p.drawLine(prev_pt, pt)
                prev_pt = pt

    # extra modes --------------------------------------------------------- #
    def _draw_bars3d(self, p, w, h, freq) -> None:
        cfg = self.config
        n = max(12, int(cfg.count / 1.5))
        gap = w / n
        depth = gap * 0.35
        p.setPen(Qt.NoPen)
        for i in range(n):
            q = self._audio_value(i, n, freq)
            hh = 6 + q * h * 0.62
            x = i * gap
            base_c = self._accent(0.35 + 0.65 * q, i / n)
            p.setBrush(base_c)
            p.drawRect(QRectF(x, h - hh, gap * 0.55, hh))
            top = QColor(base_c)
            top.setAlphaF(min(1.0, base_c.alphaF() * 1.35))
            p.setBrush(top)
            side = QPointF(x + depth, h - hh - depth)
            p.drawPolygon([QPointF(x, h - hh), QPointF(x + gap * 0.55, h - hh),
                            QPointF(x + gap * 0.55 + depth, h - hh - depth), side])

    def _draw_ring(self, p, w, h, freq) -> None:
        cfg = self.config
        cx, cy = w / 2, h / 2
        rings = max(6, int(cfg.count / 8))
        max_r = min(w, h) * 0.46
        p.setBrush(Qt.NoBrush)
        for i in range(rings):
            t = i / rings
            q = self._audio_value(i, rings, freq)
            r = 10 + t * max_r + q * 18 * cfg.sensitivity
            pen = self._pen(t)
            pen.setColor(self._accent(0.15 + 0.7 * q, t))
            pen.setWidthF(max(1.0, cfg.thickness * (0.6 + q)))
            p.setPen(pen)
            p.drawEllipse(QPointF(cx, cy), r, r)

    def _draw_starburst(self, p, w, h, freq) -> None:
        cfg = self.config
        cx, cy = w / 2, h / 2
        n = max(16, int(cfg.count / 2))
        R0 = min(w, h) * 0.05
        maxlen = min(w, h) * 0.45
        pen = self._pen()
        for i in range(n):
            a = i / n * math.pi * 2 + self.phase * 0.3
            q = self._audio_value(i, n, freq)
            r = R0 + q * maxlen
            pen.setColor(self._accent(0.2 + 0.8 * q, i / n))
            pen.setWidthF(max(1.0, cfg.thickness * (0.4 + q)))
            p.setPen(pen)
            p.drawLine(QPointF(cx + math.cos(a) * R0, cy + math.sin(a) * R0),
                       QPointF(cx + math.cos(a) * r, cy + math.sin(a) * r))

    def _draw_wavefill(self, p, w, h, freq) -> None:
        step = 4
        pts = [QPointF(0, h)]
        x = 0.0
        while x <= w:
            q = self._audio_value(x / step, max(1.0, w / step), freq)
            y = h / 2 + math.sin(x * 0.02 + self.phase * 2.4) * q * h * 0.3
            pts.append(QPointF(x, y))
            x += step
        pts.append(QPointF(w, h))
        p.setPen(Qt.NoPen)
        p.setBrush(self._accent(0.5, 0.5))
        p.drawPolygon(pts)
        pen = self._pen(0.5)
        pen.setColor(self._accent(1.0, 0.9))
        p.setPen(pen)
        for i in range(1, len(pts) - 1):
            p.drawLine(pts[i], pts[i + 1])

    def _draw_equalizer(self, p, w, h, freq) -> None:
        cfg = self.config
        n = max(12, int(cfg.count / 3))
        gap = w / n
        segs = 14
        seg_h = h / segs * 0.92
        p.setPen(Qt.NoPen)
        for i in range(n):
            q = self._audio_value(i, n, freq)
            lit = int(q * segs)
            x = i * gap + gap * 0.12
            for s in range(segs):
                y = h - (s + 1) * (h / segs)
                on = s < lit
                alpha = (0.85 if on else 0.08)
                p.setBrush(self._accent(alpha, i / n))
                p.drawRect(QRectF(x, y, gap * 0.76, seg_h))

    def _draw_orbit(self, p, w, h, freq) -> None:
        cfg = self.config
        cx, cy = w / 2, h / 2
        n = max(10, int(cfg.count / 4))
        p.setPen(Qt.NoPen)
        for i in range(n):
            t = i / n
            q = self._audio_value(i, n, freq)
            r = min(w, h) * (0.1 + t * 0.35) + q * 14
            a = self.phase * (1 + t) + t * math.pi * 2
            x = cx + math.cos(a) * r
            y = cy + math.sin(a) * r * 0.6
            rad = 2 + q * 8 * cfg.sensitivity
            p.setBrush(self._accent(0.25 + 0.75 * q, t))
            p.drawEllipse(QPointF(x, y), rad, rad)

    def _draw_flower(self, p, w, h, freq) -> None:
        cfg = self.config
        cx, cy = w / 2, h / 2
        petals = 6
        n = 160
        R = min(w, h) * 0.05
        maxr = min(w, h) * 0.4
        avg_q = self._audio_value(n * 0.3, n, freq)
        pen = self._pen()
        prev = None
        first = None
        for i in range(n + 1):
            t = i / n
            a = t * math.pi * 2
            q = self._audio_value(i, n, freq)
            r = R + (maxr * (0.4 + 0.6 * q)) * abs(math.sin(petals * a / 2 + self.phase))
            pt = QPointF(cx + math.cos(a) * r, cy + math.sin(a) * r)
            if first is None:
                first = pt
            if prev is not None:
                pen.setColor(self._accent(0.3 + 0.7 * avg_q, t))
                p.setPen(pen)
                p.drawLine(prev, pt)
            prev = pt
        if prev and first:
            p.drawLine(prev, first)

    def _draw_fireworks(self, p, w, h, freq) -> None:
        cfg = self.config
        cx, cy = w / 2, h / 2
        bursts = 5
        p.setPen(Qt.NoPen)
        for b in range(bursts):
            bt = (self.phase * 0.6 + b / bursts) % 1.0
            bx = w * ((b * 0.618) % 1.0)
            by = h * (0.25 + 0.4 * ((b * 0.382) % 1.0))
            rays = 18
            q = self._audio_value(b, bursts, freq)
            spread = bt * min(w, h) * 0.22 * (0.6 + q)
            for i in range(rays):
                a = i / rays * math.pi * 2
                r = spread
                alpha = max(0.0, (1.0 - bt) * (0.4 + 0.6 * q))
                p.setBrush(self._accent(alpha, i / rays))
                x = bx + math.cos(a) * r
                y = by + math.sin(a) * r
                rad = max(1.0, cfg.thickness * (1.0 - bt) * 1.5)
                p.drawEllipse(QPointF(x, y), rad, rad)

    def _draw_tunnel(self, p, w, h, freq) -> None:
        cfg = self.config
        cx, cy = w / 2, h / 2
        rings = 16
        p.setBrush(Qt.NoBrush)
        for i in range(rings):
            t = ((i / rings) + (self.phase * 0.15)) % 1.0
            q = self._audio_value(i, rings, freq)
            size = t * min(w, h) * (0.9 + q * 0.3)
            pen = self._pen(t)
            alpha = (1.0 - t) * (0.5 + 0.5 * q)
            pen.setColor(self._accent(alpha, t))
            p.setPen(pen)
            p.drawRect(QRectF(cx - size / 2, cy - size / 2, size, size))

    def _draw_polygon(self, p, w, h, freq) -> None:
        cfg = self.config
        cx, cy = w / 2, h / 2
        sides = max(3, min(14, int(cfg.count / 12)))
        R = min(w, h) * 0.3
        pen = self._pen()
        prev = None
        first = None
        for i in range(sides + 1):
            t = i / sides
            a = t * math.pi * 2 + self.phase * 0.5
            q = self._audio_value(i, sides, freq)
            r = R + q * min(w, h) * 0.22
            pt = QPointF(cx + math.cos(a) * r, cy + math.sin(a) * r)
            if first is None:
                first = pt
            if prev is not None:
                pen.setColor(self._accent(0.4 + 0.6 * q, t))
                p.setPen(pen)
                p.drawLine(prev, pt)
            prev = pt
        if prev and first:
            p.drawLine(prev, first)

    def _draw_grid(self, p, w, h, freq) -> None:
        cfg = self.config
        cols = max(6, int(cfg.count / 6))
        rows = max(4, cols // 2)
        cw, ch = w / cols, h / rows
        p.setPen(Qt.NoPen)
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                q = self._audio_value(idx, rows * cols, freq)
                scale = 0.25 + q * 0.75
                cx = c * cw + cw / 2
                cy = r * ch + ch / 2
                p.setBrush(self._accent(0.15 + 0.7 * q, c / cols))
                sw, sh = cw * 0.8 * scale, ch * 0.8 * scale
                p.drawRoundedRect(QRectF(cx - sw / 2, cy - sh / 2, sw, sh), 3, 3)

    def _draw_vortex(self, p, w, h, freq) -> None:
        cfg = self.config
        cx, cy = w / 2, h / 2
        n = max(60, int(cfg.count) * 2)
        max_r = min(w, h) * 0.46
        for arm in (-1, 1):
            pen = self._pen()
            prev_pt = None
            for i in range(n):
                t = i / n
                q = self._audio_value(i, n, freq)
                a = t * math.pi * 8 * arm + self.phase * 1.4
                r = t * max_r + q * 18 * cfg.sensitivity
                pt = QPointF(cx + math.cos(a) * r, cy + math.sin(a) * r)
                if prev_pt is not None:
                    pen.setColor(self._accent(0.15 + 0.85 * q, t))
                    p.setPen(pen)
                    p.drawLine(prev_pt, pt)
                prev_pt = pt

    def _draw_constellation(self, p, w, h, freq) -> None:
        cfg = self.config
        n = len(self._particles)
        pts = []
        p.setPen(Qt.NoPen)
        for idx, particle in enumerate(self._particles[:90]):
            q = self._audio_value(idx, 90, freq)
            x, y = particle["x"] * w, particle["y"] * h
            pts.append((x, y, q))
            rad = 1.2 + q * 3
            p.setBrush(self._accent(0.35 + 0.65 * q, idx / n))
            p.drawEllipse(QPointF(x, y), rad, rad)
        max_dist = min(w, h) * 0.14
        pen = self._pen()
        for i in range(len(pts)):
            x1, y1, q1 = pts[i]
            for j in range(i + 1, min(i + 6, len(pts))):
                x2, y2, q2 = pts[j]
                d = math.hypot(x1 - x2, y1 - y2)
                if d < max_dist:
                    alpha = (1 - d / max_dist) * (0.15 + 0.5 * max(q1, q2))
                    pen.setColor(self._accent(alpha, i / len(pts)))
                    pen.setWidthF(1.0)
                    p.setPen(pen)
                    p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_ribbon(self, p, w, h, freq) -> None:
        cfg = self.config
        layers = 4
        for layer in range(layers):
            lt = layer / layers
            pen = self._pen(lt)
            prev = None
            step = 6
            x = 0.0
            while x <= w:
                q = self._audio_value(x / step, max(1.0, w / step), freq)
                y = (
                    h * (0.3 + lt * 0.15)
                    + math.sin(x * 0.018 + self.phase * (1.6 + lt) + lt * 4) * q * h * 0.22
                )
                pt = QPointF(x, y)
                if prev is not None:
                    pen.setColor(self._accent(0.2 + 0.6 * q, lt))
                    p.setPen(pen)
                    p.drawLine(prev, pt)
                prev = pt
                x += step
