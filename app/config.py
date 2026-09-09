"""Configuration model, color palette and presets for TahaAi Visualizer."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from typing import List

PALETTE: List[str] = [
    "#a995ff",  # violet (default)
    "#7cf5c4",  # mint
    "#ff9ecb",  # pink
    "#ffd166",  # amber
    "#5ec8ff",  # sky
    "#ff6b6b",  # coral
    "#c4ff6b",  # lime
]

MODES = [
    ("spectrum", "Spectrum"),
    ("bars", "Mirrored Bars"),
    ("wave", "Waveform"),
    ("circle", "Circular"),
    ("radial", "Radial"),
    ("particles", "Particles"),
    ("dots", "Dot Matrix"),
    ("spiral", "Spiral"),
    ("kaleidoscope", "Kaleidoscope"),
    ("bars3d", "Perspective Bars"),
    ("ring", "Pulse Rings"),
    ("starburst", "Starburst"),
    ("wavefill", "Filled Waveform"),
    ("equalizer", "LED Equalizer"),
    ("orbit", "Orbiting Dots"),
    ("flower", "Flower Bloom"),
    ("fireworks", "Fireworks"),
    ("tunnel", "Tunnel"),
    ("polygon", "Polygon Pulse"),
    ("grid", "Reactive Grid"),
    ("vortex", "Vortex"),
    ("constellation", "Constellation"),
    ("ribbon", "Ribbon Flow"),
]

BACKGROUNDS = [
    ("solid", "Solid"),
    ("gradient", "Gradient"),
    ("transparent", "Transparent"),
    ("image", "Image"),
]

MIRROR_MODES = [
    ("none", "None"),
    ("vertical", "Vertical"),
    ("both", "Both"),
]

GRADIENT_PRESETS = [
    ("Aurora", ["#a995ff", "#5ec8ff", "#7cf5c4"]),
    ("Sunset", ["#ffd166", "#ff9ecb", "#ff6b6b"]),
    ("Neon", ["#a995ff", "#ff6b6b"]),
    ("Ocean", ["#5ec8ff", "#7cf5c4"]),
    ("Fire", ["#ffd166", "#ff6b6b", "#c4ff6b"]),
    ("Candy", ["#ff9ecb", "#a995ff", "#5ec8ff"]),
]

PRESETS = {
    "Neon": dict(accent="#a995ff", background="gradient", glow=28, opacity=0.95,
                 thickness=3.0, trails=True),
    "Minimal": dict(accent="#f7f5fc", background="solid", glow=0, opacity=0.8,
                     thickness=1.5, trails=False),
    "Pulse": dict(accent="#ff6b6b", background="gradient", glow=18, opacity=1.0,
                   thickness=4.0, trails=True),
    "Ocean": dict(accent="#5ec8ff", background="gradient", glow=22, opacity=0.9,
                   thickness=2.5, trails=True),
    "Sunset": dict(accent="#ffd166", background="gradient", glow=16, opacity=0.92,
                    thickness=3.0, trails=True),
    "Monochrome": dict(accent="#f7f5fc", background="transparent", glow=6, opacity=0.85,
                        thickness=2.0, trails=False),
}


@dataclass
class Config:
    mode: str = "spectrum"
    accent: str = PALETTE[0]
    color_mode: str = "solid"        # solid | gradient
    gradient_colors: List[str] = field(default_factory=lambda: ["#a995ff", "#5ec8ff", "#ff6b6b"])
    background: str = "solid"
    background_image: str = ""
    sensitivity: float = 1.0
    smoothing: float = 0.72
    count: int = 80
    thickness: float = 3.0
    opacity: float = 0.9
    glow: float = 14.0
    mirror: str = "vertical"     # none | vertical | both
    bass_boost: bool = True
    trails: bool = True
    demo_mode: bool = True
    fps: int = 60
    always_on_top: bool = False
    theme: str = "dark"          # dark | light

    def apply_preset(self, name: str) -> None:
        preset = PRESETS.get(name)
        if not preset:
            return
        for key, value in preset.items():
            setattr(self, key, value)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        cfg = cls()
        for key, value in data.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        return cfg

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
