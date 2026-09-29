#!/usr/bin/env bash
set -euo pipefail

ROOT="/workspace/minimax-h3-cloud"
RUNTIME="/workspace/h3-runtime"
COMFY="$RUNTIME/ComfyUI"
ENV_DIR="$RUNTIME/env-runpod-torch291-v2"
MODELS="$RUNTIME/models"

export DEBIAN_FRONTEND=noninteractive
# Retry stalled package mirrors promptly; large model transfers use aria2 below.
export UV_HTTP_TIMEOUT=60
# Keep downloaded wheels on the network volume. Installation metadata can be
# slower there than on local disk, but it is vastly cheaper than downloading
# CUDA/Python packages again after a Pod is replaced or migrated.
export UV_CACHE_DIR="${H3_UV_CACHE_DIR:-/workspace/h3-runtime/uv-cache}"
export UV_LINK_MODE=copy

mkdir -p "$RUNTIME" "$MODELS/diffusion_models" "$MODELS/text_encoders" "$MODELS/vae" "$MODELS/loras"
apt-get update -qq
apt-get install -y -qq git ffmpeg curl aria2
if ! command -v uv >/dev/null 2>&1; then
  python -m pip install -q --upgrade uv
fi

if [[ ! -d "$COMFY/.git" ]]; then
  git clone --depth 1 https://github.com/comfyanonymous/ComfyUI "$COMFY"
else
  git -C "$COMFY" pull --ff-only
fi

BASE_PYTHON=""
for candidate in "$(command -v python 2>/dev/null || true)" \
  "$(command -v python3 2>/dev/null || true)" \
  /usr/local/bin/python /usr/local/bin/python3 /usr/bin/python3 /venv/main/bin/python; do
  if [[ -n "$candidate" && -x "$candidate" ]] && \
    "$candidate" -c 'import torch; assert torch.__version__.startswith("2.9.")' >/dev/null 2>&1; then
    BASE_PYTHON="$candidate"
    break
  fi
done

if [[ -z "$BASE_PYTHON" ]]; then
  echo "[H3 Cloud] ERROR: this image does not expose its bundled PyTorch 2.9 Python." >&2
  echo "[H3 Cloud] Refusing to download a replacement multi-gigabyte CUDA stack." >&2
  exit 1
fi

echo "[H3 Cloud] using bundled PyTorch from $BASE_PYTHON"
"$BASE_PYTHON" -c 'import torch; print(f"[H3 Cloud] bundled torch {torch.__version__} / CUDA {torch.version.cuda}")'

# Keep all non-CUDA Python dependencies on the network volume. The Runpod image
# installs Torch in its system Python (not /venv/main). Inherit that installation
# and explicitly remove Torch packages from ComfyUI's requirements so uv can
# never replace them with another multi-gigabyte CUDA stack.
uv venv "$ENV_DIR" --python "$BASE_PYTHON" --system-site-packages --allow-existing
H3_PYTHON="$ENV_DIR/bin/python"

# PyPI's single-stream downloads can be extremely slow from some Runpod data
# centers. Fetch the few large, dependency-free wheels with aria2's parallel
# connections, retain them on the network volume, then let uv resolve the small
# packages normally. These are pinned to ComfyUI's current requirements.
WHEEL_CACHE="$RUNTIME/wheels"
mkdir -p "$WHEEL_CACHE"
install_cached_wheel() {
  local filename="$1" url="$2"
  local wheel="$WHEEL_CACHE/$filename"
  if [[ ! -s "$wheel" ]]; then
    echo "[H3 Cloud] parallel download: $filename"
    aria2c --allow-overwrite=true --auto-file-renaming=false --continue=true \
      --max-connection-per-server=16 --split=16 --min-split-size=1M \
      --file-allocation=none --dir="$WHEEL_CACHE" --out="$filename" "$url"
  fi
  uv pip install --python "$H3_PYTHON" --no-deps "$wheel"
}
install_cached_wheel \
  "av-18.1.0-cp311-abi3-manylinux_2_28_x86_64.whl" \
  "https://files.pythonhosted.org/packages/27/3a/204dbfc3e08eb4cdc6e6ff57be02150bc44523ebdb50182d10025792ebd9/av-18.1.0-cp311-abi3-manylinux_2_28_x86_64.whl"
