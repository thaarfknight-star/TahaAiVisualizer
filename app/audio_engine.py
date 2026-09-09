"""Audio backend for TahaAi Visualizer.

Produces a rolling FFT magnitude array that the visualizer widget reads
every frame, regardless of the active source: a synthetic "demo" signal,
a locally chosen audio file, or the Windows system-audio (WASAPI) loopback.

Optional third-party libraries are imported defensively so the app still
starts (in demo mode) on machines where they are missing or unsupported.
"""
from __future__ import annotations

import random
import threading
from typing import List, Optional

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
        self._paused = False
        self._track_ended = False

        # Playlist state -------------------------------------------------
        self.playlist: List[str] = []
        self.playlist_index: int = -1
        self.repeat_all: bool = True
        self.shuffle: bool = False

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
        self._paused = False

    def play_file(self, path: str) -> bool:
        """Play a single, standalone file (replaces any existing playlist)."""
        self.playlist = [path]
        self.playlist_index = 0
        return self._play_current_index()

    # -- playlist -------------------------------------------------------- #
    def add_to_playlist(self, paths: List[str]) -> bool:
        """Add one or more files to the playlist. Starts playback if idle."""
        self._stop_loopback()
        was_empty = not self.playlist
        self.playlist.extend(paths)
        if was_empty and self.playlist:
            self.playlist_index = 0
            return self._play_current_index()
        return True

    def play_index(self, index: int) -> bool:
        if not (0 <= index < len(self.playlist)):
            return False
        self.playlist_index = index
        return self._play_current_index()

    def play_pause_toggle(self) -> bool:
        if self._stream is None:
            return self._play_current_index()
        self._paused = not self._paused
        return True

    def next_track(self) -> bool:
        if not self.playlist:
            return False
        if self.shuffle and len(self.playlist) > 1:
            choices = [i for i in range(len(self.playlist)) if i != self.playlist_index]
            self.playlist_index = random.choice(choices)
            return self._play_current_index()
        if self.playlist_index + 1 < len(self.playlist):
            self.playlist_index += 1
        elif self.repeat_all:
            self.playlist_index = 0
        else:
            return False
        return self._play_current_index()

    def prev_track(self) -> bool:
        if not self.playlist:
            return False
        if self.playlist_index - 1 >= 0:
            self.playlist_index -= 1
        elif self.repeat_all:
            self.playlist_index = len(self.playlist) - 1
        else:
            self.playlist_index = 0
        return self._play_current_index()

    def remove_from_playlist(self, index: int) -> None:
        if not (0 <= index < len(self.playlist)):
            return
        was_current = index == self.playlist_index
        del self.playlist[index]
        if not self.playlist:
            self._stop_stream()
            self.playlist_index = -1
            self.mode = "demo"
            return
        if index < self.playlist_index:
            self.playlist_index -= 1
        elif was_current:
            self.playlist_index = min(self.playlist_index, len(self.playlist) - 1)
            self._play_current_index()

    def clear_playlist(self) -> None:
        self._stop_stream()
        self.playlist = []
        self.playlist_index = -1
        self.mode = "demo"
        self.file_name = None

    def poll_track_finished(self) -> bool:
        """Call periodically from the UI thread. Auto-advances the playlist
        when the current track has finished; returns True if it did."""
        if not self._track_ended:
            return False
        self._track_ended = False
        if not self.next_track():
            self.mode = "demo"
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
    def _play_current_index(self) -> bool:
        if not (0 <= self.playlist_index < len(self.playlist)):
            return False
        return self._start_stream_for_path(self.playlist[self.playlist_index])

    def _start_stream_for_path(self, path: str) -> bool:
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
        self._track_ended = False
        self._paused = False
        self.file_name = path.replace("\\", "/").split("/")[-1]

        def callback(outdata, frames, time_info, status):  # noqa: ANN001
            if self._paused:
                outdata[:, 0] = 0.0
                return
            assert self._playback_data is not None
            start = self._playback_pos
            end = start + frames
            chunk = self._playback_data[start:end]
            if len(chunk) < frames:
                pad = frames - len(chunk)
                chunk = np.concatenate([chunk, np.zeros(pad, dtype=np.float32)])
                self._playback_pos = end
                self._track_ended = True
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
