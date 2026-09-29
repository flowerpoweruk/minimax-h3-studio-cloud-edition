# Runpod / ComfyUI Reliability Architecture

This document records the deployment decisions behind Cloud Edition. It is
intentionally explicit so a future change does not reintroduce paid, repeated
Pod setup work.

## Non-negotiable invariants

1. Pod startup never runs `apt`, `pip`, `uv`, `git clone`, or `git pull`.
2. ComfyUI, custom nodes and Python/system dependencies are built into a
   versioned container image before a GPU Pod starts.
3. H3 model weights and user output are outside the container on persistent
   storage mounted at `/workspace`.
4. Replacing a Pod or GPU reuses that storage. A missing model is the only
   condition that may initiate a model download.
5. Existing model files must match their published byte sizes. New downloads
   must additionally match the Hugging Face LFS SHA-256 before use.
6. The public Runpod HTTP port exposes only the bearer-authenticated proxy.
   ComfyUI itself listens on loopback at `127.0.0.1:8189`.
7. The application image runs no SSH server, Jupyter server, package manager,
   or ComfyUI Manager updater.

## Why the earlier design was slow

The stock PyTorch/Jupyter image contained a CUDA/PyTorch base but not this
application. Its startup command cloned repositories, created a Python
environment and resolved dependencies on every new machine. A resolver could
also ignore the base image's PyTorch and fetch another multi-gigabyte CUDA
stack. Keeping that mutable environment on `/workspace` made it persistent but
did not make it reproducible, and metadata-heavy Python environments are a poor
fit for network storage.

The corrected design uses Runpod's documented boundary:

- immutable application software in the container image;
- model/data persistence in a volume.

## Container image

`runpod/Dockerfile` extends the versioned Runpod CUDA 13 / PyTorch 2.9.1 image.
It pins ComfyUI, KJNodes and H3 Multishot to Git commits. The dependency lock is
resolved for Python 3.12 / Linux x86-64 with Torch, CUDA, Triton and NVIDIA
runtime packages explicitly excluded. The build installs the matching
`torchvision` wheel without dependencies and verifies both versions.

The image is published only from Git tags such as `runpod-v1.0.0`. A GitHub
Actions smoke test starts ComfyUI in CPU mode and calls `/system_stats` before
the image is pushed. A new runtime release gets a new tag; existing tags are not
reused.

## ComfyUI layout and warm behavior

ComfyUI's supported `--models-directory`, `--input-directory`, and
`--output-directory` options point directly at persistent storage. This avoids
maintaining a second Comfy installation or Python virtual environment on the
volume. ComfyUI remains one long-running process for the life of the Pod, so
its normal in-process model cache can be reused by later prompts. Stopping or
replacing a Pod necessarily clears RAM/VRAM; the next first generation must
load weights from persistent storage again, but it does not download or install
them.

## Storage choices

### Standard Network Volume — default managed path

This is independent of the Pod and survives Pod deletion. A replacement Pod
can mount the same volume and immediately see the models. It is available only
in Secure Cloud and is tied to one data center. Consequently, GPU switching is
easy among compatible GPUs available in that data center, but the volume does
not expand GPU choice to other data centers.

Before sending a create-Pod request, Studio reads the configured Network Volume
through Runpod's API, rejects Community Cloud, and adds the volume's datacenter
as an explicit placement constraint. An invalid volume ID or missing placement
metadata therefore fails before Runpod creates a billable Pod.

### High-performance Network Volume — optional faster cold model load

Runpod documents up to 3x throughput and 4x IOPS compared with standard network
storage, specifically citing reduced inference model-load time. This can reduce
the first-generation load after a Pod start when storage is the bottleneck. It
does not make sampling compute faster after weights are resident. Existing
standard volumes cannot be converted in place; data must be copied to a newly
created high-performance volume.

### Global Volume — maximum GPU-location portability, beta

Global Volumes are region-independent and optimized for read-heavy model
serving, so they are the best conceptual fit for switching to a GPU in another
data center without copying model weights again. They are currently beta,
object-backed, eventually consistent, and lack atomic rename/file locking.
Their Pod attachment is currently a console workflow rather than a stable
field in the REST v2 Pod API used by Studio. For those reasons Cloud Edition
supports their `/workspace` layout but does not claim one-click managed Global
Volume creation yet. Prepare/migrate the files first and set
`H3_ALLOW_MODEL_DOWNLOAD=0` on such a Pod.

## GPU replacement procedure

1. Stop the old Pod so it no longer incurs GPU compute charges.
2. Keep its Network or Global Volume.
3. Create a new Pod from the same Cloud Edition image tag, select the new GPU,
   and attach the existing volume at `/workspace`.
4. Save the new Pod ID in Studio because Runpod proxy URLs include that ID.
5. Test the authenticated endpoint before deleting the old stopped Pod.

A standard Network Volume constrains step 3 to its data center. A Global Volume
removes that location constraint but has the beta limitations above.

## Startup sequence

1. Validate the bearer token and persistent directories.
2. Check required model byte sizes; download only an absent file when downloads
   are enabled.
3. Verify the SHA-256 of every newly downloaded file before promoting it.
4. Verify the baked PyTorch version and CUDA/GPU availability.
5. Start ComfyUI privately on port 8189 using the persistent model/input/output
   directories.
6. Wait for `/system_stats`, then start the authenticated public proxy on 8188.

## Sources

- [Runpod custom Pod templates](https://docs.runpod.io/pods/templates/create-custom-template)
- [Runpod storage types](https://docs.runpod.io/pods/storage/types)
- [Runpod Network Volumes](https://docs.runpod.io/storage/network-volumes)
- [Runpod high-performance storage](https://docs.runpod.io/storage/high-performance-storage)
- [Runpod Global Volumes](https://docs.runpod.io/storage/globalvolume/overview)
- [Runpod Global Volumes for Pods](https://docs.runpod.io/storage/globalvolume/globalvolume-pods)
- [Runpod zero-GPU restart guidance](https://docs.runpod.io/pods/troubleshooting/zero-gpus)
- [Runpod Pod migration](https://docs.runpod.io/pods/troubleshooting/pod-migration)
- [Runpod exposed ports](https://docs.runpod.io/pods/configuration/expose-ports)
- [ComfyUI source and command-line model paths](https://github.com/Comfy-Org/ComfyUI/blob/master/main.py)
