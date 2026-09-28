# Runpod backend

H3 Studio can create a managed Runpod Pod from **Settings → Compute backend**.
The Pod uses the official CUDA 13 / PyTorch image, installs ComfyUI and the H3
nodes into its persistent `/workspace` volume, downloads the FL2VA and Ref2VA
weights once, and exposes an authenticated ComfyUI-compatible API.

The browser never connects to the Pod directly. H3 Studio sends the saved bearer
token from its local backend, including for WebSocket progress events and media
uploads/downloads. Stop the Pod from Settings when it is idle to stop GPU billing.
