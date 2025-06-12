#!/usr/bin/env bash

echo "Worker Initiated"

# ===[ STEP 1: Download LoRA models from Hugging Face ]===
echo "Downloading LoRA models from Hugging Face..."
mkdir -p /stable-diffusion-webui/models/Lora

# LoRA model list
declare -a LORAS=(
  "3d_animation"
  "block_world"
  "clay_animation"
  "geometric"
  "paper_cutout"
  "picture_book"
  "soft_anime"
  "whimsical_watercolor"
)

for model in "${LORAS[@]}"; do
  echo "Downloading $model.safetensors"
  if wget --header="Authorization: Bearer $HUGGINGFACE_TOKEN" \
    "https://huggingface.co/SouthDistrict/storybook-models/resolve/main/Lora/${model}.safetensors" \
    -O "/stable-diffusion-webui/models/Lora/${model}.safetensors"; then
    echo "✓ ${model}.safetensors downloaded successfully"
  else
    echo "✗ ${model}.safetensors download failed"
  fi
done

echo "All LoRA models download attempts completed."

# ===[ STEP 2: Start WebUI API ]===
echo "Starting WebUI API with proper parameters..."
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"
export PYTHONUNBUFFERED=true

# Change to WebUI directory
cd /stable-diffusion-webui

# Start WebUI with corrected parameters
python webui.py \
  --api \
  --listen \
  --port 3000 \
  --skip-torch-cuda-test \
  --no-browser \
  --xformers \
  --no-half-vae \
  --skip-python-version-check \
  --skip-install \
  --ckpt /model.safetensors \
  --opt-sdp-attention \
  --disable-safe-unpickle \
  --nowebui \
  --skip-version-check \
  --no-hashing \
  --no-download-sd-model &

# Wait a moment for WebUI to start
sleep 5

# ===[ STEP 3: Start RunPod Handler ]===
echo "Starting RunPod Handler"
python -u /handler.py