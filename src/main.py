"""CLI entrypoint for Phase 2: list devices or run pass-through.

Examples:
  python -m src.main --list
  python -m src.main --input 2 --output 5 --samplerate 48000 --blocksize 1024
"""

from __future__ import annotations

import argparse
import contextlib
import time
from typing import Optional

from .audio_io import (
    create_passthrough_stream,
    default_io_devices,
    format_device,
    list_devices,
)
from .dsp_core import pitch_shift, simple_autotune
from .presets import PRESETS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VoiceModL phase-2 passthrough")
    parser.add_argument("--list", action="store_true", help="List audio devices and exit")
    parser.add_argument("--input", type=int, default=None, help="Input device index")
    parser.add_argument("--output", type=int, default=None, help="Output device index")
    parser.add_argument("--samplerate", type=float, default=48_000, help="Sample rate (Hz)")
    parser.add_argument("--blocksize", type=int, default=1024, help="Frames per block")
    parser.add_argument("--channels", type=int, default=1, help="Number of channels (1=mono,2=stereo)")
    parser.add_argument("--preset", type=str, default="normal", choices=list(PRESETS.keys()))
    return parser.parse_args()


def cmd_list_devices() -> None:
    for dev in list_devices():
        print(format_device(dev))


def cmd_passthrough(args: argparse.Namespace) -> None:
    in_dev = args.input
    out_dev = args.output
    if in_dev is None or out_dev is None:
        in_default, out_default = default_io_devices()
        in_dev = in_default if in_dev is None else in_dev
        out_dev = out_default if out_dev is None else out_dev
        print(f"[info] Using defaults input={in_dev} output={out_dev}")

    preset = PRESETS[args.preset]

    def process_frame(frame, sr: float) -> Optional[object]:
        # frame: (frames, channels) float32
        mono = frame[:, 0]
        if preset.get("autotune"):
            out = simple_autotune(mono, int(sr), key=preset.get("key", "C"), scale=preset.get("scale", "major"))
        else:
            out = pitch_shift(mono, int(sr), preset.get("pitch_shift_semitones", 0))
        # return mono; audio_io will handle channel duplication
        return out.astype(frame.dtype)

    stream = create_passthrough_stream(
        input_device=in_dev,
        output_device=out_dev,
        samplerate=args.samplerate,
        blocksize=args.blocksize,
        channels=args.channels,
        process_fn=process_frame,
    )

    print("[info] Starting pass-through. Ctrl+C to stop.")
    with contextlib.ExitStack() as stack:
        stack.enter_context(stream)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[info] Stopping.")


def main() -> None:
    args = parse_args()
    if args.list:
        cmd_list_devices()
        return
    cmd_passthrough(args)


if __name__ == "__main__":
    main()
