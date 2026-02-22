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
}

