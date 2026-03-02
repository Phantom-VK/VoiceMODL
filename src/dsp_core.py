"""DSP helpers: pitch shifting and a simple autotune-like correction.
"""

from __future__ import annotations

import numpy as np
import librosa


SEMITONE_RATIO = 2 ** (1 / 12)

# Utility for vibrato (delay-line modulation) and bitcrush (quantization).
def apply_vibrato(
    audio: np.ndarray,
    sr: int,
    depth_semitones: float = 0.0,
    rate_hz: float = 5.0,
    base_semitones: float = 0.0,
    phase: float = 0.0,
) -> tuple[np.ndarray, float]:
    """
    Light vibrato via time-varying fractional delay.
    depth_semitones: peak deviation in semitones (converted to delay samples).
    rate_hz: LFO frequency.
    base_semitones: static shift applied before modulation.
    phase: running phase in radians (returned for continuity across frames).
    """
    if depth_semitones == 0 and base_semitones == 0:
        return audio, phase

    n = np.arange(len(audio))
    # Convert semitone modulation to delay in samples (approx via small-angle log2 relation)
    # delay_samples ≈ (12 / ln(2)) * ln(freq_ratio) / (2π*rate) is messy;
    # simpler: translate semitone modulation into instantaneous resample index.
    lfo = np.sin(phase + 2 * np.pi * rate_hz * n / sr)
    semitone_mod = base_semitones + depth_semitones * lfo
    # Convert semitone modulation to playback rate multiplier
    rate = SEMITONE_RATIO ** semitone_mod
    # Integrate rate to get time-warped index
    t = np.cumsum(rate)
    t = t * (1.0 / np.mean(rate))  # normalize length
    t = t - t[0]
    t = t * (len(audio) - 1) / (t[-1] if t[-1] != 0 else 1)
    # Resample with linear interp
    out = np.interp(t, n, audio, left=0.0, right=0.0)
    new_phase = (phase + 2 * np.pi * rate_hz * len(audio) / sr) % (2 * np.pi)
    return out.astype(audio.dtype), new_phase


def apply_bitcrush(audio: np.ndarray, bits: int = 8) -> np.ndarray:
    """Quantize signal to given bit depth."""
    if bits <= 0 or bits >= 16:
        return audio
    levels = float(2 ** bits)
    return np.round(audio * (levels / 2)) / (levels / 2)


def apply_downsample(audio: np.ndarray, factor: int) -> np.ndarray:
    """Naive decimate + linear upsample back to original length."""
    if factor is None or factor <= 1:
        return audio
    dec = audio[::factor]
    # Upsample via interpolation to original length
    x_dec = np.linspace(0, 1, num=len(dec), endpoint=True)
    x_full = np.linspace(0, 1, num=len(audio), endpoint=True)
    up = np.interp(x_full, x_dec, dec)
    return up.astype(audio.dtype)


def apply_gain_db(audio: np.ndarray, gain_db: float) -> np.ndarray:
    """Apply gain in dB."""
    if gain_db == 0:
        return audio
    factor = 10 ** (gain_db / 20.0)
    return (audio * factor).astype(audio.dtype)


def pitch_shift(audio: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    """Shift pitch by N semitones using librosa.effects.pitch_shift.

    Args:
        audio: mono float32 array.
        sr: sample rate.
        semitones: positive for up, negative for down.
    """

    if semitones == 0:
        return audio
    # Use high-quality resampler; adjust blocksize externally if CPU is tight.
    return librosa.effects.pitch_shift(audio, sr=sr, n_steps=semitones, res_type="soxr_hq")


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
    # Ignore warnings when pyin returns all-NaN on silence/noise
    f0_median = np.nanmedian(f0)
    if np.isnan(f0_median) or f0_median <= 0:
        # No pitch detected (silence/noise); leave frame untouched.
        return audio

    midi = hz_to_midi(f0_median)
    target_midi = nearest_scale_midi(midi, key=key, scale=scale)
    semitones = target_midi - midi

    return pitch_shift(audio, sr, semitones)
