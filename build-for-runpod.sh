#!/bin/bash

# Cross-platform Docker build script for RunPod deployment
# This builds an x86_64 image from Apple Silicon Mac

set -e

echo "🐳 Building Docker image for RunPod (x86_64 architecture)..."

# Your Docker Hub username  
DOCKER_USERNAME="southdistrict"  # Your Docker Hub username
IMAGE_NAME="vertelmoment-worker"
TAG="latest"
FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"

# Check if Docker buildx is available
if ! docker buildx version > /dev/null 2>&1; then
    echo "❌ Docker buildx not available. Please update Docker Desktop."
    exit 1
fi

# Create and use a new builder instance
echo "🔧 Setting up cross-platform builder..."
docker buildx create --name runpod-builder --use 2>/dev/null || docker buildx use runpod-builder

# Build for x86_64 platform (RunPod's architecture)
echo "🏗️  Building image for linux/amd64 platform..."
docker buildx build \
    --platform linux/amd64 \
    --tag ${FULL_IMAGE_NAME} \
    --push \
    .

echo "✅ Image built and pushed successfully!"
echo "📝 Use this image in RunPod: ${FULL_IMAGE_NAME}"
echo ""
echo "🚀 Next steps:"
echo "1. Go to RunPod dashboard"
echo "2. Edit your endpoint"
echo "3. Set Docker Image to: ${FULL_IMAGE_NAME}"
echo "4. Save and restart workers"
