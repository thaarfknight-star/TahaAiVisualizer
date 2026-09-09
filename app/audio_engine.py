"""Audio backend for TahaAi Visualizer.

Produces a rolling FFT magnitude array that the visualizer widget reads
every frame, regardless of the active source: a synthetic "demo" signal,
a locally chosen audio file, or the Windows system-audio (WASAPI) loopback.

Optional third-party libraries are imported defensively so the app still
starts (in demo mode) on machines where they are missing or unsupported.
"""
from __future__ import annotations

import threading
from typing import Optional

import numpy as np

try:
    import soundfile as sf
except Exception:  # pragma: no cover - optional dependency
    sf = None

try:
    import sounddevice as sd
except Exception:  # pragma: no cover - optional dependency
    sd = None

try:
    import soundcard as sc
except Exception:  # pragma: no cover - optional dependency / Linux quirks
    sc = None


class AudioEngine:
    FFT_SIZE = 2048

    def __init__(self, samplerate: int = 44100):
        self.samplerate = samplerate
        self.mode = "demo"  # "demo" | "file" | "system"
        self.file_name: Optional[str] = None
        self.error: Optional[str] = None

        self._lock = threading.Lock()
        self._latest_block = np.zeros(self.FFT_SIZE, dtype=np.float32)
        self._freq_data = np.zeros(self.FFT_SIZE // 2, dtype=np.float32)
        self._window = np.hanning(self.FFT_SIZE).astype(np.float32)

        self._stream = None
        self._playback_data: Optional[np.ndarray] = None
        self._playback_pos = 0

        self._loopback_thread: Optional[threading.Thread] = None
        self._loopback_stop = threading.Event()

    # ------------------------------------------------------------------ #
    # public controls
    # ------------------------------------------------------------------ #
    def stop(self) -> None:
        self._stop_stream()
        self._stop_loopback()
        self.mode = "demo"
        self.file_name = None

    def play_file(self, path: str) -> bool:
        self._stop_stream()
        self._stop_loopback()

        if sf is None or sd is None:
            self.error = "برای پخش فایل باید pysoundfile و sounddevice نصب باشند."
            return False

        try:
            data, sr = sf.read(path, dtype="float32", always_2d=True)
        except Exception as exc:  # noqa: BLE001
            self.error = f"خطا در باز کردن فایل صوتی: {exc}"
            return False

        self._playback_data = data.mean(axis=1)
        self._playback_pos = 0
        self.file_name = path.replace("\\", "/").split("/")[-1]

        def callback(outdata, frames, time_info, status):  # noqa: ANN001
            assert self._playback_data is not None
            start = self._playback_pos
            end = start + frames
            chunk = self._playback_data[start:end]
            if len(chunk) < frames:
                pad = frames - len(chunk)
                chunk = np.concatenate([chunk, self._playback_data[:pad]])
                self._playback_pos = pad  # loop back to start
            else:
                self._playback_pos = end
            outdata[:, 0] = chunk
            self._push_block(chunk)

        try:
            self._stream = sd.OutputStream(
                samplerate=sr, channels=1, blocksize=1024, callback=callback,
            )
            self._stream.start()
        except Exception as exc:  # noqa: BLE001
            self.error = f"خطا در پخش صدا: {exc}"
            return False

        self.mode = "file"
        self.error = None
        return True

    def start_system_audio(self) -> bool:
        self._stop_stream()
        self._stop_loopback()

        if sc is None:
            self.error = "کتابخانه soundcard در دسترس نیست (System audio مخصوص ویندوز است)."
            return False

        try:
            speaker = sc.default_speaker()
            mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
        except Exception as exc:  # noqa: BLE001
            self.error = f"دسترسی به خروجی صدای سیستم ممکن نشد: {exc}"
            return False

        self._loopback_stop.clear()

        def worker() -> None:
            try:
                with mic.recorder(samplerate=self.samplerate) as rec:
                    while not self._loopback_stop.is_set():
                        block = rec.record(numframes=1024)
                        mono = block.mean(axis=1) if block.ndim > 1 else block
                        self._push_block(mono.astype(np.float32))
            except Exception as exc:  # noqa: BLE001
                self.error = f"دریافت صدای سیستم قطع شد: {exc}"

        self._loopback_thread = threading.Thread(target=worker, daemon=True)
        self._loopback_thread.start()
        self.mode = "system"
        self.error = None
        return True

    # ------------------------------------------------------------------ #
    # per-frame analysis
    # ------------------------------------------------------------------ #
    def compute_frequency_data(self, smoothing: float = 0.72) -> Optional[np.ndarray]:
        """Returns None while in demo mode (caller uses a synthetic curve)."""
        if self.mode == "demo":
            return None

        with self._lock:
            block = self._latest_block.copy()

        windowed = block * self._window
        spectrum = np.abs(np.fft.rfft(windowed))[: self.FFT_SIZE // 2]
        spectrum = spectrum / (self.FFT_SIZE / 2)
        spectrum = np.clip(spectrum * 6.0, 0.0, 1.0).astype(np.float32)

        with self._lock:
            prev = self._freq_data
            smoothed = prev * smoothing + spectrum * (1.0 - smoothing)
            self._freq_data = smoothed
            return smoothed.copy()

    def snapshot(self) -> Optional[np.ndarray]:
        if self.mode == "demo":
            return None
        with self._lock:
            return self._freq_data.copy()

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #
    def _push_block(self, chunk: np.ndarray) -> None:
        with self._lock:
            n = len(chunk)
            if n >= self.FFT_SIZE:
                self._latest_block = chunk[-self.FFT_SIZE:].astype(np.float32)
            else:
                self._latest_block = np.concatenate(
                    [self._latest_block[n:], chunk.astype(np.float32)]
                )

    def _stop_stream(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass
            self._stream = None

    def _stop_loopback(self) -> None:
        self._loopback_stop.set()
        if self._loopback_thread is not None:
            self._loopback_thread.join(timeout=1.0)
            self._loopback_thread = None
