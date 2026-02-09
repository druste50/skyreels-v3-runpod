"""
SkyReels-V3 Talking Avatar - RunPod Serverless Handler
Receives image + audio (base64 or URL) and generates a talking avatar video.
"""

import os
import sys
import uuid
import base64
import tempfile
import subprocess
import glob
import traceback
import requests
import runpod

# SkyReels-V3 repo path
SKYREELS_DIR = "/app/SkyReels-V3"
MODEL_DIR = os.environ.get("MODEL_DIR", "/runpod-volume/models")


def download_file(url: str, dest_path: str) -> str:
    """Download a file from URL to destination path."""
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return dest_path


def save_base64_file(b64_data: str, dest_path: str) -> str:
    """Decode base64 data and save to file."""
    # Strip data URI prefix if present
    if "," in b64_data[:100]:
        b64_data = b64_data.split(",", 1)[1]
    raw = base64.b64decode(b64_data)
    with open(dest_path, "wb") as f:
        f.write(raw)
    return dest_path


def prepare_input_file(data: str, suffix: str, task_dir: str) -> str:
    """Prepare an input file from base64 data or URL."""
    dest = os.path.join(task_dir, f"input{suffix}")
    if data.startswith("http://") or data.startswith("https://"):
        return download_file(data, dest)
    else:
        return save_base64_file(data, dest)


def find_output_video(output_dir: str) -> str | None:
    """Find the generated video file in the output directory."""
    patterns = ["*.mp4", "*.MP4"]
    for pattern in patterns:
        files = glob.glob(os.path.join(output_dir, "**", pattern), recursive=True)
        if files:
            # Return the most recently modified file
            return max(files, key=os.path.getmtime)
    return None


def handler(job: dict) -> dict:
    """RunPod serverless handler for SkyReels-V3 Talking Avatar."""
    job_input = job.get("input", {})

    # Validate required inputs
    image_data = job_input.get("image_base64") or job_input.get("image_url")
    audio_data = job_input.get("audio_base64") or job_input.get("audio_url") or job_input.get("wav_base64")
    prompt = job_input.get("prompt", "A person is talking naturally with clear expressions.")
    resolution = job_input.get("resolution", "720P")
    seed = job_input.get("seed", 42)

    if not image_data:
        return {"error": "image_base64 or image_url is required"}
    if not audio_data:
        return {"error": "audio_base64, audio_url, or wav_base64 is required"}

    # Create task directory
    task_id = str(uuid.uuid4())
    task_dir = os.path.join(tempfile.gettempdir(), f"skyreels_task_{task_id}")
    os.makedirs(task_dir, exist_ok=True)
    output_dir = os.path.join(task_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Prepare input files
        print(f"[SkyReels] Task {task_id}: Preparing input files...")

        # Detect image format
        image_suffix = ".jpg"
        if isinstance(image_data, str) and image_data.startswith("data:image/png"):
            image_suffix = ".png"
        elif isinstance(image_data, str) and ".png" in image_data[:200]:
            image_suffix = ".png"

        image_path = prepare_input_file(image_data, image_suffix, task_dir)

        # Detect audio format
        audio_suffix = ".wav"
        if isinstance(audio_data, str) and (".mp3" in audio_data[:200] or "audio/mp3" in audio_data[:100]):
            audio_suffix = ".mp3"

        audio_path = prepare_input_file(audio_data, audio_suffix, task_dir)

        print(f"[SkyReels] Image: {image_path} ({os.path.getsize(image_path)} bytes)")
        print(f"[SkyReels] Audio: {audio_path} ({os.path.getsize(audio_path)} bytes)")

        # Determine model path
        model_id = os.path.join(MODEL_DIR, "SkyReels-V3-A2V-19B")
        if not os.path.exists(model_id):
            # Fallback to HuggingFace download
            model_id = "Skywork/SkyReels-V3-A2V-19B"
            print(f"[SkyReels] Model not found locally, will download from HuggingFace: {model_id}")
        else:
            print(f"[SkyReels] Using local model: {model_id}")

        # Build command
        cmd = [
            "python3", os.path.join(SKYREELS_DIR, "generate_video.py"),
            "--task_type", "talking_avatar",
            "--prompt", prompt,
            "--input_image", image_path,
            "--input_audio", audio_path,
            "--model_id", model_id,
            "--resolution", resolution,
            "--seed", str(seed),
            "--offload",
            "--save_dir", output_dir,
        ]

        # Add low_vram flag for GPUs with less VRAM
        gpu_vram = job_input.get("low_vram", False)
        if gpu_vram:
            cmd.append("--low_vram")

        print(f"[SkyReels] Running command: {' '.join(cmd)}")

        # Execute SkyReels-V3
        env = os.environ.copy()
        env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=SKYREELS_DIR,
            env=env,
            timeout=1800,  # 30 min timeout
        )

        print(f"[SkyReels] stdout: {result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout}")
        if result.stderr:
            print(f"[SkyReels] stderr: {result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr}")

        if result.returncode != 0:
            return {
                "error": f"Video generation failed (exit code {result.returncode})",
                "stdout": result.stdout[-1000:],
                "stderr": result.stderr[-1000:],
            }

        # Find output video
        video_path = find_output_video(output_dir)
        if not video_path:
            # Also check in the SkyReels default output directory
            video_path = find_output_video(os.path.join(SKYREELS_DIR, "output"))

        if not video_path:
            return {
                "error": "No output video found after generation",
                "stdout": result.stdout[-500:],
            }

        print(f"[SkyReels] Output video: {video_path} ({os.path.getsize(video_path)} bytes)")

        # Encode video to base64
        with open(video_path, "rb") as f:
            video_base64 = base64.b64encode(f.read()).decode("utf-8")

        return {
            "status": "success",
            "video_base64": video_base64,
            "filename": f"skyreels_{task_id}.mp4",
            "resolution": resolution,
        }

    except subprocess.TimeoutExpired:
        return {"error": "Video generation timed out (30 min limit)"}
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}
    finally:
        # Cleanup task directory
        try:
            import shutil
            shutil.rmtree(task_dir, ignore_errors=True)
        except Exception:
            pass


# Start RunPod serverless worker
runpod.serverless.start({"handler": handler})
