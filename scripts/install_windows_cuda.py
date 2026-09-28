"""Reproducible standalone Windows/CUDA installer."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
ENV = APP / "env"


def run(*args: str, cwd: Path = ROOT) -> None:
    print("\n>", " ".join(str(x) for x in args), flush=True)
    subprocess.run([str(x) for x in args], cwd=cwd, check=True)


def clone_or_update(url: str, dest: Path) -> None:
    if (dest / ".git").is_dir():
        run("git", "-C", str(dest), "pull", "--ff-only")
    elif dest.exists():
        raise RuntimeError(f"{dest} exists but is not a Git checkout")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        run("git", "clone", "--depth", "1", url, str(dest))


def download(url: str, dest: Path) -> None:
    if dest.is_file() and dest.stat().st_size > 1024 * 1024:
        print(f"Ready: {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    offset = part.stat().st_size if part.exists() else 0
    request = urllib.request.Request(url)
    if offset:
        request.add_header("Range", f"bytes={offset}-")
    print(f"Downloading {dest.name} (large model; resumable)...", flush=True)
    with urllib.request.urlopen(request, timeout=120) as response:
        mode = "ab" if offset and response.status == 206 else "wb"
        if mode == "wb":
            offset = 0
        total = int(response.headers.get("Content-Length") or 0) + offset
        done = offset
        with part.open(mode) as handle:
            while True:
                chunk = response.read(8 * 1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {done / 1024**3:.1f} / {total / 1024**3:.1f} GB", end="", flush=True)
    print()
    part.replace(dest)


def main() -> None:
    if os.name != "nt":
        raise RuntimeError("This installer is for Windows only")
    run("nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader")
    clone_or_update("https://github.com/comfyanonymous/ComfyUI", APP)
    run("uv", "venv", str(ENV), "--python", "3.10", "--seed")
    py = ENV / "Scripts" / "python.exe"
    run("uv", "pip", "install", "--python", str(py), "-r", str(APP / "requirements.txt"))
    run("uv", "pip", "install", "--python", str(py), "-r", str(ROOT / "studio" / "requirements.txt"))

    nodes = APP / "custom_nodes"
    clone_or_update("https://github.com/ltdrdata/ComfyUI-Manager", nodes / "ComfyUI-Manager")
    clone_or_update("https://github.com/kijai/ComfyUI-KJNodes", nodes / "ComfyUI-KJNodes")
    clone_or_update("https://github.com/jlucasmcrell/ComfyUI-H3-Multishot", nodes / "ComfyUI-H3-Multishot")
    run("uv", "pip", "install", "--python", str(py), "-r", str(nodes / "ComfyUI-KJNodes" / "requirements.txt"))
    run(
        "uv", "pip", "install", "--python", str(py),
        "torch==2.10.0", "torchvision==0.25.0", "torchaudio==2.10.0",
        "--index-url", "https://download.pytorch.org/whl/cu130", "--force-reinstall",
    )
    run("uv", "pip", "install", "--python", str(py), "triton-windows==3.6.0.post26")

    bundled_node = nodes / "minimax_h3_cloud_edition"
    if bundled_node.exists():
        shutil.rmtree(bundled_node)
    shutil.copytree(ROOT / "custom_nodes" / "minimax_h3_pinokio", bundled_node)
    workflow_dest = APP / "user" / "default" / "workflows"
    workflow_dest.mkdir(parents=True, exist_ok=True)
    for workflow in (ROOT / "workflows").glob("*.json"):
        shutil.copy2(workflow, workflow_dest / workflow.name)

    base = "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main"
    models = [
        (f"{base}/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors?download=true", APP / "models/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
        (f"{base}/vae/minimax_h3_video_vae_fp16.safetensors?download=true", APP / "models/vae/minimax_h3_video_vae_fp16.safetensors"),
        (f"{base}/vae/minimax_h3_audio_vae_fp32.safetensors?download=true", APP / "models/vae/minimax_h3_audio_vae_fp32.safetensors"),
        (f"{base}/diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors?download=true", APP / "models/diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors"),
        (f"{base}/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors?download=true", APP / "models/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors"),
        ("https://huggingface.co/Kijai/MiniMax-H3_comfy/resolve/main/loras/minimax_h3_fl2v_lightx2v_turbo_4step_v0.1_comfy.safetensors?download=true", APP / "models/loras/minimax_h3_fl2v_lightx2v_turbo_4step_v0.1_comfy.safetensors"),
    ]
    for url, dest in models:
        download(url, dest)
    (ROOT / ".cloud-edition-installed").write_text("windows-cuda\n", encoding="utf-8")
    print("\nMinimax H3 Studio - Cloud Edition is ready.")


if __name__ == "__main__":
    main()
