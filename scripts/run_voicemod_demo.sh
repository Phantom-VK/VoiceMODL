#!/usr/bin/env bash
# Launch VoiceModL demo with sane defaults. Assumes PulseAudio/PipeWire virtual
# devices already exist (VoiceModSink/VoiceModSource).

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
source "${PROJECT_ROOT}/.venv/bin/activate"

INPUT_DEV=${INPUT_DEV:-12}
OUTPUT_DEV=${OUTPUT_DEV:-12}
SAMPLERATE=${SAMPLERATE:-48000}
BLOCKSIZE=${BLOCKSIZE:-2048}
PRESET=${PRESET:-tpain}

echo "[demo] input=${INPUT_DEV} output=${OUTPUT_DEV} sr=${SAMPLERATE} block=${BLOCKSIZE} preset=${PRESET}"
exec python -m src.main \
  --input "${INPUT_DEV}" \
  --output "${OUTPUT_DEV}" \
  --samplerate "${SAMPLERATE}" \
  --blocksize "${BLOCKSIZE}" \
  --preset "${PRESET}"
