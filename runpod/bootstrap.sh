#!/usr/bin/env bash
set -euo pipefail

ROOT="/workspace/minimax-h3-cloud"
RUNTIME="/workspace/h3-runtime"
COMFY="$RUNTIME/ComfyUI"
ENV_DIR="$RUNTIME/env"
MODELS="$RUNTIME/models"

export DEBIAN_FRONTEND=noninteractive
export UV_HTTP_TIMEOUT=1200
export HF_HUB_ENABLE_HF_TRANSFER=1

mkdir -p "$RUNTIME" "$MODELS/diffusion_models" "$MODELS/text_encoders" "$MODELS/vae" "$MODELS/loras"
apt-get update -qq
apt-get install -y -qq git ffmpeg curl
python -m pip install -q --upgrade uv huggingface_hub hf_transfer

if [[ ! -d "$COMFY/.git" ]]; then
  git clone --depth 1 https://github.com/comfyanonymous/ComfyUI "$COMFY"
else
  git -C "$COMFY" pull --ff-only
fi

uv venv "$ENV_DIR" --python "$(command -v python)" --system-site-packages
uv pip install --python "$ENV_DIR/bin/python" -r "$COMFY/requirements.txt"
uv pip install --python "$ENV_DIR/bin/python" -r "$ROOT/studio/requirements.txt"

for spec in \
  "https://github.com/ltdrdata/ComfyUI-Manager|ComfyUI-Manager" \
  "https://github.com/kijai/ComfyUI-KJNodes|ComfyUI-KJNodes" \
  "https://github.com/jlucasmcrell/ComfyUI-H3-Multishot|ComfyUI-H3-Multishot"; do
  url="${spec%%|*}"
  name="${spec##*|}"
  dest="$COMFY/custom_nodes/$name"
  if [[ ! -d "$dest/.git" ]]; then
    git clone --depth 1 "$url" "$dest"
  else
    git -C "$dest" pull --ff-only
  fi
done
uv pip install --python "$ENV_DIR/bin/python" -r "$COMFY/custom_nodes/ComfyUI-KJNodes/requirements.txt"

# CUDA 13 / torch 2.10 is the accelerated path used by the local edition too.
uv pip install --python "$ENV_DIR/bin/python" \
  torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0 \
  --index-url https://download.pytorch.org/whl/cu130 --force-reinstall

rm -rf "$COMFY/models/diffusion_models" "$COMFY/models/text_encoders" "$COMFY/models/vae" "$COMFY/models/loras"
ln -s "$MODELS/diffusion_models" "$COMFY/models/diffusion_models"
ln -s "$MODELS/text_encoders" "$COMFY/models/text_encoders"
ln -s "$MODELS/vae" "$COMFY/models/vae"
ln -s "$MODELS/loras" "$COMFY/models/loras"

rm -rf "$COMFY/custom_nodes/minimax_h3_cloud"
cp -R "$ROOT/custom_nodes/minimax_h3_pinokio" "$COMFY/custom_nodes/minimax_h3_cloud"
mkdir -p "$COMFY/user/default/workflows"
cp "$ROOT"/workflows/*.json "$COMFY/user/default/workflows/"

download_model() {
  local repo="$1" file="$2" dest="$3"
  if [[ -s "$dest/$file" ]]; then
    echo "[H3 Cloud] ready: $file"
    return
  fi
  "$ENV_DIR/bin/python" -c \
    'from huggingface_hub import hf_hub_download; import sys; hf_hub_download(sys.argv[1], sys.argv[2], local_dir=sys.argv[3])' \
    "$repo" "$file" "$dest"
}

download_model Comfy-Org/MiniMax-H3 \
  text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors "$MODELS"
download_model Comfy-Org/MiniMax-H3 \
  vae/minimax_h3_video_vae_fp16.safetensors "$MODELS"
download_model Comfy-Org/MiniMax-H3 \
  vae/minimax_h3_audio_vae_fp32.safetensors "$MODELS"
download_model Comfy-Org/MiniMax-H3 \
  diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors "$MODELS"
download_model Comfy-Org/MiniMax-H3 \
  diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors "$MODELS"

if [[ -z "${H3_CLOUD_TOKEN:-}" ]]; then
  echo "H3_CLOUD_TOKEN is required" >&2
  exit 1
fi

cd "$COMFY"
"$ENV_DIR/bin/python" main.py --listen 127.0.0.1 --port 8189 --disable-auto-launch &
COMFY_PID=$!
trap 'kill "$COMFY_PID" 2>/dev/null || true' EXIT INT TERM

for _ in $(seq 1 180); do
  if curl -fsS http://127.0.0.1:8189/system_stats >/dev/null; then
    echo "[H3 Cloud] ComfyUI ready; authenticated proxy starting on :8188"
    exec "$ENV_DIR/bin/python" "$ROOT/runpod/auth_proxy.py"
  fi
  sleep 2
done
echo "ComfyUI did not become ready" >&2
exit 1
