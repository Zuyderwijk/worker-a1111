#!/usr/bin/env bash

echo "Worker starting up..."

# ===[ DEBUG: Check environment variables ]===
echo "=== ENVIRONMENT DEBUG ==="
echo "HUGGINGFACE_TOKEN is set: ${HUGGINGFACE_TOKEN:+YES}"
echo "HUGGINGFACE_TOKEN length: ${#HUGGINGFACE_TOKEN}"
if [ -n "$HUGGINGFACE_TOKEN" ]; then
    echo "HUGGINGFACE_TOKEN first 10 chars: ${HUGGINGFACE_TOKEN:0:10}..."
else
    echo "❌ HUGGINGFACE_TOKEN is NOT set!"
fi

echo "HF_TOKEN is set: ${HF_TOKEN:+YES}"
echo "HUGGING_FACE_API_TOKEN is set: ${HUGGING_FACE_API_TOKEN:+YES}"

echo "All environment variables with 'HF' or 'TOKEN':"
env | grep -iE "(hf|token)" | head -10 || echo "None found"
echo "=========================="

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
  
  # Try multiple token sources in order of preference
  TOKEN=""
  TOKEN_SOURCE=""
  
  if [ -n "$HUGGINGFACE_TOKEN" ]; then
    TOKEN="$HUGGINGFACE_TOKEN"
    TOKEN_SOURCE="HUGGINGFACE_TOKEN"
  elif [ -n "$HF_TOKEN" ]; then
    TOKEN="$HF_TOKEN" 
    TOKEN_SOURCE="HF_TOKEN"
  elif [ -n "$HUGGING_FACE_API_TOKEN" ]; then
    TOKEN="$HUGGING_FACE_API_TOKEN"
    TOKEN_SOURCE="HUGGING_FACE_API_TOKEN"
  else
    echo "❌ No Hugging Face token found!"
    echo "Checked: HUGGINGFACE_TOKEN, HF_TOKEN, HUGGING_FACE_API_TOKEN"
    echo "Available environment variables containing 'TOKEN' or 'HF':"
    env | grep -iE "(token|hf)" | head -5 || echo "None found"
    echo "⚠️ Skipping LoRA downloads - worker will use base model only"
    break
  fi
  
  echo "Using token from: $TOKEN_SOURCE (${TOKEN:0:10}...)"
  
  if wget --header="Authorization: Bearer $TOKEN" \
    "https://huggingface.co/SouthDistrict/storybook-models/resolve/main/Lora/${model}.safetensors" \
    -O "/stable-diffusion-webui/models/Lora/${model}.safetensors"; then
    echo "✓ ${model}.safetensors downloaded successfully"
  else
    echo "✗ ${model}.safetensors download failed (401 = token issue, 404 = file not found)"
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
echo "Starting WebUI on port 3000..."
python webui.py \
  --api \
  --listen \
  --port 3000 \
  --skip-torch-cuda-test \
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
  --no-download-sd-model \
  --api-log &

# Wait longer for WebUI to fully start
echo "Waiting for WebUI to start..."
sleep 15

# Check if WebUI is responding
echo "Checking WebUI status..."
for i in {1..30}; do
  if curl -s http://127.0.0.1:3000/sdapi/v1/txt2img > /dev/null 2>&1; then
    echo "✓ WebUI is ready!"
    break
  else
    echo "Waiting for WebUI... attempt $i/30"
    sleep 2
  fi
done

# ===[ STEP 3: Start RunPod Handler ]===
echo "Starting RunPod Handler"
python -u /handler.py