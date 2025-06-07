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
  wget --header="Authorization: Bearer $HUGGINGFACE_TOKEN" \
    "https://huggingface.co/SouthDistrict/storybook-models/resolve/main/Lora/${model}.safetensors" \
    -O "/stable-diffusion-webui/models/Lora/${model}.safetensors"
done

echo "All LoRA models downloaded."

# ===[ STEP 2: Start WebUI API ]===
echo "Starting WebUI API"
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"
export PYTHONUNBUFFERED=true
python /stable-diffusion-webui/webui.py \
  --xformers \
  --no-half-vae \
  --skip-python-version-check \
  --skip-torch-cuda-test \
  --skip-install \
  --ckpt /model.safetensors \
  --opt-sdp-attention \
  --disable-safe-unpickle \
  --port 3000 \
  --api \
  --nowebui \
  --skip-version-check \
  --no-hashing \
  --no-download-sd-model &

# ===[ STEP 3: Start RunPod Handler ]===
echo "Starting RunPod Handler"
python -u /handler.py