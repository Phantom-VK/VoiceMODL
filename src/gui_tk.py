"""Minimal Tkinter GUI for VoiceModL (no external GUI deps).

Run: python -m src.gui_tk
"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

import numpy as np

from audio_io import RealTimeProcessor, list_devices
from dsp_core import (
    apply_bitcrush,
    apply_downsample,
    apply_gain_db,
    apply_vibrato,
    pitch_shift,
    simple_autotune,
)
from presets import PRESETS


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VoiceModL (Tk)")
        self.geometry("520x360")

        self.processor: Optional[RealTimeProcessor] = None
        self.vibrato_phase = 0.0

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        # Devices
        ttk.Label(frame, text="Input device").grid(row=0, column=0, sticky="w")
        self.input_var = tk.StringVar()
        ttk.Label(frame, text="Output device").grid(row=1, column=0, sticky="w")
        self.output_var = tk.StringVar()

        devices = list_devices()
        choices = [f"{d.index}:{d.name}" for d in devices]
        if not choices:
            choices = ["0:default"]
        self.input_box = ttk.Combobox(frame, textvariable=self.input_var, values=choices, state="readonly")
        self.output_box = ttk.Combobox(frame, textvariable=self.output_var, values=choices, state="readonly")
        self.input_box.grid(row=0, column=1, sticky="ew")
        self.output_box.grid(row=1, column=1, sticky="ew")
        self.input_box.current(0)
        self.output_box.current(0)

        # Preset
        ttk.Label(frame, text="Preset").grid(row=2, column=0, sticky="w")
        self.preset_var = tk.StringVar(value=list(PRESETS.keys())[0])
        self.preset_box = ttk.Combobox(frame, textvariable=self.preset_var, values=list(PRESETS.keys()), state="readonly")
        self.preset_box.grid(row=2, column=1, sticky="ew")

        # Dry/wet
        ttk.Label(frame, text="Dry/Wet").grid(row=3, column=0, sticky="w")
        self.drywet = tk.DoubleVar(value=1.0)
        ttk.Scale(frame, variable=self.drywet, from_=0.0, to=1.0, orient="horizontal").grid(row=3, column=1, sticky="ew")

        # Blocksize
        ttk.Label(frame, text="Blocksize").grid(row=4, column=0, sticky="w")
        self.blocksize = tk.IntVar(value=2048)
        ttk.Spinbox(frame, from_=256, to=8192, increment=128, textvariable=self.blocksize).grid(row=4, column=1, sticky="ew")

        # Manual overrides
        ttk.Label(frame, text="Pitch shift (st)").grid(row=5, column=0, sticky="w")
        self.pitch = tk.DoubleVar(value=0.0)
        ttk.Spinbox(frame, from_=-12, to=12, increment=0.5, textvariable=self.pitch).grid(row=5, column=1, sticky="ew")

        self.autotune_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Autotune (C major)", variable=self.autotune_var).grid(row=6, column=0, columnspan=2, sticky="w")

        ttk.Label(frame, text="Vibrato depth (st)").grid(row=7, column=0, sticky="w")
        self.vib_depth = tk.DoubleVar(value=0.0)
        ttk.Spinbox(frame, from_=0, to=6, increment=0.1, textvariable=self.vib_depth).grid(row=7, column=1, sticky="ew")
        ttk.Label(frame, text="Vibrato rate (Hz)").grid(row=8, column=0, sticky="w")
        self.vib_rate = tk.DoubleVar(value=5.0)
        ttk.Spinbox(frame, from_=0.1, to=12, increment=0.1, textvariable=self.vib_rate).grid(row=8, column=1, sticky="ew")

        ttk.Label(frame, text="Bitcrush bits").grid(row=9, column=0, sticky="w")
        self.bits = tk.IntVar(value=8)
        ttk.Spinbox(frame, from_=2, to=12, increment=1, textvariable=self.bits).grid(row=9, column=1, sticky="ew")

        ttk.Label(frame, text="Downsample factor").grid(row=10, column=0, sticky="w")
        self.downsample = tk.IntVar(value=1)
        ttk.Spinbox(frame, from_=1, to=8, increment=1, textvariable=self.downsample).grid(row=10, column=1, sticky="ew")

        ttk.Label(frame, text="Volume gain (dB)").grid(row=11, column=0, sticky="w")
        self.gain = tk.DoubleVar(value=0.0)
        ttk.Spinbox(frame, from_=-12, to=12, increment=0.5, textvariable=self.gain).grid(row=11, column=1, sticky="ew")

        # Buttons and status
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=12, column=0, columnspan=2, pady=8)
        ttk.Button(btn_frame, text="Start", command=self.start).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Stop", command=self.stop).pack(side="left", padx=4)
        self.status = ttk.Label(frame, text="Idle")
        self.status.grid(row=13, column=0, columnspan=2, sticky="w")

        for i in range(2):
            frame.columnconfigure(i, weight=1)

    def start(self):
        if self.processor:
            return
        try:
            in_idx = int(self.input_var.get().split(":")[0])
            out_idx = int(self.output_var.get().split(":")[0])
            preset = dict(PRESETS[self.preset_var.get()])
            # Manual overrides
            preset["pitch_shift_semitones"] = self.pitch.get()
            if self.autotune_var.get():
                preset["autotune"] = True
            preset["vibrato_depth_semitones"] = self.vib_depth.get()
            preset["vibrato_hz"] = self.vib_rate.get()
            preset["bitcrush_bits"] = self.bits.get()
            preset["downsample_factor"] = self.downsample.get()
            preset["volume_db"] = self.gain.get()

            drywet = float(np.clip(self.drywet.get(), 0.0, 1.0))
            blocksize = int(self.blocksize.get())
            self.vibrato_phase = 0.0

            def process_frame(mono: np.ndarray, sr: float):
                out = mono
                if preset.get("autotune"):
                    out = simple_autotune(out, int(sr), key=preset.get("key", "C"), scale=preset.get("scale", "major"))
                else:
                    out = pitch_shift(out, int(sr), preset.get("pitch_shift_semitones", 0))
                out = apply_downsample(out, int(preset.get("downsample_factor", 1)))
                depth = float(preset.get("vibrato_depth_semitones", 0.0))
                rate = float(preset.get("vibrato_hz", 5.0))
                base = float(preset.get("pitch_shift_semitones", 0.0))
                if depth > 0:
                    out, self.vibrato_phase = apply_vibrato(out, int(sr), depth, rate, base_semitones=base, phase=self.vibrato_phase)
                if "bitcrush_bits" in preset:
                    out = apply_bitcrush(out, int(preset["bitcrush_bits"]))
                if "volume_db" in preset:
                    out = apply_gain_db(out, float(preset["volume_db"]))
                blended = (1 - drywet) * mono + drywet * out
                return blended.astype(np.float32)

            self.processor = RealTimeProcessor(
                process_fn=process_frame,
                input_device=in_idx,
                output_device=out_idx,
                samplerate=48_000,
                blocksize=blocksize,
                channels=2,
            )
            self.processor.start()
            self.status.config(text="Running")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status.config(text="Error")

    def stop(self):
        if self.processor:
            self.processor.stop()
            self.processor = None
        self.status.config(text="Stopped")

    def destroy(self):
        self.stop()
        super().destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
