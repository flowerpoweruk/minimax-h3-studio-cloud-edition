# Runpod H100 Benchmark

Date: 2026-09-29

Five runs were started individually with the visible Minimax H3 Studio - Cloud
Edition GUI. No job was submitted directly to ComfyUI or queued through an API.

## Fixed configuration

- Prompt: `a man is crying`
- Mode: text to video
- Duration: 15 seconds (362 generated frames; output is 15.083 seconds at 24 fps)
- Resolution: 1280x736
- Sampler: `res_multistep`
- Scheduler: `simple`
- Steps: 20
- GPU: Runpod Secure Cloud, NVIDIA H100 80GB HBM3
- Image: `ghcr.io/flowerpoweruk/minimax-h3-studio-cloud-edition:runpod-v1.0.5`
- Persistent model volume: `minimax-h3-cloud-models`

## Results

| Run | Studio start-to-finish | Comfy execution | Output |
| ---: | ---: | ---: | --- |
| 1 | 16:40.255 | 16:35 | 15.083s, 1280x736, H.264 + AAC |
| 2 | 16:24.317 | 16:21 | 15.083s, 1280x736, H.264 + AAC |
| 3 | 16:28.170 | 16:23 | 15.083s, 1280x736, H.264 + AAC |
| 4 | 16:27.561 | 16:23 | 15.083s, 1280x736, H.264 + AAC |
| 5 | 16:27.364 | 16:22 | 15.083s, 1280x736, H.264 + AAC |

- Mean Studio time: **16:29.533**
- Mean Comfy execution time: **16:24.8**
- Warm-run mean (runs 2-5): **16:26.853** Studio / **16:22.25** Comfy
- Fastest/slowest Studio spread: **15.938 seconds**
- Approximate GPU cost at $3.49/hour: **$0.96 per run** at the measured mean

Run 1's sampler log took 15:32 for 20 steps, averaging approximately 46.63
seconds per step. GPU utilization stayed at 100% during sampling. The remote
queue contained exactly one running prompt and zero pending prompts throughout
each clean run. No model download, dependency installation, OOM, or execution
error occurred.

## Confirmed defects fixed after the benchmark

1. The GUI elapsed timer used a polling-loop counter as seconds. Network and
   history request time made it under-report a 16-minute render as roughly nine
   minutes. It now derives elapsed time from persisted real timestamps.
2. Cancelling a Studio job used ComfyUI's global `/interrupt` call. If that
   Studio job was pending behind an orphan, the wrong running prompt could be
   interrupted while the intended pending prompt remained queued. Studio now
   uses ComfyUI's targeted `/api/jobs/{prompt_id}/cancel` endpoint, which
   atomically cancels that exact running or pending prompt.
3. A cancellation during graph preparation could race with prompt submission.
   The worker now checks cancellation immediately before submitting to ComfyUI.

## Optimization priorities

1. **Reduce sampling work.** Sampling accounts for about 94% of total runtime.
   A validated turbo LoRA or a lower step preset is the highest-impact option;
   reducing 20 steps to 12-15 should reduce the dominant portion roughly in
   proportion, subject to a quality comparison.
2. **Benchmark shorter temporal chunks.** Compare one 15-second/362-frame job
   with three linked 5-second jobs. Temporal attention may scale non-linearly,
   so this must be measured rather than assumed.
3. **Benchmark the full 96GB Blackwell GPU.** The selected H3 checkpoint uses
   INT8 ConvRot operations. A full RTX PRO 6000 Blackwell may execute that path
   differently from H100; it needs the same controlled five-run test when
   capacity is available.
4. **Evaluate attention acceleration separately.** Studio currently disables
   Sage Attention deliberately. Sage/Flash-style acceleration should only be
   enabled after an image-level compatibility and output-quality benchmark.
5. **Keep models warm for batches.** The first run was about 16 seconds slower
   than the fastest warm run. Sequential jobs on one running Pod already reuse
   the loaded model and avoid model downloads.

The Network Volume remains intact. Stopping or replacing the Pod does not erase
these models and does not require downloading them again.
