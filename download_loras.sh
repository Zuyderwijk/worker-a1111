#!/bin/bash

echo "[INFO] Downloading LoRA models from Hugging Face..."

mkdir -p /workspace/stable-diffusion-webui/models/Lora

# Example for one LoRA model
wget --header="Authorization: Bearer $HUGGINGFACE_TOKEN" \
  https://huggingface.co/SouthDistrict/storybook-models/resolve/main/Lora/picture_book.safetensors \
  -O /workspace/stable-diffusion-webui/models/Lora/picture_book.safetensors

echo "[INFO] All LoRA models downloaded."