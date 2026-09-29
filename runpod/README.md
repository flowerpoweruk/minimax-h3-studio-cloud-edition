# Runpod backend

H3 Studio can create a managed Runpod Pod from **Settings → Compute backend**.
The Pod runs the versioned Cloud Edition image published from
[`runpod/Dockerfile`](Dockerfile). ComfyUI, PyTorch and every Python/system
dependency are built into that image; Pod startup does not run `apt`, `pip`,
`uv`, `git clone`, or `git pull`.

Only H3 model weights, inputs and outputs live under `/workspace`. Attach a
Runpod Network Volume there to retain the large weights independently of a Pod.
The runtime checks for each model and downloads only a missing file, using a
temporary `.partial` name so an interrupted transfer is never accepted as a
complete model.

The browser never connects to the Pod directly. H3 Studio sends the saved bearer
token from its local backend, including for WebSocket progress events and media
uploads/downloads. Stop the Pod from Settings when it is idle to stop GPU billing.

The image pins ComfyUI and both third-party custom-node repositories to commits.
To upgrade them, change the `*_REF` build arguments, build the image in GitHub
Actions, verify it, then publish a new versioned Runpod image tag.
