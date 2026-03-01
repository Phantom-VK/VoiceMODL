# VoiceModL (POC)

Real-time voice changer for Linux using PulseAudio/PipeWire virtual devices.

## Quick start

1) Create virtual devices (once per session):
```bash
bash scripts/create_virtual_devices.sh
```

2) Activate env:
```bash
source .venv/bin/activate
```

3) List devices:
```bash
python -m src.main --list
```

4) Run demo (adjust indices from step 3):
```bash
python -m src.main --input 12 --output 12 --samplerate 48000 --blocksize 2048 --preset tpain --drywet 1.0
```

Or use the helper script (env vars override defaults):
```bash
INPUT_DEV=12 OUTPUT_DEV=12 PRESET=tpain bash scripts/run_voicemod_demo.sh
```

5) In your VOIP app, select microphone: `VoiceModSource`.

## GUI (experimental)
Two options:

1) Tk (no extra deps):  
```bash
source .venv/bin/activate
python -m src.gui_tk
```

2) GTK (needs system `python3-gi`):  
```bash
python -m src.gui   # if python3-gi is installed
```
Both show device selectors, preset dropdown, and manual tweaks (pitch, vibrato, bitcrush, downsample, gain, dry/wet).

## Presets

Editable in `configs/presets.json` and mirrored in `src/presets.py` for now.

## Known tips
- If you see underruns, increase `--blocksize` (e.g., 4096) or ensure the Python stream is routed to `VoiceModSink` via `pavucontrol`.
- `--drywet` lets you blend processed/dry signal (1.0 = fully processed).
