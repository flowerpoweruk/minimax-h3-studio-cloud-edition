# Starting Up Runpod Again Easily

This guide is for the Cloud Edition Pod that has already been configured. The
ComfyUI installation, Python environment, custom nodes, and MiniMax H3 model
files live in the Pod's 150 GB persistent `/workspace` storage.

## Important: stop the Pod; do not delete it

- **Stop Pod** keeps the configured Pod and its persistent `/workspace` files.
- **Terminate**, **Delete**, or removing its storage can permanently remove the
  downloaded models and force a full setup again.
- Do not create a generic PyTorch/Jupyter Pod for Cloud Edition. It will not
  include the Cloud Edition startup command or ComfyUI service.

## Start it next time

1. Open the [Runpod Console](https://www.runpod.io/console/pods).
2. Find the Pod named **minimax-h3-studio-cloud-edition**.
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

The saved Runpod API key, Pod ID, endpoint, and backend access token are reused
from this computer. Do not replace them unless the Pod or local settings have
actually changed.

## When finished

1. Wait for any active generation to finish.
2. Open the [Runpod Console](https://www.runpod.io/console/pods).
3. Click **Stop** on **minimax-h3-studio-cloud-edition**.
4. Do **not** click Terminate or Delete.

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

## If the Pod was deleted

The original Pod's ordinary persistent storage may no longer be recoverable.
Use **Create managed Pod** inside Cloud Edition instead of creating a stock Pod
in Runpod. A managed Pod configures the correct ports, access token, persistent
workspace, repository, and automatic startup command.

For storage that must move between replacement Pods, create a Runpod Network
Volume first, paste its ID into **Settings → Managed Pod options → Network
volume ID**, and then use **Create managed Pod**. Models stored on that Network
Volume can be attached to a replacement Pod without downloading them again.

