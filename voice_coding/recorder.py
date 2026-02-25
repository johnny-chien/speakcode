"""Microphone capture using sounddevice."""

import io
import threading
import time

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"
MIN_DURATION_SECS = 0.5  # Ignore recordings shorter than this


class Recorder:
    def __init__(self):
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._start_time: float = 0

    def start(self):
        """Open mic stream and start accumulating audio frames."""
        with self._lock:
            self._frames = []
            self._start_time = time.monotonic()
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> bytes:
        """Stop recording and return WAV bytes. Returns empty if too short."""
        with self._lock:
            duration = time.monotonic() - self._start_time

            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            if not self._frames or duration < MIN_DURATION_SECS:
                self._frames = []
                return b""

            audio = np.concatenate(self._frames, axis=0)
            num_frames = len(self._frames)
            self._frames = []

        buf = io.BytesIO()
        sf.write(buf, audio, SAMPLE_RATE, format="WAV", subtype="FLOAT")
        wav_bytes = buf.getvalue()
        print(f"🎙  Recorded {duration:.1f}s ({num_frames} chunks, {len(audio)} samples, {len(wav_bytes) / 1024:.0f} KB WAV)")
        return wav_bytes

    def _callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            pass  # silently ignore overflow warnings
        self._frames.append(indata.copy())
