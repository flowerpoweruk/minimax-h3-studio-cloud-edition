# Starting Up Runpod Again Easily

This guide is for the Cloud Edition Pod that has already been configured. The
ComfyUI installation, Python environment, custom nodes, and all MiniMax H3
model files live on the 150 GB Runpod Network Volume named
**minimax-h3-cloud-models**, mounted at `/workspace`.

## Important: stop the Pod; do not delete it

- **Stop Pod** ends GPU compute billing while keeping the configured Pod.
- The Network Volume keeps `/workspace` independently of the Pod. Never delete
  the Network Volume named **minimax-h3-cloud-models**.
- Do not create a generic PyTorch/Jupyter Pod for Cloud Edition. It will not
  include the Cloud Edition startup command or ComfyUI service.

## Start it next time

1. Open the [Runpod Console](https://www.runpod.io/console/pods).
2. Find the Pod named **minimax-h3-studio-cloud-edition**.
   It should show **Secure Cloud**, a **48 GB RTX PRO 6000 MIG**, and the
   network volume **minimax-h3-cloud-models**.
3. Click **Start** for that same Pod.
4. Wait for Runpod to show the Pod as **Running**.
5. Allow roughly 2–5 minutes for Cloud Edition to check the cached files and
   start ComfyUI. Existing model files are detected and are not downloaded
   again.
6. On Windows, double-click `run-cloud-edition.bat` in the Cloud Edition folder.
7. In H3 Studio, open **Settings → Compute backend**.
8. Confirm **Video GPU** is set to **Runpod cloud GPU**.
9. Click **Test**. Wait until the page says **Runpod ComfyUI connected**.
10. Return to **Scene**, enter a prompt, and click **Generate**.

The first generation after starting the Pod can spend several minutes loading
the large text encoder and video model from persistent storage into RAM/VRAM.
That is normal; later generations in the same running session reuse the loaded
weights and start more quickly. Do not restart the Pod while the job says it is
running and no error is shown.

The saved Runpod API key, Pod ID, endpoint, and backend access token are reused
from this computer. Do not replace them unless the Pod or local settings have
actually changed.

## When finished

1. Wait for any active generation to finish.
2. Open the [Runpod Console](https://www.runpod.io/console/pods).
3. Click **Stop** on **minimax-h3-studio-cloud-edition**.
4. Leave the Network Volume **minimax-h3-cloud-models** in place.

Stopping the Pod ends GPU compute billing while retaining the Pod's persistent
files. Runpod may still charge a much smaller storage fee while it is stopped.

## If Test does not connect

1. Confirm Runpod says the Pod is **Running**.
2. Wait another 2–5 minutes and click **Test** again. Startup can take longer
   after Cloud Edition or ComfyUI updates.
3. Confirm the Pod still exposes these ports:
   - `8188/http` — authenticated Cloud Edition/ComfyUI endpoint
   - `8888/http` — reserved for optional maintenance tools (Jupyter is not
     required and may not be running)
   - `22/tcp` — SSH (maintenance only)
4. Confirm its container/start command still launches
   `runpod/bootstrap.sh` from this repository.
5. Do not create a second GPU Pod just to fix a slow startup; that can bill for
   two GPUs simultaneously.

## If Runpod says the GPU is unavailable, or the Pod was deleted

The models are safe on the Network Volume and do not need downloading again:

1. In H3 Studio open **Settings → Compute backend → Managed Pod options**.
2. Confirm **Cloud tier** is **Secure Cloud**, **GPU type ID** is
   `NVIDIA RTX PRO 6000 Blackwell Server Edition MIG 2g.48gb`, and **Network
   volume ID** is already filled in.
3. Terminate the unavailable old Pod in Runpod so only one Pod can use the
   volume.
4. Click **Create managed Pod** in H3 Studio.
5. Wait for it to run, click **Test**, then generate normally.

The replacement Pod attaches the same network volume, detects the complete
models, and starts ComfyUI without downloading them again. Do not create a
generic PyTorch/Jupyter Pod because it lacks the Cloud Edition startup command.