install_cached_wheel \
  "comfyui_workflow_templates_media_api-0.3.84-py3-none-any.whl" \
  "https://files.pythonhosted.org/packages/35/47/e4c723615b396f75893049af38a4b53bcb0e8944418819bb0e0d72f342e8/comfyui_workflow_templates_media_api-0.3.84-py3-none-any.whl"
install_cached_wheel \
  "opencv_python_headless-5.0.0.93-cp37-abi3-manylinux_2_28_x86_64.whl" \
  "https://files.pythonhosted.org/packages/9b/21/f6ef335f6e65724aa78b8d792b48d40a48c381715f1e62f5a5049e09d07e/opencv_python_headless-5.0.0.93-cp37-abi3-manylinux_2_28_x86_64.whl"

FILTERED_COMFY_REQUIREMENTS="$(mktemp)"
trap 'rm -f "$FILTERED_COMFY_REQUIREMENTS"' EXIT
awk '!/^[[:space:]]*(torch|torchvision|torchaudio)([[:space:]<>=!~].*)?$/' \
  "$COMFY/requirements.txt" > "$FILTERED_COMFY_REQUIREMENTS"
uv pip install --python "$H3_PYTHON" -r "$FILTERED_COMFY_REQUIREMENTS"
uv pip install --python "$H3_PYTHON" -r "$ROOT/studio/requirements.txt"
# The current Runpod torch291 image does not consistently include torchvision.
# Install its small matching wheel without dependencies, which makes it
# impossible for the resolver to fetch or replace Torch/CUDA.
if ! "$H3_PYTHON" -c 'import torchvision; assert torchvision.__version__.startswith("0.24.")' >/dev/null 2>&1; then
  uv pip install --python "$H3_PYTHON" --no-deps torchvision==0.24.1
fi
"$H3_PYTHON" -c 'import torch, torchvision; assert torch.__version__.startswith("2.9."); assert torchvision.__version__.startswith("0.24.")'

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
uv pip install --python "$H3_PYTHON" -r "$COMFY/custom_nodes/ComfyUI-KJNodes/requirements.txt"

# Never replace the image's bundled CUDA/PyTorch packages during Pod startup.
# If GPU initialization fails, abort cheaply and surface the real error.
"$H3_PYTHON" -c 'import torch; assert torch.cuda.is_available(), "CUDA GPU is unavailable"; print(f"[H3 Cloud] GPU ready with torch {torch.__version__} / CUDA {torch.version.cuda}")'

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
  local target="$dest/$file" partial="$dest/$file.partial"
  mkdir -p "$(dirname "$target")"
  echo "[H3 Cloud] downloading: $file"
  aria2c --allow-overwrite=true --auto-file-renaming=false --continue=true \
    --max-connection-per-server=16 --split=16 --min-split-size=16M \
    --file-allocation=none --dir="$(dirname "$partial")" \
    --out="$(basename "$partial")" \
    "https://huggingface.co/$repo/resolve/main/$file?download=true"
  mv "$partial" "$target"
}

download_model Comfy-Org/MiniMax-H3 \
  text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors "$MODELS"
download_model Comfy-Org/MiniMax-H3 \
  vae/minimax_h3_video_vae_fp16.safetensors "$MODELS"
download_model Comfy-Org/MiniMax-H3 \
  vae/minimax_h3_audio_vae_fp32.safetensors "$MODELS"
download_model Comfy-Org/MiniMax-H3 \
  diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors "$MODELS"
if [[ "${H3_DOWNLOAD_REF2V:-0}" == "1" ]]; then
  download_model Comfy-Org/MiniMax-H3 \
    diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors "$MODELS"
else
  echo "[H3 Cloud] reference-video model deferred (set H3_DOWNLOAD_REF2V=1 to install it)"
fi

if [[ -z "${H3_CLOUD_TOKEN:-}" ]]; then
  echo "H3_CLOUD_TOKEN is required" >&2
  exit 1
fi

cd "$COMFY"
"$H3_PYTHON" main.py --listen 127.0.0.1 --port 8189 --disable-auto-launch &
COMFY_PID=$!
trap 'kill "$COMFY_PID" 2>/dev/null || true' EXIT INT TERM

for _ in $(seq 1 180); do
  if curl -fsS http://127.0.0.1:8189/system_stats >/dev/null; then
    echo "[H3 Cloud] ComfyUI ready; authenticated proxy starting on :8188"
    exec "$H3_PYTHON" "$ROOT/runpod/auth_proxy.py"
  fi
  sleep 2
done
echo "ComfyUI did not become ready" >&2
exit 1
