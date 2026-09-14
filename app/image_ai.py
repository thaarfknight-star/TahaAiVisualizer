"""TahaAi Image AI — smart image scanner for the visualizer.

Give it a picture (album art, a photo, anything) and it:

1. extracts the dominant color palette with k-means clustering
   (a real machine-learning algorithm, implemented here in pure numpy),
2. detects the image "mood" (dark / bright, warm / cool, vivid / muted),
3. returns ready-to-apply visualizer settings so the visualizer drawn
   ON the image feels like it belongs to that image.

The heavy Qt-dependent part (loading a file into pixels) is isolated in
``load_pixels_qimage``; everything else is pure numpy and fully testable
without a display or Qt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np


@dataclass
class ImageAnalysis:
    """Result of scanning one image."""
    palette: List[str] = field(default_factory=list)  # hex colors, dominant first
    mood_fa: str = ""          # Persian mood description, e.g. "تیره و دراماتیک • گرم"
    brightness: float = 0.0    # 0..1 mean luminance
    saturation: float = 0.0    # 0..1 mean color saturation
    warmth: float = 0.0        # -1..1  (negative = cool/blue, positive = warm/red)
    contrast: float = 0.0      # 0..1 std of luminance
    overlay_dim: float = 0.5   # suggested dark-overlay alpha for image background
    suggested_mode: str = "spectrum"  # visualizer mode that fits the mood


# --------------------------------------------------------------------------- #
# k-means (numpy only)
# --------------------------------------------------------------------------- #
def _kmeans(pixels: np.ndarray, k: int, seed: int = 7, iters: int = 40):
    """Cluster RGB pixels; returns (centers [k,3], labels [n])."""
    data = pixels.reshape(-1, 3).astype(np.float64)
    n = len(data)
    k = max(2, min(k, n))
    rng = np.random.default_rng(seed)
    uniq = np.unique(data, axis=0)
    if len(uniq) < k:
        # flat images (e.g. solid color): pad with slightly jittered copies
        # so we still return k representative shades
        need = k - len(uniq)
        jitter = uniq[rng.choice(len(uniq), size=need)]
        jitter = jitter + rng.normal(0, 5, (need, 3))
        pool = np.vstack([uniq, np.clip(jitter, 0, 255)])
    else:
        pool = uniq
    centers = pool[rng.choice(len(pool), size=k, replace=False)].astype(np.float64)

    for _ in range(iters):
        dist = ((data[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = dist.argmin(axis=1)
        new_centers = centers.copy()
        for i in range(k):
            pts = data[labels == i]
            if len(pts):
                new_centers[i] = pts.mean(axis=0)
        if np.allclose(new_centers, centers, atol=1e-3):
            break
        centers = new_centers
    return centers, labels


def _rgb_to_hex(rgb) -> str:
    r, g, b = (int(round(max(0, min(255, v)))) for v in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def extract_palette(pixels: np.ndarray, k: int = 5, seed: int = 7) -> List[str]:
    """Dominant colors of the image as hex strings, most dominant first."""
    if pixels.size == 0:
        return []
    rgb = pixels.reshape(-1, 3)
    centers, labels = _kmeans(rgb, k=k, seed=seed)
    counts = np.bincount(labels, minlength=len(centers))
    order = np.argsort(-counts)
    return [_rgb_to_hex(centers[i]) for i in order]


# --------------------------------------------------------------------------- #
# mood analysis
# --------------------------------------------------------------------------- #
def _mood_stats(pixels: np.ndarray) -> dict:
    rgb = pixels.reshape(-1, 3).astype(np.float64) / 255.0
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    mx = rgb.max(axis=1)
    mn = rgb.min(axis=1)
    sat = np.where(mx > 1e-6, (mx - mn) / mx, 0.0)
    return {
        "brightness": float(lum.mean()),
        "saturation": float(sat.mean()),
        "warmth": float((r - b).mean()),          # -1..1
        "contrast": float(lum.std() * 2.2),       # scaled to ~0..1
    }


def _describe_mood(stats: dict) -> str:
    b, s, w = stats["brightness"], stats["saturation"], stats["warmth"]
    if b < 0.32:
        base = "تیره و دراماتیک"
    elif b > 0.62:
        base = "روشن و پرانرژی"
    else:
        base = "متعادل"
    if w > 0.06:
        tone = "گرم"
    elif w < -0.06:
        tone = "سرد"
    else:
        tone = "خنثی"
    vivid = " • زنده و پررنگ" if s > 0.45 else (" • ملایم و کم‌رنگ" if s < 0.18 else "")
    return f"{base} • حال‌وهوای {tone}{vivid}"


def _suggest_settings(stats: dict) -> dict:
    b, s = stats["brightness"], stats["saturation"]
    # Dark overlay: brighter images need more dimming so bars stay readable.
    overlay_dim = float(min(0.75, max(0.25, b)))
    # Glowy modes read best on dark images; bold shapes on bright ones.
    if b < 0.4:
        mode = "particles" if s > 0.35 else "fireworks"
    elif b > 0.65:
        mode = "spectrum"
    else:
        mode = "tunnel" if s > 0.4 else "wave"
    return {"overlay_dim": overlay_dim, "suggested_mode": mode}


def analyze_image(pixels: np.ndarray, k: int = 5) -> ImageAnalysis:
    """Full AI scan of an image given as an RGB numpy array (H, W, 3)."""
    if pixels.ndim != 3 or pixels.shape[2] < 3:
        raise ValueError("pixels باید آرایه‌ای به شکل (H, W, 3) باشد")
    rgb = pixels[:, :, :3]
    # downscale for speed; analysis doesn't need full resolution
    h, w = rgb.shape[:2]
    scale = min(1.0, 160.0 / max(h, w))
    if scale < 1.0:
        nh, nw = max(1, int(h * scale)), max(1, int(w * scale))
        ys = (np.linspace(0, h - 1, nh)).astype(int)
        xs = (np.linspace(0, w - 1, nw)).astype(int)
        small = rgb[ys][:, xs]
    else:
        small = rgb

    palette = extract_palette(small, k=k)
    stats = _mood_stats(small)
    sugg = _suggest_settings(stats)
    return ImageAnalysis(
        palette=palette,
        mood_fa=_describe_mood(stats),
        brightness=round(stats["brightness"], 3),
        saturation=round(stats["saturation"], 3),
        warmth=round(stats["warmth"], 3),
        contrast=round(min(1.0, stats["contrast"]), 3),
        overlay_dim=round(sugg["overlay_dim"], 2),
        suggested_mode=sugg["suggested_mode"],
    )


# --------------------------------------------------------------------------- #
# Qt file loader (isolated so the analysis stays Qt-free)
# --------------------------------------------------------------------------- #
def load_pixels_qimage(path: str) -> np.ndarray:
    """Load an image file into an RGB numpy array using Qt (no PIL needed)."""
    try:
        from PySide6.QtGui import QImage
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("PySide6 در دسترس نیست") from exc
    img = QImage(path).convertToFormat(QImage.Format.Format_RGB888)
    if img.isNull():
        raise ValueError("فایل تصویر قابل خواندن نیست")
    w, h = img.width(), img.height()
    ptr = img.constBits()
    arr = np.frombuffer(ptr, dtype=np.uint8, count=h * img.bytesPerLine())
    arr = arr.reshape(h, img.bytesPerLine())[:, : w * 3].reshape(h, w, 3)
    return arr.copy()
