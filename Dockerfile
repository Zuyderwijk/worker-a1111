# ---------------------------------------------------------------------------- #
#                         Stage 1: Download the models                         #
# ---------------------------------------------------------------------------- #
FROM alpine/git:2.43.0 AS download

# Download the base model
RUN apk add --no-cache wget && \
    wget -q -O /model.safetensors https://huggingface.co/XpucT/Deliberate/resolve/main/Deliberate_v6.safetensors

# ---------------------------------------------------------------------------- #
#                        Stage 2: Build the final image                        #
# ---------------------------------------------------------------------------- #
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_PREFER_BINARY=1 \
    ROOT=/stable-diffusion-webui \
    PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    fonts-dejavu-core rsync git jq moreutils aria2 wget \
    libgoogle-perftools-dev libtcmalloc-minimal4 procps \
    libgl1 libglib2.0-0 libgoogle-perftools4 \
    build-essential && \
    apt-get autoremove -y && rm -rf /var/lib/apt/lists/* && apt-get clean -y

# Clone and setup Automatic1111 WebUI
RUN git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git ${ROOT} && \
    cd ${ROOT} && \
    git reset --hard ${A1111_RELEASE}

# Install Python dependencies 
WORKDIR ${ROOT}
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 && \
    pip install xformers==0.0.22.post7 --index-url https://download.pytorch.org/whl/cu118 && \
    pip install -r requirements_versions.txt

# Pre-download models and extensions
RUN python -c "from launch import prepare_environment; prepare_environment()" --skip-torch-cuda-test

# Copy the base model
COPY --from=download /model.safetensors /model.safetensors

# Install RunPod handler dependencies
COPY requirements.txt /requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /requirements.txt

# Copy our custom handler and scripts
COPY src/handler.py /handler.py
COPY src/start.sh /start.sh

# Make start script executable
RUN chmod +x /start.sh

# Set working directory back to root
WORKDIR /

# Expose the port
EXPOSE 3000

# Start the handler
CMD ["/start.sh"]