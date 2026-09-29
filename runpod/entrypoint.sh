#!/usr/bin/env bash
set -Eeuo pipefail

COMFY="${H3_COMFY_ROOT:-/opt/ComfyUI}"
MODELS="${H3_MODELS_DIR:-/workspace/h3-runtime/models}"
OUTPUTS="${H3_OUTPUT_DIR:-/workspace/h3-output}"
INPUTS="${H3_INPUT_DIR:-/workspace/h3-input}"

if [[ -z "${H3_CLOUD_TOKEN:-}" ]]; then
  echo "[H3 Cloud] ERROR: H3_CLOUD_TOKEN is required" >&2
  exit 1
fi

mkdir -p \
  "$MODELS/diffusion_models" "$MODELS/text_encoders" "$MODELS/vae" "$MODELS/loras" \
  "$OUTPUTS" "$INPUTS"

download_model() {
  local repo="$1" file="$2" expected_size="$3" expected_sha="$4"
  local target="$MODELS/$2" partial="$MODELS/$2.partial" actual_size
  if [[ -s "$target" ]]; then
    actual_size="$(stat -c %s "$target")"
    if [[ "$actual_size" != "$expected_size" ]]; then
      echo "[H3 Cloud] ERROR: existing model has the wrong size: $file ($actual_size, expected $expected_size)" >&2
      echo "[H3 Cloud] Refusing an automatic replacement; verify the attached volume." >&2
      exit 1
    fi
    if [[ "${H3_VERIFY_MODELS:-0}" == "1" ]]; then
      echo "[H3 Cloud] verifying SHA-256: $file"
      echo "$expected_sha  $target" | sha256sum --check --status
    fi
    echo "[H3 Cloud] model present: $file"
    return
  fi
  if [[ "${H3_ALLOW_MODEL_DOWNLOAD:-1}" != "1" ]]; then
    echo "[H3 Cloud] ERROR: model missing and downloads are disabled: $file" >&2
    echo "[H3 Cloud] Attach the prepared model volume instead of downloading again." >&2
    exit 1
  fi
  mkdir -p "$(dirname "$target")"
  echo "[H3 Cloud] downloading missing model once: $file"
  aria2c --allow-overwrite=true --auto-file-renaming=false --continue=true \
    --max-connection-per-server=16 --split=16 --min-split-size=16M \
    --file-allocation=none --dir="$(dirname "$partial")" --out="$(basename "$partial")" \
    "https://huggingface.co/$repo/resolve/main/$file?download=true"
  actual_size="$(stat -c %s "$partial")"
  if [[ "$actual_size" != "$expected_size" ]]; then
    echo "[H3 Cloud] ERROR: downloaded model has the wrong size: $file ($actual_size, expected $expected_size)" >&2
    exit 1
  fi
  echo "[H3 Cloud] verifying downloaded model: $file"
  echo "$expected_sha  $partial" | sha256sum --check --status
  mv "$partial" "$target"
}

# Model weights deliberately live on the network volume, not in the container
# image. A replacement or migrated Pod therefore reuses the same files.
download_model Comfy-Org/MiniMax-H3 text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors \
  15687142551 35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6
download_model Comfy-Org/MiniMax-H3 vae/minimax_h3_video_vae_fp16.safetensors \
  5207808496 7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522
download_model Comfy-Org/MiniMax-H3 vae/minimax_h3_audio_vae_fp32.safetensors \
  605254808 8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48
download_model Comfy-Org/MiniMax-H3 diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors \
  20970379616 e889202c41dafb67b10d67b97f0d8541508036a6090af23425a5c2615d03c47a
if [[ "${H3_DOWNLOAD_REF2V:-1}" == "1" ]]; then
  download_model Comfy-Org/MiniMax-H3 diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors \
    20970379616 9255f52b6677845ad238f20dfaafa94727053694127ab7f255c048f0f9365779
fi

python - <<'PY'
import torch
assert torch.__version__.startswith("2.9.1"), torch.__version__
assert torch.cuda.is_available(), "CUDA GPU is unavailable"
print(f"[H3 Cloud] GPU ready: {torch.cuda.get_device_name(0)}; torch {torch.__version__}; CUDA {torch.version.cuda}", flush=True)
PY

cleanup() {
  local status=$?
  trap - EXIT INT TERM
  [[ -n "${PROXY_PID:-}" ]] && kill "$PROXY_PID" 2>/dev/null || true
  [[ -n "${COMFY_PID:-}" ]] && kill "$COMFY_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  exit "$status"
}
trap cleanup EXIT INT TERM

cd "$COMFY"
python main.py \
  --listen 127.0.0.1 --port 8189 --disable-auto-launch \
  --disable-comfy-compiler --highvram \
  --models-directory "$MODELS" \
  --output-directory "$OUTPUTS" --input-directory "$INPUTS" &
COMFY_PID=$!

for _ in $(seq 1 180); do
  if ! kill -0 "$COMFY_PID" 2>/dev/null; then
    echo "[H3 Cloud] ERROR: ComfyUI exited during startup" >&2
    wait "$COMFY_PID"
  fi
  if curl -fsS http://127.0.0.1:8189/system_stats >/dev/null; then
    echo "[H3 Cloud] ComfyUI ready; authenticated endpoint listening on 0.0.0.0:8188"
    python /opt/h3-cloud/auth_proxy.py &
    PROXY_PID=$!
    wait -n "$COMFY_PID" "$PROXY_PID"
    exit $?
  fi
  sleep 2
done

echo "[H3 Cloud] ERROR: ComfyUI was not ready after 6 minutes" >&2
exit 1

