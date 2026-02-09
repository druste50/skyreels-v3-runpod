# SkyReels-V3 RunPod Serverless Worker

Deploy SkyReels-V3 Talking Avatar as a RunPod Serverless Endpoint.
Pay only when generating videos — no idle costs.

## 🚀 Setup (Step by Step)

### Step 1: Create a Network Volume on RunPod

1. Go to [RunPod Console](https://www.runpod.io/console/user/storage) → **Storage**
2. Click **Create Network Volume**
3. Choose a region (e.g., `US-TX-3`) and **100 GB** size
4. Name it `skyreels-models`

### Step 2: Download Models to Network Volume

Create a temporary GPU Pod to download the model:

1. Go to **Pods** → **Deploy**
2. Use template: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`
3. Attach your `skyreels-models` Network Volume
4. Select a cheap GPU (e.g., RTX 3090)
5. Start the Pod and open the **Terminal**

Run these commands in the Pod terminal:

```bash
# Install huggingface CLI
pip install huggingface_hub[cli]

# Create models directory
mkdir -p /runpod-volume/models

# Download SkyReels-V3 A2V model (~40GB)
huggingface-cli download Skywork/SkyReels-V3-A2V-19B \
  --local-dir /runpod-volume/models/SkyReels-V3-A2V-19B

# Verify download
ls -la /runpod-volume/models/SkyReels-V3-A2V-19B/

# Done! Stop the Pod to save money.
```

### Step 3: Build & Push Docker Image

On your local machine (requires Docker installed):

```bash
# Navigate to the docker folder
cd skyreels-v3-runpod

# Build the image
docker build -t YOUR_DOCKERHUB_USERNAME/skyreels-v3-runpod:latest .

# Login to Docker Hub
docker login

# Push the image
docker push YOUR_DOCKERHUB_USERNAME/skyreels-v3-runpod:latest
```

> Replace `YOUR_DOCKERHUB_USERNAME` with your actual Docker Hub username.

### Step 4: Create Serverless Endpoint

1. Go to [RunPod Console](https://www.runpod.io/console/serverless) → **Serverless**
2. Click **New Endpoint**
3. Fill in:
   - **Name:** `SkyReels-V3-Avatar`
   - **Docker Image:** `YOUR_DOCKERHUB_USERNAME/skyreels-v3-runpod:latest`
   - **GPU Type:** **H100** (recommended) or RTX 4090
   - **Network Volume:** Select `skyreels-models`
   - **Max Workers:** 3
   - **Idle Timeout:** 60 seconds
4. Click **Create Endpoint**
5. Copy the **Endpoint ID** (e.g., `abc123xyz`)

### Step 5: Update Your App

Update the RunPod endpoint in your Supabase secrets:

```bash
# Set the new endpoint ID in Supabase
supabase secrets set SKYREELS_ENDPOINT_ID=abc123xyz
```

---

## 📡 API Reference

### Input

```json
{
  "input": {
    "image_base64": "base64_encoded_image",
    "audio_base64": "base64_encoded_audio",
    "prompt": "A person is talking naturally",
    "resolution": "720P",
    "seed": 42
  }
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `image_base64` | string | Yes* | - | Base64 encoded portrait image |
| `image_url` | string | Yes* | - | URL to portrait image |
| `audio_base64` / `wav_base64` | string | Yes* | - | Base64 encoded audio (WAV/MP3) |
| `audio_url` | string | Yes* | - | URL to audio file |
| `prompt` | string | No | "A person is talking naturally" | Scene description |
| `resolution` | string | No | "720P" | "480P", "540P", or "720P" |
| `seed` | int | No | 42 | Random seed |
| `low_vram` | bool | No | false | Enable for GPUs < 24GB |

*Either base64 or URL must be provided for image and audio.

### Output (Success)

```json
{
  "status": "success",
  "video_base64": "base64_encoded_mp4_video",
  "filename": "skyreels_<uuid>.mp4",
  "resolution": "720P"
}
```

### Output (Error)

```json
{
  "error": "Error description",
  "stdout": "...",
  "stderr": "..."
}
```

---

## 💰 Cost Estimate

| GPU | ~Time (15s video, 720p) | Cost/hr | Cost per video |
|-----|------------------------|---------|----------------|
| RTX 4090 | ~8-12 min | ~$0.69 | ~$0.09-0.14 |
| H100 SXM | ~2-4 min | ~$3.99 | ~$0.13-0.27 |

H100 is faster per video but higher hourly rate. For short videos, costs are similar.
