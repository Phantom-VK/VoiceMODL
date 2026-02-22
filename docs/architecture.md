# VoiceModL Architecture

## High-level flow

```mermaid
flowchart LR
    Mic[Physical Mic] -->|Pulse/ALSA capture| InDev[pulse/alsa input index]
    InDev --> RTProc[RealTimeProcessor\n(queue + worker thread)]
    RTProc --> DSP[dsp_core.py\n pitch_shift / autotune]
    DSP --> RTProc
    RTProc --> Sink[VoiceModSink (null sink)]
    Sink --> VSource[VoiceModSource (virtual mic)]
    VSource --> Apps[Discord/Zoom/OBS]
    Sink -. monitor .-> Monitor[Optional loopback to headphones]
```

## Components

- **PulseAudio/PipeWire routing**: `scripts/create_virtual_devices.sh` sets up `VoiceModSink` (null sink) and `VoiceModSource` (virtual mic attached to the sink monitor). Apps select `VoiceModSource` as the mic.
- **Audio I/O** (`src/audio_io.py`): uses `sounddevice` to read from selected input device and write to output device. `RealTimeProcessor` keeps the callback light by pushing frames through queues to a worker thread.
- **DSP** (`src/dsp_core.py`): per-frame processing
  - `pitch_shift`: librosa pitch shift (light resampler)
  - `simple_autotune`: f0 via pyin → snap to scale → pitch shift
  - Clamps output to [-1,1]
- **CLI** (`src/main.py`): chooses devices, preset, blocksize, dry/wet mix; starts the RT processor.
- **Presets** (`src/presets.py`, `configs/presets.json`): named effect settings (pitch offsets, autotune key/scale).
- **Helper scripts**: `run_voicemod_demo.sh` bootstraps the run with env overrides.

## Threading model

```mermaid
sequenceDiagram
    participant ALSA/Pulse as Sounddevice Callback
    participant InQ as Input Queue
    participant Worker as DSP Worker Thread
    participant OutQ as Output Queue
    participant SD as Sounddevice Output

    ALSA/Pulse->>InQ: push input frame (non-blocking)
    Worker->>InQ: get frame (blocking)
    Worker->>Worker: mono extract + DSP (pitch/autotune)
    Worker->>OutQ: push processed frame (non-blocking)
    ALSA/Pulse->>OutQ: pop processed frame (non-blocking)
    ALSA/Pulse->>SD: write to output buffer
    Note over ALSA/Pulse,OutQ: If OutQ empty → zero frame; stats underrun++
    Note over InQ: If full → drop frame; stats dropped_in++
```

## Routing specifics (PulseAudio/PipeWire)

1. `VoiceModSink` is a null sink that receives processed audio.
2. `VoiceModSource` is a virtual source whose master is `VoiceModSink.monitor`; apps see it as a microphone.
3. Optionally load `module-loopback` to monitor `VoiceModSource.monitor` in headphones for self-monitoring.
4. Use `pavucontrol` to move the Python playback stream to `VoiceModSink` if needed.

## Latency knobs

- `--blocksize`: larger = safer/fewer XRUNs, higher latency (start 2048–4096).
- `--samplerate`: 48 kHz recommended to match Pulse defaults.
- DSP cost: autotune heavier than fixed pitch shift; use `--preset female/male` for lighter load.

## Dry/Wet mixing

- CLI flag `--drywet` blends processed audio with original mono frame (0=dry, 1=wet). Implemented in `src/main.py` before channel duplication.

## Stats and logging

- `RealTimeProcessor.stats`: `dropped_in` (input queue full) and `underrun_out` (no processed frame ready). Printed on Ctrl+C exit.
- Warnings suppressed when pyin sees silence (returns NaN f0).

