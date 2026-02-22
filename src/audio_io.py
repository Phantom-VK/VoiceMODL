"""Audio I/O helpers built on top of sounddevice.

Phase 2 deliverables:
- Enumerate devices for a CLI user prompt.
- Provide a minimal pass-through stream to prove routing works.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple
import queue
import threading
import time

import numpy as np
import sounddevice as sd


@dataclass
class DeviceInfo:
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float


def list_devices() -> List[DeviceInfo]:
    """Return a simplified list of audio devices."""

    devices = []
    for idx, dev in enumerate(sd.query_devices()):
        devices.append(
            DeviceInfo(
                index=idx,
                name=dev["name"],
                max_input_channels=dev["max_input_channels"],
                max_output_channels=dev["max_output_channels"],
                default_samplerate=float(dev["default_samplerate"]),
            )
        )
    return devices


def format_device(dev: DeviceInfo) -> str:
    return (
        f"[{dev.index}] {dev.name} | in:{dev.max_input_channels} "
        f"out:{dev.max_output_channels} | {dev.default_samplerate:.0f} Hz"
    )


def _channel_copy(indata: np.ndarray, channels: int) -> np.ndarray:
    """Ensure we have exactly `channels` columns, duplicating mono if needed."""

    if indata.ndim == 1:  # safety: force 2D
        indata = indata[:, None]

    if indata.shape[1] == channels:
        return indata
    if indata.shape[1] > channels:
        return indata[:, :channels]

    # If fewer input channels than requested, duplicate the first channel.
    first = indata[:, 0:1]
    return np.repeat(first, channels, axis=1)


def create_passthrough_stream(
    input_device: Optional[int] = None,
    output_device: Optional[int] = None,
    samplerate: float = 48_000,
    blocksize: int = 1024,
    channels: int = 1,
    dtype: str = "float32",
    process_fn: Optional[Callable] = None,
) -> sd.Stream:
    """Legacy simple stream: process (or copy) inside the audio callback."""

    def callback(indata, outdata, frames, time_info, status):  # type: ignore[unused-argument]
        if status:
            print(f"[audio_io] stream status: {status}")
        if process_fn is None:
            out = _channel_copy(indata, channels)
        else:
            mono_out = process_fn(indata, samplerate)
            if mono_out is None:
                mono_out = indata[:, 0]
            if mono_out.ndim == 1:
                mono_out = mono_out[:, None]
            out = _channel_copy(mono_out, channels)
        outdata[:] = out

    return sd.Stream(
        samplerate=samplerate,
        blocksize=blocksize,
        dtype=dtype,
        channels=channels,
        callback=callback,
        device=(input_device, output_device),
        latency="low",
    )


class RealTimeProcessor:
    """Queue-based audio processor to keep heavy DSP off the callback thread."""

    def __init__(
        self,
        process_fn: Callable[[np.ndarray, int], np.ndarray],
        *,
        input_device: Optional[int] = None,
        output_device: Optional[int] = None,
        samplerate: int = 48_000,
        blocksize: int = 1024,
        channels: int = 2,
        dtype: str = "float32",
        max_queue: int = 8,
    ):
        self.process_fn = process_fn
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.channels = channels
        self.dtype = dtype
        self._in_q: queue.Queue[np.ndarray] = queue.Queue(maxsize=max_queue)
        self._out_q: queue.Queue[np.ndarray] = queue.Queue(maxsize=max_queue)
        self._stop = threading.Event()
        self._worker: Optional[threading.Thread] = None
        self.stream = sd.Stream(
            samplerate=samplerate,
            blocksize=blocksize,
            dtype=dtype,
            channels=channels,
            callback=self._callback,
            device=(input_device, output_device),
            latency="low",
        )
        self.stats = {"dropped_in": 0, "underrun_out": 0}

    # Public control
    def start(self):
        self._stop.clear()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        self.stream.start()
        return self

    def stop(self):
        self._stop.set()
        if self._worker:
            self._worker.join(timeout=1.0)
        self.stream.stop()

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc, tb):
        self.stop()

    # Internals
    def _callback(self, indata, outdata, frames, time_info, status):  # type: ignore[unused-argument]
        if status:
            print(f"[audio_io] stream status: {status}")
        try:
            self._in_q.put_nowait(np.copy(indata))
        except queue.Full:
            self.stats["dropped_in"] += 1

        try:
            processed = self._out_q.get_nowait()
        except queue.Empty:
            processed = np.zeros_like(indata)
            self.stats["underrun_out"] += 1

        outdata[:] = processed

    def _worker_loop(self):
        while not self._stop.is_set():
            try:
                frame = self._in_q.get(timeout=0.1)
            except queue.Empty:
                continue
            mono = frame[:, 0]
            try:
                processed_mono = self.process_fn(mono, self.samplerate)
            except Exception as exc:  # pragma: no cover
                print(f"[audio_io] process_fn error: {exc}")
                processed_mono = mono
            if processed_mono.ndim == 1:
                processed = _channel_copy(processed_mono[:, None], self.channels)
            else:
                processed = _channel_copy(processed_mono, self.channels)
            processed = np.clip(processed, -1.0, 1.0).astype(self.dtype)
            try:
                self._out_q.put_nowait(processed)
            except queue.Full:
                # Drop oldest by replacing with latest
                try:
                    _ = self._out_q.get_nowait()
                    self._out_q.put_nowait(processed)
                except queue.Empty:
                    pass


def default_io_devices() -> Tuple[int, int]:
    """Return the current default (input, output) device indexes."""

    default_in, default_out = sd.default.device
    return int(default_in), int(default_out)
