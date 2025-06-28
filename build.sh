#!/bin/bash

# Build script for RunPod compatible Docker image
set -e

# Configuration
IMAGE_NAME="vertelmoment/worker-a1111"
TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"

echo "🐳 Building Docker image for RunPod (linux/amd64)..."

# Check if we're on Apple Silicon and warn about cross-compilation
if [[ $(uname -m) == "arm64" ]]; then
    echo "⚠️  Building on Apple Silicon - this will take longer due to cross-compilation"
    echo "💡 Consider using GitHub Actions or a Linux machine for faster builds"
fi

# Build for linux/amd64 (RunPod's architecture)
docker buildx build \
    --platform linux/amd64 \
    --tag $FULL_IMAGE_NAME \
    --load \
    .

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "📦 Image: $FULL_IMAGE_NAME"
    
    # Show image info
    docker images $IMAGE_NAME:$TAG
    
    echo ""
    echo "🚀 Next steps:"
    echo "1. Test locally: docker run --rm -p 3000:3000 $FULL_IMAGE_NAME"
    echo "2. Push to registry: docker push $FULL_IMAGE_NAME"
    echo "3. Update RunPod endpoint to use: $FULL_IMAGE_NAME"
else
    echo "❌ Build failed!"
    exit 1
fi
