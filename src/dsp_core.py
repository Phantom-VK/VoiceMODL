"""DSP helpers: pitch shifting and a simple autotune-like correction.

This is intentionally lightweight for Phase 3 POC. It uses librosa
for pitch shifting and a naive pitch detector for key snapping.
"""

from __future__ import annotations

import numpy as np
import librosa


SEMITONE_RATIO = 2 ** (1 / 12)


def pitch_shift(audio: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    """Shift pitch by N semitones using librosa.effects.pitch_shift.

    Args:
        audio: mono float32 array.
        sr: sample rate.
        semitones: positive for up, negative for down.
    """

    if semitones == 0:
        return audio
    return librosa.effects.pitch_shift(audio, sr=sr, n_steps=semitones, res_type="soxr_vhq")


def hz_to_midi(hz: float) -> float:
    if hz <= 0:
        return -np.inf
    return 69 + 12 * np.log2(hz / 440.0)


def midi_to_hz(midi: float) -> float:
    if np.isneginf(midi):
        return 0.0
    return 440.0 * (2 ** ((midi - 69) / 12))


KEY_OFFSETS = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}

SCALE_INTERVALS = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
}


def nearest_scale_midi(midi: float, key: str = "C", scale: str = "major") -> float:
    if np.isneginf(midi):
        return midi
    root = KEY_OFFSETS.get(key.upper(), 0)
    intervals = SCALE_INTERVALS.get(scale.lower(), SCALE_INTERVALS["major"])

    note_class = int(round(midi)) % 12
    octave = int(np.floor((midi - note_class) / 12))

    # Find nearest interval in scale
    best = None
    best_dist = 1e9
    for interval in intervals:
        candidate_class = (root + interval) % 12
        dist = abs(candidate_class - note_class)
        if dist < best_dist:
            best_dist = dist
            best = candidate_class

    snapped = 12 * octave + best
    return snapped


def simple_autotune(audio: np.ndarray, sr: int, key: str = "C", scale: str = "major") -> np.ndarray:
    """Very lightweight autotune: detect f0, snap to scale, apply pitch shift.

    - Detect f0 using librosa.pyin on a short frame.
    - Compute semitone offset to nearest scale note.
    - Apply pitch shift to the whole frame.
    """

    if len(audio) == 0:
        return audio

    f0, _, _ = librosa.pyin(audio, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"))
    f0_median = np.nanmedian(f0)
    if np.isnan(f0_median) or f0_median <= 0:
        return audio

    midi = hz_to_midi(f0_median)
    target_midi = nearest_scale_midi(midi, key=key, scale=scale)
    semitones = target_midi - midi

    return pitch_shift(audio, sr, semitones)

