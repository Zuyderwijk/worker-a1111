#!/bin/bash

echo "[INFO] Downloading LoRA models from Hugging Face..."

# Create LoRA directory
mkdir -p /workspace/stable-diffusion-webui/models/Lora

# Base URL for SouthDistrict/storybook-models
BASE_URL="https://huggingface.co/SouthDistrict/storybook-models/resolve/main/Lora"
LORA_DIR="/workspace/stable-diffusion-webui/models/Lora"

# Array of all available LoRA models
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

# Function to download a single LoRA
download_lora() {
  local lora_name=$1
  local filename="${lora_name}.safetensors"
  local url="${BASE_URL}/${filename}"
  local output_path="${LORA_DIR}/${filename}"
  
  echo "[INFO] Downloading ${filename}..."
  
  if [ -f "$output_path" ]; then
    echo "[SKIP] ${filename} already exists"
    return 0
  fi
  
  if wget --header="Authorization: Bearer $HUGGINGFACE_TOKEN" \
    "$url" \
    -O "$output_path"; then
    echo "[SUCCESS] ${filename} downloaded successfully"
    return 0
  else
    echo "[ERROR] Failed to download ${filename}"
    return 1
  fi
}

# Download all LoRAs
successful_downloads=0
failed_downloads=0

for lora in "${LORAS[@]}"; do
  if download_lora "$lora"; then
    ((successful_downloads++))
  else
    ((failed_downloads++))
  fi
done

# Summary
echo ""
echo "[SUMMARY] LoRA download completed:"
echo "  - Successful: ${successful_downloads}"
echo "  - Failed: ${failed_downloads}"
echo "  - Total: ${#LORAS[@]}"

# List downloaded files
echo ""
echo "[INFO] Downloaded LoRA files:"
ls -la "$LORA_DIR"/*.safetensors 2>/dev/null || echo "No LoRA files found"

# Verify all expected files are present
echo ""
echo "[VERIFY] Checking all expected LoRAs:"
all_present=true
for lora in "${LORAS[@]}"; do
  filename="${lora}.safetensors"
  if [ -f "${LORA_DIR}/${filename}" ]; then
    size=$(du -h "${LORA_DIR}/${filename}" | cut -f1)
    echo "  ✓ ${filename} (${size})"
  else
    echo "  ✗ ${filename} - MISSING"
    all_present=false
  fi
done

if [ "$all_present" = true ]; then
  echo "[SUCCESS] All LoRA models are present and ready to use!"
  exit 0
else
  echo "[WARNING] Some LoRA models are missing. Check the download process."
  exit 1
fi