"""Preset definitions for quick voice profiles."""

from __future__ import annotations

PRESETS = {
    "off": {"pitch_shift_semitones": 0, "autotune": False},
    "man": {"pitch_shift_semitones": -1.5, "autotune": False},
    "woman": {"pitch_shift_semitones": 2.5, "autotune": False},
    "boy": {"pitch_shift_semitones": 1.25, "autotune": False},
    "girl": {"pitch_shift_semitones": 2.8, "autotune": False},
    "darth_vader": {"pitch_shift_semitones": -6.0, "autotune": False},
    "chipmunk": {"pitch_shift_semitones": 10.0, "autotune": False},
    "bad_mic": {"pitch_shift_semitones": 0, "autotune": False, "downsample_factor": 8, "volume_db": 0},
    "radio": {"pitch_shift_semitones": 0, "autotune": False, "downsample_factor": 6, "volume_db": 0},
    "megaphone": {"pitch_shift_semitones": 0, "autotune": False, "downsample_factor": 2, "volume_db": 0},
    "tpain": {
        "pitch_shift_semitones": 0,
        "autotune": True,
        "key": "Eb",
        "scale": "major",
        "retune_strength": 1.0,
        "volume_db": 1.5,
    },
}
