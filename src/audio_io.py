"""Audio I/O helpers built on top of sounddevice.

Phase 2 deliverables:
- Enumerate devices for a CLI user prompt.
- Provide a minimal pass-through stream to prove routing works.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

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
    process_fn: Optional[callable] = None,
) -> sd.Stream:
    """Create a sounddevice Stream that copies (or processes) input to output.

    Args:
        process_fn: callable(frame, sr) -> mono np.ndarray. If None, acts as pure pass-through.
    """

    def callback(indata, outdata, frames, time, status):  # type: ignore[unused-argument]
        if status:
            # Status contains XRuns/underflows; print once per callback.
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

    stream = sd.Stream(
        samplerate=samplerate,
        blocksize=blocksize,
        dtype=dtype,
        channels=channels,
        callback=callback,
        device=(input_device, output_device),
        latency="low",  # hint: pulse will negotiate closest option
    )
    return stream


def default_io_devices() -> Tuple[int, int]:
    """Return the current default (input, output) device indexes."""

    default_in, default_out = sd.default.device
    return int(default_in), int(default_out)
