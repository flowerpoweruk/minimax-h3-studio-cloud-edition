# syntax=docker/dockerfile:1.7
FROM runpod/pytorch:1.0.3-cu1300-torch291-ubuntu2404

LABEL org.opencontainers.image.source="https://github.com/flowerpoweruk/minimax-h3-studio-cloud-edition" \
      org.opencontainers.image.description="Pinned Runpod runtime for Minimax H3 Studio - Cloud Edition" \
      org.opencontainers.image.licenses="AGPL-3.0"

ARG COMFYUI_REF=3b3939a78878ca0d5c0817d8829df8cbf7308ffd
ARG KJNODES_REF=d3cfe21625e5170126ce06fbfcfe1d88108688c3
ARG H3_MULTISHOT_REF=d7d197709fc93c1afb125e3db1dfd4ac0ae28c60

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    H3_COMFY_ROOT=/opt/ComfyUI \
    H3_MODELS_DIR=/workspace/h3-runtime/models \
    H3_OUTPUT_DIR=/workspace/h3-output \
    H3_INPUT_DIR=/workspace/h3-input

RUN apt-get update \
    && apt-get install -y --no-install-recommends aria2 ca-certificates curl ffmpeg git tini \
    && rm -rf /var/lib/apt/lists/*

RUN git init /opt/ComfyUI \
    && git -C /opt/ComfyUI remote add origin https://github.com/comfyanonymous/ComfyUI.git \
    && git -C /opt/ComfyUI fetch --depth 1 origin "$COMFYUI_REF" \
    && git -C /opt/ComfyUI checkout --detach FETCH_HEAD \
    && git init /opt/ComfyUI/custom_nodes/ComfyUI-KJNodes \
    && git -C /opt/ComfyUI/custom_nodes/ComfyUI-KJNodes remote add origin https://github.com/kijai/ComfyUI-KJNodes.git \
    && git -C /opt/ComfyUI/custom_nodes/ComfyUI-KJNodes fetch --depth 1 origin "$KJNODES_REF" \
    && git -C /opt/ComfyUI/custom_nodes/ComfyUI-KJNodes checkout --detach FETCH_HEAD \
    && git init /opt/ComfyUI/custom_nodes/ComfyUI-H3-Multishot \
    && git -C /opt/ComfyUI/custom_nodes/ComfyUI-H3-Multishot remote add origin https://github.com/jlucasmcrell/ComfyUI-H3-Multishot.git \
    && git -C /opt/ComfyUI/custom_nodes/ComfyUI-H3-Multishot fetch --depth 1 origin "$H3_MULTISHOT_REF" \
    && git -C /opt/ComfyUI/custom_nodes/ComfyUI-H3-Multishot checkout --detach FETCH_HEAD \
    && find /opt/ComfyUI -type d -name .git -prune -exec rm -rf '{}' +

COPY runpod/requirements.lock /opt/h3-cloud/requirements.lock

# The base image owns the CUDA 13 / PyTorch 2.9.1 stack. The hashed lock was
# resolved with all Torch, CUDA and NVIDIA runtime packages explicitly excluded,
# so this build cannot accidentally download or replace the GPU stack.
RUN python -m pip install --no-deps \
      'https://files.pythonhosted.org/packages/93/b1/db2941526ecddd84884132e2742a55c9311296a6a38627f9e2627f5ac889/torchvision-0.24.1-cp312-cp312-manylinux_2_28_x86_64.whl#sha256=66a98471fc18cad9064123106d810a75f57f0838eee20edc56233fd8484b0cc7' \
    && python -m pip install --require-hashes -r /opt/h3-cloud/requirements.lock \
    && python -c "import torch, torchvision; assert torch.__version__.startswith('2.9.1'); assert torchvision.__version__.startswith('0.24.1'); print(torch.__version__, torch.version.cuda)" \
    && python -m pip check

COPY custom_nodes/minimax_h3_pinokio /opt/ComfyUI/custom_nodes/minimax_h3_cloud
COPY workflows /opt/ComfyUI/user/default/workflows
COPY runpod/auth_proxy.py /opt/h3-cloud/auth_proxy.py
COPY runpod/entrypoint.sh /opt/h3-cloud/entrypoint.sh

RUN chmod 0755 /opt/h3-cloud/entrypoint.sh \
    && python -m compileall -q /opt/h3-cloud /opt/ComfyUI/custom_nodes/minimax_h3_cloud

WORKDIR /opt/ComfyUI
EXPOSE 8188
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/opt/h3-cloud/entrypoint.sh"]

