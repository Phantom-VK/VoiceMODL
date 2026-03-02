"""Minimal Tkinter GUI for VoiceModL (no external GUI deps).

Run: python -m src.gui_tk
"""

from __future__ import annotations

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
        style = ttk.Style()
        try:
            style.configure("TLabel", font=("Sans", 11))
            style.configure("TButton", font=("Sans", 11))
            style.configure("TCombobox", font=("Sans", 11))
        except Exception:
            pass

        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)

        # Devices
        ttk.Label(frame, text="Input device").grid(row=0, column=0, sticky="w")
        self.input_var = tk.StringVar()
        ttk.Label(frame, text="Output device").grid(row=1, column=0, sticky="w")
        self.output_var = tk.StringVar()

        devices = list_devices()
        # Prefer pulse/default devices; otherwise first with inputs/outputs
        choices = []
        default_in_idx = None
        default_out_idx = None
        for d in devices:
            if d.max_input_channels > 0:
                choices.append(f"{d.index}:{d.name}")
                if default_in_idx is None and ("pulse" in d.name.lower() or "default" in d.name.lower()):
                    default_in_idx = len(choices) - 1
            elif d.max_output_channels > 0:
                choices.append(f"{d.index}:{d.name}")
            if d.max_output_channels > 0 and default_out_idx is None and ("pulse" in d.name.lower() or "default" in d.name.lower()):
                default_out_idx = len(choices) - 1
        if not choices:
            choices = ["0:default"]
        self.input_box = ttk.Combobox(frame, textvariable=self.input_var, values=choices, state="readonly")
        self.output_box = ttk.Combobox(frame, textvariable=self.output_var, values=choices, state="readonly")
        self.input_box.grid(row=0, column=1, sticky="ew")
        self.output_box.grid(row=1, column=1, sticky="ew")
        self.input_box.current(default_in_idx if default_in_idx is not None else 0)
        self.output_box.current(default_out_idx if default_out_idx is not None else 0)

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

        # Buttons and status
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=8)
        ttk.Button(btn_frame, text="Start", command=self.start, width=10).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Stop", command=self.stop, width=10).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Reset", command=self.reset_fields, width=10).pack(side="left", padx=6)
        self.status = ttk.Label(frame, text="Idle")
        self.status.grid(row=6, column=0, columnspan=2, sticky="w")

        for i in range(2):
            frame.columnconfigure(i, weight=1)

    def start(self):
        if self.processor:
            return
        try:
            in_idx = int(self.input_var.get().split(":")[0])
            out_idx = int(self.output_var.get().split(":")[0])
            # Clamp channels to device capabilities
            in_dev = next((d for d in list_devices() if d.index == in_idx), None)
            out_dev = next((d for d in list_devices() if d.index == out_idx), None)
            if not in_dev or in_dev.max_input_channels < 1:
                raise RuntimeError("Selected input has no channels; pick another device.")
            if not out_dev or out_dev.max_output_channels < 1:
                raise RuntimeError("Selected output has no channels; pick another device.")
            max_ch = max(1, min(in_dev.max_input_channels or 1, out_dev.max_output_channels or 1))
            channels = min(2, max_ch)
            preset = dict(PRESETS[self.preset_var.get()])

            drywet = float(np.clip(self.drywet.get(), 0.0, 1.0))
            blocksize = int(self.blocksize.get())
            self.vibrato_phase = 0.0

            def process_frame(mono: np.ndarray, sr: float):
                out = mono
                if preset.get("autotune"):
                    out, _ = simple_autotune(
                        out,
                        int(sr),
                        key=preset.get("key", "C"),
                        scale=preset.get("scale", "major"),
                        retune_strength=float(preset.get("retune_strength", 1.0)),
                        last_midi=None,
                    )
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
                channels=channels,
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

    def reset_fields(self):
        # Reset to defaults/preset defaults
        self.drywet.set(1.0)
        self.blocksize.set(2048)
        # Keep current devices and preset selection
        self.status.config(text="Idle")

    def destroy(self):
        self.stop()
        super().destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
