# SkyReels-V3 RunPod Serverless Worker
# Optimized for H100 GPU with CUDA 12.4

FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    git \
    wget \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Upgrade pip
RUN python3 -m pip install --upgrade pip setuptools wheel

# Clone SkyReels-V3
WORKDIR /app
RUN git clone https://github.com/SkyworkAI/SkyReels-V3.git /app/SkyReels-V3

# Install SkyReels-V3 dependencies
WORKDIR /app/SkyReels-V3
RUN pip install -r requirements.txt

# Install RunPod serverless SDK
RUN pip install runpod requests

# Copy handler and entrypoint
COPY handler.py /app/handler.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Default model path (Network Volume will be mounted here)
ENV MODEL_DIR=/runpod-volume/models
ENV HF_HOME=/runpod-volume/huggingface

WORKDIR /app

CMD ["/app/start.sh"]
