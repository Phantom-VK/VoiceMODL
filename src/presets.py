"""Preset definitions for quick voice profiles."""

from __future__ import annotations

PRESETS = {
    "normal": {
        "pitch_shift_semitones": 0,
        "autotune": False,
    },
    "female": {
        "pitch_shift_semitones": 5,
        "autotune": False,
    },
    "male": {
        "pitch_shift_semitones": -5,
        "autotune": False,
    },
    "tpain": {
        "pitch_shift_semitones": 0,
        "autotune": True,
        "key": "G",
        "scale": "major",
        "retune_speed": "fast",
    },
    "funny": {
        "pitch_shift_semitones": 0,
        "autotune": True,
        "key": "C",
        "scale": "major",
        "vibrato_hz": 5.0,
        "vibrato_depth_semitones": 2.0,
        "bitcrush_bits": 8,
        "downsample_factor": 2,
        "volume_db": 4.0,
    },
    "lofi": {
        "pitch_shift_semitones": -3,
        "autotune": False,
        "downsample_factor": 4,
        "bitcrush_bits": 6,
        "volume_db": 3.0,
    },
}
