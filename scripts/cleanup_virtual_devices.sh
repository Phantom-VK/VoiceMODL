#!/usr/bin/env bash
# Unload VoiceModL PulseAudio/PipeWire modules.

set -euo pipefail

SINK_NAME=${SINK_NAME:-VoiceModSink}
SOURCE_NAME=${SOURCE_NAME:-VoiceModSource}

# Collect module IDs matching our names
ids=()
while read -r id type args; do
  case "$type" in
    module-null-sink)
      if echo "$args" | grep -q "sink_name=$SINK_NAME"; then ids+=("$id"); fi
      ;;
    module-virtual-source|module-remap-source)
      if echo "$args" | grep -q "source_name=$SOURCE_NAME"; then ids+=("$id"); fi
      ;;
    module-loopback)
      if echo "$args" | grep -q "$SOURCE_NAME"; then ids+=("$id"); fi
      ;;
  esac
done < <(pactl list short modules)

for id in "${ids[@]}"; do
  echo "[cleanup] unloading module id $id"
  pactl unload-module "$id" || true
done

echo "[cleanup] done"
