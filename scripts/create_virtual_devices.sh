#!/usr/bin/env bash
# Create PulseAudio null sink + virtual source for the VoiceModL pipeline.
# Idempotent: if a module is already loaded, we skip creating duplicates.

set -euo pipefail

SINK_NAME=${SINK_NAME:-VoiceModSink}
SOURCE_NAME=${SOURCE_NAME:-VoiceModSource}

load_once() {
  local module="$1"; shift
  local args=("$@")
  if pactl list short modules | grep -q "${module}.*${SINK_NAME}"; then
    echo "[skip] ${module} with name ${SINK_NAME} already loaded"
    return 0
  fi
  if pactl list short modules | grep -q "${module}.*${SOURCE_NAME}"; then
    echo "[skip] ${module} with name ${SOURCE_NAME} already loaded"
    return 0
  fi
  echo "[load] pactl load-module ${module} ${args[*]}"
  pactl load-module "${module}" "${args[@]}"
}

load_once module-null-sink \
  sink_name=${SINK_NAME} \
  sink_properties=device.description="VoiceMod Processing Sink"

load_once module-virtual-source \
  source_name=${SOURCE_NAME} \
  master=${SINK_NAME}.monitor \
  source_properties=device.description="VoiceMod Microphone"

echo "[info] Current PulseAudio sinks:" && pactl list short sinks
echo "[info] Current PulseAudio sources:" && pactl list short sources

cat <<'EOF'
Use cases:
- Select '${SOURCE_NAME}' as mic in Discord/Zoom/etc.
- Route processed audio to ${SINK_NAME}; its monitor feeds the virtual mic.
Optional monitoring: load module-loopback with source=${SOURCE_NAME}.monitor.
EOF
