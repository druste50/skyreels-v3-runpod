#!/bin/bash
set -e

echo "============================================"
echo " SkyReels-V3 RunPod Serverless Worker"
echo "============================================"

# Check if models are available on Network Volume
MODEL_DIR="${MODEL_DIR:-/runpod-volume/models}"
MODEL_PATH="$MODEL_DIR/SkyReels-V3-A2V-19B"

if [ -d "$MODEL_PATH" ]; then
    echo "[START] Models found at $MODEL_PATH"
else
    echo "[START] WARNING: Models NOT found at $MODEL_PATH"
    echo "[START] Models will be downloaded from HuggingFace on first request (slow cold start)"
    echo "[START] Recommendation: Create a Network Volume and pre-download models"
fi

# Set HuggingFace cache to Network Volume
export HF_HOME="${HF_HOME:-/runpod-volume/huggingface}"
mkdir -p "$HF_HOME" 2>/dev/null || true

# CUDA optimization
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"

echo "[START] Starting handler..."
exec python3 /app/handler.py
