#!/usr/bin/env bash
# Download the local TTS model (Kokoro-82M ONNX, Apache-2.0) into models/. ~350 MB.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p models
base=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s "models/$f" ] || curl -fL --retry 4 -o "models/$f" "$base/$f"
done
echo "models ready"; ls -la models
