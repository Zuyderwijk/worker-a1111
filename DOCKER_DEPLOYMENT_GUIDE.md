# Docker Deployment Guide for RunPod

## 🎯 Overview

This guide shows how to build your custom worker with LoRAs on your Mac and deploy it to RunPod.

## 📋 Prerequisites

1. **Docker Desktop** with buildx enabled ✅ (you have this)
2. **Docker Hub account** (free)
3. **Your RunPod endpoint** (existing)

## 🚀 Step-by-Step Deployment

### **Step 1: Docker Hub Setup**

1. Create account at https://hub.docker.com (if needed)
2. Login locally:
```bash
docker login
```

### **Step 2: Configure Build Script**

Edit `build-for-runpod.sh` and replace `your-username` with your Docker Hub username:

```bash
DOCKER_USERNAME="your-actual-username"  # Replace this!
```

### **Step 3: Build and Push**

Run the build script:
```bash
./build-for-runpod.sh
```

This will:
- ✅ Build for x86_64 architecture (RunPod's platform)
- ✅ Include your LoRA models and custom handler
- ✅ Push to Docker Hub automatically
- ✅ Work on RunPod GPUs

### **Step 4: Update RunPod Endpoint**

1. Go to your RunPod dashboard
2. Edit your endpoint
3. Change Docker Image to: `your-username/vertelmoment-worker:latest`
4. Set Container Disk to **50 GB**
5. Add environment variables:
```
HUGGINGFACE_TOKEN=your_token_here
```
6. Save changes

### **Step 5: Test Deployment**

1. Terminate unhealthy workers
2. Scale up 1 new worker
3. Monitor logs for successful startup
4. Test image generation

## 🔧 Alternative: GitHub Actions (Automated)

For automated builds on every code change:

1. Push your code to GitHub
2. Add these secrets in GitHub repository settings:
   - `DOCKER_USERNAME`: Your Docker Hub username
   - `DOCKER_PASSWORD`: Your Docker Hub token
3. GitHub will build and push automatically

## 🛠️ Build Environments

### **Local (Mac) - Cross Platform Build**
- ✅ Builds x86_64 from ARM64 Mac
- ✅ Uses Docker buildx
- ✅ Fast and reliable

### **GitHub Actions**
- ✅ Free Linux build environment
- ✅ Automatic on code changes
- ✅ No local resources needed

### **Cloud Build**
- ✅ Google Cloud Build
- ✅ AWS CodeBuild
- ✅ Professional CI/CD

## 💡 Benefits of Custom Image

✅ **Your LoRA Models**: All 8 style models included
✅ **Custom Handler**: Dynamic book format logic
✅ **Optimized Startup**: Models pre-downloaded
✅ **Reliable**: Built for correct architecture
✅ **Version Control**: Track changes and rollback

## 🔍 Troubleshooting

### **Build Issues**
```bash
# Check buildx
docker buildx version

# Check available builders
docker buildx ls

# Reset builder if needed
docker buildx rm runpod-builder
docker buildx create --name runpod-builder --use
```

### **Push Issues**
```bash
# Re-login to Docker Hub
docker logout
docker login

# Check image exists
docker images | grep vertelmoment
```

### **RunPod Issues**
- Ensure 50GB container disk space
- Check environment variables are set
- Monitor worker logs for startup errors
- Verify image name matches exactly

## 🎊 Success!

Once deployed, your custom worker will:
- Download and cache LoRA models on startup
- Support all your dynamic book formats
- Generate images with proper Lulu dimensions
- Handle style-specific optimizations

Your image generation will be faster and more reliable than the default RunPod setup!
