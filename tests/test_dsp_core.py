import numpy as np

from src.dsp_core import pitch_shift


def _peak_freq(signal, sr):
    # crude peak finder in frequency domain for test purposes
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(len(signal), 1 / sr)
    peak_idx = np.argmax(np.abs(spectrum))
    return freqs[peak_idx]


def test_pitch_shift_up_two_semitones():
    sr = 48000
    duration = 0.5
    f = 440.0  # A4
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = 0.5 * np.sin(2 * np.pi * f * t).astype(np.float32)

    shifted = pitch_shift(tone, sr, 2)
    peak = _peak_freq(shifted, sr)
    expected = f * 2 ** (2 / 12)  # ≈ 493.88 Hz
    assert abs(peak - expected) < 6.0
