# Starting Up Runpod Again Easily

Use this checklist after the one-time model download has completed. Cloud
Edition keeps software and durable data in separate places:

- **Container image:** the pinned ComfyUI installation, custom nodes, PyTorch
  integration and all other software.
- **Network Volume `minimax-h3-cloud-models`:** the large H3 model files, inputs
  and generated outputs.

Starting a Pod does **not** reinstall Python packages, clone repositories or
download models that are already on the Network Volume.

## Start tomorrow

1. Open the [Runpod Pods page](https://console.runpod.io/pods).
2. Find **`minimax-h3-studio-cloud-edition`**. Confirm it is attached to the
   Network Volume **`minimax-h3-cloud-models`**.
3. Click **Start**. If Runpod offers migration because that GPU is unavailable,
   choose **Automatically migrate your Pod data**. Migration creates a new Pod
   ID, so copy the new ID after it completes.
4. On Windows, double-click **`run-cloud-edition.bat`**.
5. Open **Settings → Compute backend** and select **Runpod cloud GPU**.
6. If the Pod was migrated or replaced, paste its new **Pod ID**, leave
   **ComfyUI endpoint** blank, then click **Save & connect**. Otherwise do not
   change the saved settings.
7. Click **Test**. Continue only when it says **Runpod ComfyUI connected**.
8. Generate normally.

Normal startup pulls the prebuilt container image if that machine does not
already cache it, checks the persistent model filenames, starts ComfyUI and
starts the authenticated proxy. It must not run `apt`, `pip`, `uv`, `git clone`
or `git pull`. The first generation of a session still has to load large model
weights from the Network Volume into RAM/VRAM; later generations in that same
session reuse the loaded models.

## Stop safely when finished

1. Wait until the current generation has finished or cancel it.
2. Click **Stop Pod** in Studio Settings or **Stop** in the Runpod console.
3. Leave the Network Volume **`minimax-h3-cloud-models`** in place.

Stopping ends active GPU billing. The much smaller Network Volume storage charge
continues while the models are retained. Do not delete the Network Volume unless
you intentionally want to erase the downloaded models and outputs.

## If the old GPU is unavailable

Prefer Runpod's migration option. If migration is unavailable:

1. Stop or terminate the unavailable old Pod. Only one Pod can attach a Network
   Volume at a time.
2. In Studio, confirm **Secure Cloud**, select a full GPU with enough VRAM, and
   confirm the existing **Network volume ID** is still filled in.
3. Click **Create managed Pod**. Do not create a generic PyTorch/Jupyter Pod.
4. Save the newly created Pod ID, wait for **Test** to connect, then generate.

The replacement uses the same prebuilt Cloud Edition image and the same model
volume. There is no dependency installation and no repeat model download.

An ordinary Network Volume is tied to its data center. You may select any
compatible GPU available in that data center. If the GPU you want is available
only elsewhere, use Runpod's beta Global Volume procedure described in the main
README; do not copy or download the 64 GB model bundle again from the internet.

## If Test does not connect

1. Confirm the Pod is **Running** and exposes `8188/http`.
2. Open the Pod logs. A healthy start ends with:
   `ComfyUI ready; authenticated endpoint listening on 0.0.0.0:8188`.
3. If the log says **downloading missing model once**, that exact model file was
   absent from the attached volume. Verify the correct Network Volume is mounted
   at `/workspace` before allowing a large download.
4. If the Pod ID changed after migration, update the ID in Studio and leave the
   endpoint blank so Studio derives the new proxy URL.
5. Never start a second paid GPU merely to troubleshoot a slow first Pod.

Runpod's documentation confirms that container images should contain software
and dependencies, while Network Volumes persist independently of Pods:
[custom Pod templates](https://docs.runpod.io/pods/templates/create-custom-template),
[storage types](https://docs.runpod.io/pods/storage/types), and
[Pod migration](https://docs.runpod.io/pods/troubleshooting/pod-migration).
