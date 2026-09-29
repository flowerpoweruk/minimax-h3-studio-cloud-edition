# Minimax H3 Studio - Cloud Edition

Already configured a Runpod Pod? Follow **[Starting Up Runpod Again Easily](starting%20up%20runpod%20again%20easily.md)** for the short Start → Test → Generate routine and the safe shutdown steps that preserve downloaded models.

For the researched deployment boundaries, reproducibility rules, storage
tradeoffs and GPU-replacement procedure, see
**[Runpod / ComfyUI Reliability Architecture](runpod/ARCHITECTURE.md)**.

<p align="center">
  <img src="github-preview.png" alt="Minimax H3 Studio - Cloud Edition" width="640" />
</p>

A cloud-enabled fork of [erdinoral/minimax-h3-studio](https://github.com/erdinoral/minimax-h3-studio) built for people who want to run **MiniMax H3 without owning a local NVIDIA GPU**. The Studio interface runs on your Windows PC while ComfyUI, CUDA and all H3 inference run on a **Runpod Cloud GPU**.

Your computer does not download the H3 weights and does not need CUDA for the recommended cloud setup. The fork also keeps the upstream local-CUDA and Pinokio modes for users who want them.

MiniMax H3 accepts text, images, video and audio as context and generates video with native stereo audio. H3 Studio adds Director, Plan, Cinema Studio, queue management and a bilingual TR/EN interface.

## What Cloud Edition adds

- **No local GPU required:** use the full Studio interface from an ordinary Windows PC or laptop.
- **Managed Runpod Pods:** create, start, stop and test a Pod directly from Studio Settings.
- **Private remote ComfyUI access:** managed Pods expose port 8188 through Runpod's proxy and require a generated bearer token.
- **Fast, repeatable startup:** ComfyUI, CUDA-facing Python packages and custom nodes are prebuilt in a pinned container image—no `pip`, `uv`, `apt` or Git install runs when a Pod starts.
- **Persistent model storage:** keep the roughly 63 GB of H3 weights on a Runpod Network Volume so replacement and migrated Pods reuse the same files.
- **Local mode preserved:** switch back to a locally installed NVIDIA/CUDA backend whenever you want.

| Runs on your computer | Runs on Runpod |
|---|---|
| H3 Studio web interface, settings, prompts, queue and gallery | NVIDIA GPU, CUDA 13, ComfyUI, custom nodes and H3 generation |
| Small Python client environment | Roughly 63 GB of model weights plus the GPU software stack |

## Install on Windows — Runpod mode (no local GPU)

Requirements: Windows 10 or 11, internet access, a [Runpod account](https://www.runpod.io/console/signup) with billing enabled, and a few GB of local disk space. An NVIDIA GPU and a local CUDA installation are **not** required.

1. [Download the latest source ZIP](https://github.com/flowerpoweruk/minimax-h3-studio-cloud-edition/archive/refs/heads/main.zip) and extract the entire folder. Alternatively, clone this repository with Git.
2. Double-click **`install-cloud-client-windows.bat`**. It installs uv and Python 3.10 when needed, creates an isolated environment and installs only the Studio client.
3. Double-click **`run-cloud-edition.bat`**. The browser opens H3 Studio automatically.
4. Open **Settings → Compute backend** and complete the Runpod setup below.

The installer deliberately does not install ComfyUI, CUDA, PyTorch or H3 model files on your computer. GPU software is already contained in the managed Pod image; only the H3 weights are stored on the Runpod volume.

## Set up Runpod

### 1. Create an API key

1. Sign in to the [Runpod Console](https://www.runpod.io/console/user/settings).
2. Open **Settings → API Keys**, create a key and copy it. Runpod's official introduction also links its current [API-key instructions](https://docs.runpod.io/).
3. In H3 Studio, open **Settings → Compute backend**, select **Runpod cloud GPU**, paste the API key and click **Save & connect**.

The API key is used by your local Studio only to manage your Pod. It is stored in the Git-ignored `studio/data/runpod_settings.json` file and is never committed to the repository.

### 2. Create a managed Pod (recommended)

The defaults are ready for H3:

- **GPU:** `NVIDIA RTX PRO 6000 Blackwell Server Edition` (full GPU, not a MIG slice). You can replace this with another available Runpod GPU ID with sufficient VRAM.
- **Cloud:** Secure Cloud. Community Cloud can also be selected.
- **Persistent volume:** 150 GB, mounted at `/workspace`.
- **Network volume ID:** strongly recommended. Create a 150 GB or larger Network Volume in Runpod and enter its ID so models and outputs survive independently of the Pod. The volume and GPU must be available in a compatible data center.

Click **Create managed Pod**. Cloud Edition provisions the Pod from the versioned, prebuilt Cloud Edition image and starts an authenticated ComfyUI proxy on port 8188. It does not install Python or CUDA packages at startup. On a new empty Network Volume only, the first start downloads roughly 64 GB of H3 weights. Every later start detects and reuses those files.

The managed image is application-only: it exposes `8188/http` and deliberately
does not start SSH, Jupyter or a package installer. Its ComfyUI revision, custom
node revisions and hashed Python dependency lock are fixed at image-build time.

When setup finishes, click **Test**. A green connection status means generation requests are using the Runpod GPU. Runpod documents the `https://<pod-id>-<port>.proxy.runpod.net` format in its [port-exposure guide](https://docs.runpod.io/pods/configuration/expose-ports).

### 3. Generate and stop the Pod when finished

Use H3 Studio normally—the generation controls do not change between local and cloud modes. Click **Stop Pod** in Settings when you are finished so active GPU compute stops. Your persistent or network volume remains available for later starts; storage charges may continue according to your Runpod plan.

If a stopped Pod cannot reacquire its original GPU, migrate it or create a replacement attached to the same Network Volume. Runpod notes that migration creates a new Pod ID and new proxy URLs; save the replacement Pod ID in Studio. See Runpod's [Pod migration guide](https://docs.runpod.io/pods/troubleshooting/pod-migration).

### Use an existing Runpod Pod instead

Advanced users can connect an existing Pod:

1. Run a ComfyUI-compatible server on the Pod and expose HTTP port 8188.
2. Enter the **Pod ID**. If Endpoint URL is blank, Studio derives `https://<pod-id>-8188.proxy.runpod.net` automatically.
3. Enter the bearer token expected by that endpoint, then click **Save & connect** and **Test**.

The managed-Pod option is recommended because it installs the exact nodes, workflows and model layout expected by this fork and configures authentication automatically.

### Switching to another Runpod GPU without reinstalling

With a Network Volume, stop the old Pod and create a managed Pod with a different
GPU type while keeping the same **Network volume ID**. The new Pod pulls the
prebuilt Cloud Edition image and mounts the existing weights; it does not clone,
install or download those weights again. A normal Network Volume is tied to one
data center, so only GPU types available in that data center can use it.

For the widest cross-data-center GPU choice, Runpod now offers **Global Volumes**
in beta. They are region-independent and optimized for read-heavy inference, but
they have object-storage semantics (no atomic rename or file locking) and their
Pod attachment is currently a Runpod-console flow rather than a stable field in
the Pod API used by Studio. The safe advanced procedure is:

1. Create a Global Volume in Runpod.
2. Attach both the existing Network Volume and new Global Volume to one temporary
   Pod and copy `/workspace/` to `/workspace-global/` with Runpod's documented
   `rsync` procedure.
3. Delete that temporary Pod only after the copy is verified.
4. Deploy Cloud Edition image
   `ghcr.io/flowerpoweruk/minimax-h3-studio-cloud-edition:runpod-v1.0.6`, attach
   the Global Volume at `/workspace`, expose `8188/http`, and set the same strong
   `H3_CLOUD_TOKEN` in both the Pod and Studio. Also set
   `H3_ALLOW_MODEL_DOWNLOAD=0`; this makes a wrong or incomplete mount fail fast
   instead of writing another 64 GB bundle to object-backed storage.

See Runpod's [Global Volumes guide](https://docs.runpod.io/storage/globalvolume/overview)
and [Global Volumes for Pods](https://docs.runpod.io/storage/globalvolume/globalvolume-pods).
Because the feature is beta, the default one-click Studio path remains the more
predictable Secure Cloud + Network Volume configuration.

## Other installation options

### Local NVIDIA/CUDA

To run inference on your own NVIDIA GPU, double-click **`install-windows-cuda.bat`**, then **`run-cloud-edition.bat`**. The full local installation needs roughly 75 GB of disk space and validates that an NVIDIA driver is present before downloading the models.

### Pinokio

The upstream-style Pinokio **Install / Start / Update / Reset** flow remains available for local NVIDIA installations. If the app is already installed through Pinokio, selecting Runpod in Studio Settings makes Start launch Studio without starting local ComfyUI. For a computer with no local GPU, use the lightweight Windows cloud-client installer above.

Default output uses a 768-pixel short edge, but that is a default rather than a limit—see [Resolution](#resolution--you-are-not-capped-at-768p) for 1080p and higher output.

---

## What gets installed on the GPU machine

In Runpod mode, these files are installed on the Pod—not on your PC. In local CUDA mode, they are installed locally.

| Component | File | Size |
|---|---|---|
| H3-Encoder (Qwen3-VL-32B) | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 15.7 GB |
| H3-VisualVAE | `minimax_h3_video_vae_fp16.safetensors` | 5.2 GB |
| H3-AudioVAE | `minimax_h3_audio_vae_fp32.safetensors` | 0.6 GB |
| H3-Base-FL2VA | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | 21.0 GB |
| H3-Base-Ref2VA | `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | 21.0 GB |
| **Total weights** | | **~63 GB** |

ComfyUI and its Python dependencies are part of the versioned container image, not the Network Volume.

### Why these files and not the official ones

The official release is BF16: a single variant is ~144 GB (66 GB transformer + 67 GB text encoder + 10 GB VAE), and both variants plus the diffusers copy total ~290 GB. That does not fit on a normal SSD, and the BF16 transformer alone does not fit in 32 GB of VRAM.

Two reductions are applied, both chosen deliberately:

- **`pruned`** — drops the ~13 B AdaLN-branch parameters. The MiniMax model card states AdaLN modulation outputs "can be precomputed and cached, [so] these parameters do not need to be loaded for inference-only deployment." This is a strict win for inference, not a quality tradeoff. 33 B → ~20 B.
- **`int8_convrot` / `nvfp4_awq`** — rotation-based quantization with ComfyUI's `TensorCoreConvRotW4A4Layout` and `TensorCoreNVFP4Layout`. On Blackwell (RTX 50-series) these map onto native tensor-core instructions.

Net effect: 290 GB → 63 GB, and each model fits in 32 GB of VRAM.

### The cu130 requirement

ComfyUI's `comfy/quant_ops.py` disables the accelerated `comfy-kitchen` CUDA backend when `torch.version.cuda < 13`:

> `WARNING: You need pytorch with cu130 or higher to use optimized CUDA operations.`

Because every weight here is quantized, a cu12x torch build would still *run*, but on a dramatically slower path.

In practice ComfyUI's current `requirements.txt` **already** resolves to a CUDA 13 stack from PyPI — torch 2.13.0 (which depends on `nvidia-cudnn-cu13` / `nvidia-nccl-cu13`), torchvision 0.28.0, torchaudio 2.11.0 — so nothing needs fixing today. This launcher still ships its own `torch.js` pinning those exact versions to the cu130 index (`torch==2.13.0+cu130` etc.) as a **guarantee**: if PyPI's default torch ever reverts to a cu12x build, the launcher keeps working. The pins are equal to what ComfyUI resolves, so the step is a no-op on an up-to-date install rather than a downgrade.

The local `torch.js` also exists because the **stock** `system/examples/torch.js` pins `torch 2.7.0+cu128`, which *would* silently break the quantized path.

### GPU-machine requirements

- **Runpod mode:** an NVIDIA Runpod GPU and at least 80 GB of persistent storage; the managed default is a 48 GB RTX A6000 with 150 GB storage.
- **Local mode:** an NVIDIA GPU, current driver and roughly 75 GB of free local disk. The quantized weights and cu130 kernels are CUDA-specific. 32 GB VRAM comfortably runs one model at a time; less can use ComfyUI offloading but will be slower.

---

## H3 Studio (custom UI)

Start opens **H3 Studio** and connects it to the selected compute backend. Local mode also starts ComfyUI on the PC; Runpod mode connects to ComfyUI on the Pod and leaves the local GPU untouched. Top bar **TR | EN** switches the Studio UI and Director chat language (`h3Prompt` / SCENE stays English). Pinokio menu:

| Menu | Opens |
|---|---|
| **Open H3 Studio** (default) | Custom UI — prompt, 5/10/15s, continue, batch queue, Director, system bar |
| **Open ComfyUI** | Unmodified Comfy node graph (always available) |

Studio never replaces Comfy. If Studio fails, use **Open ComfyUI** as before.

### Latest Studio update

- **Scene workspace:** T2V, I2V, reference-video, continuation, selectable multi-LoRA, queue controls and final-frame continuation that follows the actual previous render.
- **Image Studio workflow:** generate a start/reference image from a prompt or add a local image, then use it in video creation. Image and video results live together in Gallery.
- **Gallery:** separate Video / Photo view, larger previews, prompt details, individual and bulk deletion, plus player previous/next navigation.
- **Director / Cinema:** production types for Film/Trailer, Music Video, Commercial, Intro and Outro; simplified content-first JSON import; character, location and scene bindings; continuous shot chains.
- **Music video planning:** upload a song, add a visual concept and lyrics, create editable lyric timing notes, then prepare a visual clip plan. This assists visual planning; it is not automatic beat-sync or lip-sync.

### Support

Bugs and ideas: Studio top bar **Destek / Support**, or [Cloud Edition GitHub Issues](https://github.com/flowerpoweruk/minimax-h3-studio-cloud-edition/issues). Use **Bug** for breakage and **Idea** for improvements.

### H3 Yönetmen (Director persona)

Bottom chat uses the local **H3 Yönetmen** persona (`studio/prompts/director_system.md`) over a Director LLM. Default is **Ollama** (`http://127.0.0.1:11434`). You can also pick **LM Studio** (`http://127.0.0.1:1234/v1`) or **llama.cpp** (`http://127.0.0.1:8080/v1`) — both use the OpenAI-compatible `/v1/chat/completions` API, no cloud key. Cloud providers (OpenAI, NVIDIA NIM, Gemini, Grok, Claude) stay available. The Director interviews for purpose / style / 5·10·15s clips, then returns a FilmBrief + shot list with H3-ready prompts. Every chat turn injects the current shot board (and Direktör studio cards) so the model can see shot text. **Plan** mode is for reading/editing those SCENE prompts without queuing; say “shot 3’ü değiştir” and save, then **Üretime al**. Production still runs on Comfy; on generate a local Ollama model is unloaded to free VRAM. When the last clip in the queue finishes (or you reset production), Studio asks ComfyUI to unload H3 models (`POST /free`) so VRAM is released. Continue / cinema shots in the same batch keep the models loaded between clips.

1. Start a Director backend: Ollama (`ollama serve` + a chat model such as `qwen3:8b`), **or** LM Studio Local Server with a loaded model (Gemma etc.), **or** `llama-server --port 8080`.
2. Pick the provider and model under **Ayarlar → Yönetmen LLM**.
3. Chat or tap chips → when brief is ready: **Sahneye aktar** or **Aktar + kuyruğa al**.

These local servers power **Director / Rewrite only**. H3 video still needs Comfy + DiT weights.

**Music video from a song:** expand the Director dock → **Şarkı seç** → optional concept/lyrics → **Şarkıdan brief**. Studio measures loudness per clip window (not beat-sync) and the Director writes a silent continue chain (same face/wardrobe). Queue with **Üretime al**, keep **Devam zincirine ekle** on, then **Şarkılı final** to mux your track. Face/reference stills in Reference mode help identity further. H3 will not lipsync to the file.

One-time after update (if Studio deps missing):

```text
Pinokio → Install   (or: uv pip install -r studio/requirements.txt inside app/env)
```

Studio talks to Comfy at the URL captured on start (`COMFY_URL`). Bottom bar shows CPU / RAM / GPU / VRAM / disk (ACE-Step–style, horizontal).

## Usage

1. **Install** — the cloud-client installer installs only Studio on the PC. The managed Runpod bootstrap installs ComfyUI, cu130 dependencies, workflows and weights on the Pod. The local-CUDA/Pinokio installer puts that full stack on the PC instead.
2. **Start** — launches H3 Studio and either connects to Runpod or starts local ComfyUI, according to **Settings → Compute backend**.
3. In ComfyUI, the bundled workflows already have their models selected:

| Workflow | Mode | Transformer |
|---|---|---|
| **MiniMax H3 - Text to Video (sage3)** | text → video+audio | FL2VA |
| **MiniMax H3 - Image to Video (stock)** | first/last frame → video+audio | FL2VA |
| **MiniMax H3 - Reference to Video (sage3)** | omni-reference → video+audio | Ref2VA |

Ref2VA accepts up to 9 images, 3 video clips and 3 audio clips (12 files max, ≤15 s combined; audio can never be the only input).

These are the official Comfy-Org templates, unmodified except that the two `(sage3)` graphs have a **Patch Sage Attention KJ** node spliced between the `UNETLoader` and the model consumers, set to `sageattn3`. Set that node to **`disabled`** to A/B against stock attention.

> **Auto-open:** which workflow ComfyUI opens on launch is browser localStorage, not a file on disk, so it cannot be preset. ComfyUI's `Comfy.Workflow.Persist` setting (enabled here) reopens the last-used workflow — so open one of these once and it comes back automatically from then on.

**Reinstall Workflows** in the menu restores the three bundled graphs; it overwrites only those files and leaves your own saved workflows alone.

### Prompting

H3's quality depends heavily on prompt structure — the hosted pipeline runs a preprocessing model (H3-Context-IR) that expands your prompt into a long structured description with `integrated_multimodal_description`, `overall_soundscape` and `non_diegetic_music` sections. That module is **not open source**. To get comparable results locally, write prompts in that same structured style; see the prompting guides linked in the sidebar.

Spoken dialogue uses `<d>` tags, e.g. `<d>[English] Follow the wind, live free.</d>`

### LoRA (H3 Studio)

Production **Ayarlar**: named list — **click a LoRA to download it**, then **Uygula**. That attaches the file (and strength). **Steps stay whatever you typed** in the Steps box — a turbo LoRA can run at 4 or 10 (or any count). Sampler is also yours. The list still shows a recommended step count in the hint.

| LoRA | Size | What it does |
|---|---|---|
| **Yok** | — | Default 20 step · `res_multistep` |
| **LightX2V Turbo** | ~1.8 GB | FL2VA 4-step distill · `er_sde` · strength 0.75. New video / first-last only — skipped on Ref / V2V / face. |
| **ErosMax Turbo** | ~1.8 GB | FL2VA 4-step · same skip on Ref / face. |
| **H3 Turbo 6-step EMA** | ~0.8 GB | FL2VA 6-step · same skip on Ref / face. |
| **H3 Turbo v4 EMA** | ~0.7 GB | FL2VA turbo (`step600` is training, not 4 inference steps) — set steps yourself. |
| **H3 Realism People** | ~125 MB | T2V / I2V / Ref · keeps your step/sampler. |
| **Cinematic Look (DY)** | ~148 MB | Film texture · trigger `DY` · tensor-error fix · T2V + Ref. |
| **Better Motion** | ~296 MB | Movement quality · strength 0.4–0.8 · T2V + Ref. |
| **Spatial & Physics** | ~148 MB | Collision / gravity / objects · stacks with turbo. |
| **Ref2V Turbo (8 step)** | ~933 MB | Ref/face only · 8-step · skipped on T2V (fills the Ref turbo gap). |
| **Photoreal still** | ~148 MB | Character/location sheets only · trigger `ph0t0r34l` · **not** applied to the video queue. |
| **PinkFluffyBunny** | ~2.3 GB | Character LoRA · works on new video and Ref/face. |

Missing files download into `app/models/loras` from Hugging Face when you click the name (or **Uygula**). Same files are also in Pinokio **Download Models**.

Drop extra H3 `.safetensors` via **LoRA ekle**, paste a Hugging Face **resolve** URL into **URL’den al**, or copy the file into `app/models/loras` — they appear in the same list. Studio hides SDXL / Pony / Wan / Flux / ClipProj files; those are not MiniMax H3 video LoRAs. Catalog hints may mention 4-step / 6-step as a recommendation only.

Cinema studio has the **same LoRA list** next to duration/steps (film-wide; still-only rows stay in the shop). Character cards still have an optional per-character LoRA for Ref2VA identity shots. For a consistent person without a character LoRA, use **Yüz referansı** or a Direktör still (Ref2VA). If **Photoreal still** is on disk, sheet jobs pick it automatically.

**Post-pass (one, no community workflow JSON):** next to quality chips — **1.5× upscale** (`ImageScaleBy` lanczos) or **24→48 VFI** when a FILM/RIFE file is in `app/models/frame_interpolation`. Not both.

```text
GET  /api/loras
POST /api/loras/download   # { id } catalog entry with a url (downloadable: true)
POST /api/loras/upload     # multipart .safetensors
POST /api/loras/import     # { url, filename? } direct HF / .safetensors link
```

### H3 Multishot — Kesintisiz zincir (Seamless Chain)

[ComfyUI-H3-Multishot](https://github.com/jlucasmcrell/ComfyUI-H3-Multishot) (jlucasmcrell) is a **custom node pack**, not a LoRA. It welds 10–15s H3 blocks into **one take** (picture + audio, no cut at the join). Studio queues that as a single Comfy graph (`H3MultishotSampler`, CORE path — last-frame hand-off, no Motion-Context / JoyEcho). v2.7: decoded frames pass through **`H3ChainNormalize`** (colour/texture drift) and optional character **voice clips** (`voice_ref` / `_2` / `_3`) from the character card.

**Install (existing Pinokio install):** menu **Download Models → H3 Multishot (Seamless Chain) nodes**, or **Update**. Then **Stop → Start** so Comfy loads the pack.

**Cinema:** **Kesintisiz zincir** (on when the pack is present). Shot texts are joined with `---` and render as one clip per **take** (max 8 shots, e.g. 8×5s = 40s). In JSON, `takes[]` is the scene list of **one continuing film**: “5 sahneli” = 5 takes × 8 shots (Sahne 1…5), then concat. A flat `sections[]` list still auto-chunks every 8. Pack limit is 8 shots **per take**, not per film. Uncheck it to use the older per-shot Continue chain (last-frame I2V, up to 80 shots).

**Kesintisiz JSON** (`h3-cinema-seamless/v1`): Direktör → **JSON → Kesintisiz örnek**. You fill only `_user.scenes` + `_user.about`, send the file to an AI. It writes detailed author fields; Studio composes the official H3 three-block prompt (`integrated_multimodal_description` / `overall_soundscape` / `non_diegetic_music`). Delete `_instructions` + `_user`, import, then **Üret**. One Multishot job **per take**. Do not add portraits. The older **Film örneği** (`h3-cinema/v1`) is the face-lock package (same `_user` brief).

```text
GET  /api/cinema/json-template              # 12×5s Film (h3-cinema/v1)
GET  /api/cinema/json-template?kind=seamless  # takes[] Kesintisiz (h3-cinema-seamless/v1)
POST /api/cinema/import-json                # { payload, mode: replace|merge }
POST /api/cinema/produce                    # seamless: true → one job per take (max 8 shots each)
```

```javascript
const tmpl = await fetch("/api/cinema/json-template?kind=seamless").then((r) => r.json());
// fill tmpl.title / characters / takes[].sections, delete tmpl._instructions
await fetch("/api/cinema/import-json", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ payload: tmpl, mode: "replace" }),
});
await fetch("/api/cinema/produce", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ seamless: true, duration: 10, prepare_sheets: false }),
});
```

```python
import requests
base = "http://127.0.0.1:8787"
pkg = requests.get(f"{base}/api/cinema/json-template", params={"kind": "seamless"}).json()
pkg.pop("_instructions", None)
# fill pkg["title"], pkg["characters"], pkg["sections"]
requests.post(f"{base}/api/cinema/import-json", json={"payload": pkg, "mode": "replace"})
requests.post(f"{base}/api/cinema/produce", json={"seamless": True, "duration": 10, "prepare_sheets": False})
```

```bash
curl -s "http://127.0.0.1:8787/api/cinema/json-template?kind=seamless" -o take.json
# fill take.json, delete _instructions
curl -s -X POST http://127.0.0.1:8787/api/cinema/import-json \
  -H "Content-Type: application/json" \
  -d "{\"payload\":$(cat take.json),\"mode\":\"replace\"}"
```

Optional full v2 extras (LLM writer, `context_pin`, accelerators) stay out of Studio; CORE + v2.7 normalize / voice refs is enough for cinema. Continuum (chunked latent long-form) is not installed this round.

### Direktör · Sinema stüdyosu

**Sahne → Direktör** opens a two-column cinema studio for long-form films.

- **Sol sütun (üst/alt):** **Karakter ekle+** opens a card (name, description, reference still; optional character LoRA). **Mekan ekle+** is the same for locations (region name, description, still).
- **Film setup presets:** the first pill (**Ön ayar / Preset**) fills camera, color palette, lighting, era, purpose, style, and audio mode. You can still override any pill afterwards. **Auto** clears those locks.
- **Gallery delete** removes the card and the files: studio clip, last frame, Comfy `app/output/video/H3_Studio` copy, and uploaded last-frame stills.
- **Kalite:** duration, 480/720/1080, steps, film LoRA, and **Kesintisiz zincir** live in this panel and drive the queue.
- **Ses / müzik (Higgsfield film):** H3 cannot emit the *same* song on every shot — each clip invents a new score. **Diyalog + SFX** mode forbids generated BGM, locks each character’s **Ses tarifi** into every prompt, then you upload **one** film track and **Aynı müziği filme karıştır** after the queue finishes (dialogue stays; the score is mixed underneath). Do not use the music-video mux here — that *replaces* audio and kills speech.
- **Sağ sütun — shot listesi:** write a shot, then **+ Yeni video** (t2v / new chain) or **+ Continue** (last frame of the previous shot). Tags on each card can flip the mode later.
- Mention a character or location **name** in a shot — that still is attached on New Video shots (Ref2VA). Continue shots keep last-frame I2V and put identity in the prompt text.

#### Film modu — 1 dakikalık film reçetesi (TR)

Uzun filmlerde **New Video / Continue** ile uğraşmak yerine **Film modu** panelini kullan:

1. **Karakterler:** her role **2–3 yüz stilli** yükle; shot metninde çağrı adını kullan (`@Ayşe`).
2. **H3 Yönetmen:** “1 dakikalık film, 10 saniyelik klipler, karakterler …” de → Plan kaydet (**Sinema’ya aktar**).
3. **Film modu:** hedef **60 sn**, klip **10 sn**, segment **6 shot** (dengeli: 2 segment × 6).
4. **Otomatik devam/kes** açıkken shot kartlarında T2V/Continue gizlenir; sistem `linkToPrev` + yüz kilidini uygular.
5. **Film modu · kuyruğa al** → segment 1 kuyruğa girer; bitince segment 2 otomatik; **Bitince birleştir** ile tek MP4.
6. Yönetmen **Üretime al** (Sinema açıkken) artık düz batch yerine **`/api/cinema/produce`** kullanır (karakter stilleri + akıllı continue).

Still eksik karakterler sarı uyarı ile gösterilir — kimlik için still şart.

```text
POST /api/cinema/produce-film   # segmentli üretim (total_sec, clip_sec, segment_size)
GET  /api/cinema/film-plan      # segment durumu
POST /api/cinema/film-plan/concat
POST /api/clips/concat          # seçili klipleri birleştir
```

```javascript
// 1 dakika · 10 sn klip · 6’lı segment
await fetch("/api/cinema/produce-film", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    total_sec: 60,
    clip_sec: 10,
    segment_size: 6,
    reset_plan: true,
    auto_concat: true,
  }),
});
// Segment 2 otomatik (UI) veya:
await fetch("/api/cinema/produce-film", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ advance: true, reset_plan: false }),
});
await fetch("/api/cinema/film-plan/concat", { method: "POST" });
```

```python
import requests
base = "http://127.0.0.1:8787"
requests.post(f"{base}/api/cinema/produce-film", json={
    "total_sec": 60, "clip_sec": 10, "segment_size": 6, "reset_plan": True,
})
# … wait for segments …
requests.post(f"{base}/api/cinema/film-plan/concat")
```

```bash
curl -s -X POST http://127.0.0.1:8787/api/cinema/produce-film \
  -H "Content-Type: application/json" \
  -d '{"total_sec":60,"clip_sec":10,"segment_size":6,"reset_plan":true}'
```

```text
GET  /api/cinema
PUT  /api/cinema
POST /api/cinema/character
POST /api/cinema/location
POST /api/cinema/produce   # shots with take_index, or flat list packed every 8; seamless: true
                          # optional post_pass: "" | "upscale" | "vfi"
POST /api/cinema/produce-film
GET  /api/cinema/film-plan
POST /api/cinema/film-plan/concat
POST /api/cinema/mux       # concat clips, keep dialogue, mix one score
POST /api/clips/concat
GET  /api/cinema/final/{batch_id}
POST /api/director/chat            # plan_mode: true → shot tahtasını görür, patch ile düzenler
POST /api/director/plan            # { session_id, shots, apply_cinema } Plan kaydet / stüdyoya aktar
POST /api/director/commit          # cinema_studio → cinema/produce + face lock
GET  /api/llm/settings
GET  /api/llm/models               # ?provider=gemini|ollama|lmstudio|llamacpp|…  (does not switch saved provider)
POST /api/llm/settings             # provider: ollama | lmstudio | llamacpp | openai | nvidia | gemini | grok | claude
```

```javascript
await fetch("/api/llm/settings", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    provider: "lmstudio",
    lmstudio_base_url: "http://127.0.0.1:1234/v1",
    lmstudio_model: "google/gemma-4-e4b",
  }),
});
```

```python
import requests
requests.post("http://127.0.0.1:8787/api/llm/settings", json={
    "provider": "llamacpp",
    "llamacpp_base_url": "http://127.0.0.1:8080/v1",
    "llamacpp_model": "gemma-4-e4b",
})
```

```bash
curl -s -X POST http://127.0.0.1:8787/api/llm/settings \
  -H "Content-Type: application/json" \
  -d '{"provider":"lmstudio","lmstudio_base_url":"http://127.0.0.1:1234/v1"}'
```

```bash
# Curl — produce a film (dialogue+SFX, no generated BGM), then mix one score
curl -s -X POST http://127.0.0.1:8787/api/cinema/produce \
  -H "Content-Type: application/json" \
  -d '{"shots":[{"text":"Ada walks into Rooftop.","mode":"t2v"}],"audio":{"mode":"film","score_id":"MUSIC_ID"}}'

curl -s -X POST http://127.0.0.1:8787/api/cinema/mux \
  -H "Content-Type: application/json" \
  -d '{"batch_id":"BATCH","score_id":"MUSIC_ID"}'
```

```javascript
await fetch("/api/cinema/produce", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    shots: [{ text: "Ada walks into Rooftop.", mode: "t2v" }],
    audio: { mode: "film", score_id: musicId },
  }),
});
const mux = await fetch("/api/cinema/mux", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ score_id: musicId }),
}).then((r) => r.json());
window.open(mux.final_url);
```

```python
import requests
base = "http://127.0.0.1:8787"
requests.post(f"{base}/api/cinema/produce", json={
    "shots": [{"text": "Ada walks into Rooftop.", "mode": "t2v"}],
    "audio": {"mode": "film", "score_id": music_id},
})
mux = requests.post(f"{base}/api/cinema/mux", json={"score_id": music_id}).json()
print(mux["final_url"])
```

### Resolution — you are not capped at 768p

The nodes take explicit `width` / `height` inputs (default **1344×768**, max `MAX_RESOLUTION` = 16384), so you can generate natively at 1920×1088 or higher. 768 is the *default* short edge and the resolution H3 was primarily trained at — not a ceiling.

The `MAX_PIXELS = 768*1344` constant in `nodes_minimax_h3.py` is easy to misread: it lives in `adapt_canvas()`, which is called in exactly one place — sizing **reference video** clips in the Ref2VA node. It never touches your output canvas.

Cost scales steeply with pixel count. Community figures on a 32 GB RTX 5090 at 1920×1088, INT8:

| Job | Time |
|---|---|
| 5 s, with sage-attention | ~8.4 min |
| 10 s, with sage-attention | ~23 min |
| 10 s, 20 steps, without | ~58 min |

So 1080p is very much usable — it just costs time, and quality is reportedly better than 768p. Practical levers (besides LoRA): **shorter clips**, **480p/720p**, **15 steps**, **silent decode** on music videos. Studio has **Taslak** (5s · 480p · 12) and **Hızlı** (5s · 720p · 15). Studio graphs do **not** patch Sage Attention.

See **SageAttention 3** below if you want those kernels in Comfy itself; H3 Studio no longer uses them.

At 1080p the working set exceeds 32 GB of VRAM, so ComfyUI offloads to system RAM. Your 93 GB is comfortable for this.

### SageAttention 3 (Blackwell FP4) — optional, menu-installable

RTX 50-series only. **Install SageAttention 3** in the menu builds the FP4 attention kernels from source. Measured on this exact stack (RTX 5090, sm_120, torch 2.13.0+cu130), sage3 vs PyTorch SDPA:

| shape (B,H,L,D) | pytorch | sage3 | speedup |
|---|---|---|---|
| (1, 24, 4096, 128) | 1.25 ms | 0.51 ms | **2.44×** |
| (1, 24, 16384, 128) | 18.54 ms | 6.03 ms | **3.07×** |
| (1, 16, 32768, 128) | 48.77 ms | 14.70 ms | **3.32×** |

The gain grows with sequence length — H3 packs video and audio into one long sequence, so higher resolution and longer clips benefit most.

**What the script does:** installs a private CUDA 13.0 toolkit into `./cuda13` (~4.9 GB), clones `thu-ml/SageAttention`, compiles `sageattn3` for `sm_120a` (CUTLASS is auto-cloned; 15–25 min), installs the wheel, adds ComfyUI-KJNodes, then runs a live kernel check before marking success.

The private toolkit is required because `torch/utils/cpp_extension.py` **raises** on a CUDA *major* mismatch, and Pinokio's bundled nvcc is 12.8 while our torch is cu130. Toolkit 13.0 matches torch's 13.0 exactly — not even a minor-version warning.

**How to actually use it.** `--use-sage-attention` will *not* select it — that flag picks SageAttention 1/2 and needs the separate `sageattention` package. ComfyUI registers this build as the `sage3` attention function, selected per-model via `transformer_options["optimized_attention_override"]`. Add KJNodes' **"Patch Sage Attention KJ"** node between your model loader and the sampler, mode **`sageattn3`**.

**Caveats, honestly:**
- Upstream validates SageAttention 3 on CogVideoX-2B, HunyuanVideo, Mochi and image models. **MiniMax H3 is not on that list**, and upstream explicitly warns it "does not guarantee lossless acceleration for all models." A/B it before trusting it on final renders.
- Against reference SDPA on random tensors it shows ~19% mean relative deviation. That is inherent to 4-bit attention and the metric is harsh on random inputs (real attention is far more peaked), but it is not free.
- ComfyUI bypasses it entirely when `dim_head >= 256 or N <= 1024` (`attention.py:643`), falling back to PyTorch attention.
- The widely-circulated WSL2 build report needs `PYTORCH_CUDA_ALLOC_CONF=backend:native` and a `libcuda.so` symlink. **Neither applies here** — verified working under ComfyUI's default `cudaMallocAsync` on native Linux. That report also predates official cu130 wheels (it built PyTorch from source) and concluded the low-level `fp4attn_cuda` / `fp4quant_cuda` kernels were unavailable; this build produces both.

### Not included

**H3-Regenerate-2K** has not been open-sourced by MiniMax. That is the *in-context regeneration* module — it feeds the 768p result plus the original context back through H3 to recover fine detail (small text, textures) that plain upscaling has to invent. Generating directly at high resolution, as above, is a different and cruder path to a big frame; it does not reproduce what Regenerate-2K does. The official 2K pipeline remains API-only.

---

## Menu

| Item | Effect |
|---|---|
| **Start** | Launch ComfyUI |
| **Download Models** | Fetch any variant not currently on disk |
| **Manage Disk Space** | Delete either transformer independently (21 GB each), re-downloadable later |
| **Update** | `git pull` ComfyUI + Manager, reinstall deps, restore cu130 torch |
| **Reset** | Delete ComfyUI and its venv. **Weights are kept** — they live on a Pinokio virtual drive, so a reset does not re-download 63 GB |

Weights are stored on a virtual drive under `PINOKIO_HOME/drive/drives/peers/`, linked into `app/models/`. Any peer ComfyUI install shares the same files rather than duplicating them.

---

## Troubleshooting

### Web UI is blank inside the Pinokio app, but works in an external browser

Not a launcher fault — Pinokio's HTTPS reverse proxy (**Caddy**) is missing. Caddy is what serves the `http://localhost:<PORT>` → `https://<PORT>.localhost` endpoints that Pinokio's *embedded* browser loads. Without it the webview has nothing to fetch, while `http://127.0.0.1:<PORT>` keeps working fine in a normal browser.

This affects **every** Pinokio app, not just this one — a quick way to confirm is to open another installed app's Web UI and see if it is blank too.

Diagnose:

```bash
grep -i caddy ~/pinokio/logs/stdout.txt | tail -3
#   caddy version undefined
#   caddy coerced null
#   caddy satisfied? false        <- proxy unavailable

curl -s -o /dev/null -w '%{http_code}\n' http://localhost:2019/config/   # Caddy admin API
pterm which caddy                                                        # should print a path
```

Fix — install Caddy where Pinokio looks for it, then **restart Pinokio** so it re-runs the dependency check and starts the proxy:

```bash
conda install -y -n base -c conda-forge caddy
```

(A distro package works too — on Arch/CachyOS `caddy` is in the repos — but the conda route matches how Pinokio manages its other bundled binaries and is what its `satisfied?` check inspects.)

Verify after restarting: `pterm which caddy` resolves, `http://localhost:2019/config/` answers, and `https://<PORT>.localhost` loads.

### Checking the app is actually up

`http://127.0.0.1:8188` returning HTTP 200 means ComfyUI is healthy regardless of what the embedded view shows. If the sidebar shows **Open Web UI**, `start.js` captured the URL correctly and the launcher is working.

## API

Cloud Edition exposes compute management through the local Studio API (normally `http://127.0.0.1:8787`):

```bash
# Read the active backend (secrets are always masked)
curl http://127.0.0.1:8787/api/runpod/settings

# Select Runpod and attach an existing Pod
curl -X POST http://127.0.0.1:8787/api/runpod/settings \
  -H "Content-Type: application/json" \
  -d '{"provider":"runpod","api_key":"rpa_...","pod_id":"POD_ID","access_token":"TOKEN"}'

# Test, start, or stop it
curl -X POST http://127.0.0.1:8787/api/runpod/test
curl -X POST http://127.0.0.1:8787/api/runpod/pod/start
curl -X POST http://127.0.0.1:8787/api/runpod/pod/stop
```

Python and JavaScript use the same JSON endpoints:

```python
import requests
requests.post("http://127.0.0.1:8787/api/runpod/test").raise_for_status()
```

```javascript
const status = await fetch("http://127.0.0.1:8787/api/runpod/test", { method: "POST" });
console.log(await status.json());
```

ComfyUI exposes an HTTP API on the same port as the web UI. The reliable way to build a request body:

1. Open an H3 template in ComfyUI and configure it.
2. Enable **Settings → Lite Graph → Enable dev mode options**.
3. **Workflow → Export (API)** to save `workflow_api.json`.

That file is the `prompt` object below. Find node IDs for the prompt text and the model loader by matching the `class_type` / `_meta.title` fields, then overwrite their `inputs` per request.

Replace `PORT` with the port shown in the Pinokio terminal.

### curl

```bash
BASE=http://127.0.0.1:PORT

# Queue a job. workflow_api.json must be wrapped as {"prompt": {...}}
PROMPT_ID=$(jq -n --slurpfile w workflow_api.json '{prompt: $w[0]}' \
  | curl -s -X POST "$BASE/prompt" -H 'Content-Type: application/json' -d @- \
  | jq -r '.prompt_id')

# Poll until the job appears in history
until curl -s "$BASE/history/$PROMPT_ID" | jq -e 'keys|length>0' >/dev/null; do sleep 5; done

# Download every output file the job produced
curl -s "$BASE/history/$PROMPT_ID" \
  | jq -r --arg id "$PROMPT_ID" '.[$id].outputs[] | (.gifs//.videos//.images//[])[]
      | "filename=\(.filename)&subfolder=\(.subfolder)&type=\(.type)"' \
  | while read -r q; do
      curl -s -o "$(echo "$q" | sed 's/.*filename=\([^&]*\).*/\1/')" "$BASE/view?$q"
    done
```

### Python

```python
import json, time, requests

BASE = "http://127.0.0.1:PORT"

with open("workflow_api.json") as f:
    prompt = json.load(f)

# Example: point the positive prompt node at new text.
# Look up the real node id in your exported workflow.
prompt["6"]["inputs"]["text"] = (
    "[Shot 1] Cinematic wide shot, slow push in. "
    "<d>[English] Follow the wind, live free.</d>"
)

prompt_id = requests.post(f"{BASE}/prompt", json={"prompt": prompt}).json()["prompt_id"]

while True:
    history = requests.get(f"{BASE}/history/{prompt_id}").json()
    if history:
        break
    time.sleep(5)

for node in history[prompt_id]["outputs"].values():
    for item in node.get("gifs", []) + node.get("videos", []) + node.get("images", []):
        data = requests.get(f"{BASE}/view", params={
            "filename":  item["filename"],
            "subfolder": item["subfolder"],
            "type":      item["type"],
        }).content
        with open(item["filename"], "wb") as f:
            f.write(data)
        print("saved", item["filename"])
```

### JavaScript

```javascript
import fs from "node:fs/promises";

const BASE = "http://127.0.0.1:PORT";

const prompt = JSON.parse(await fs.readFile("workflow_api.json", "utf8"));
prompt["6"].inputs.text = "[Shot 1] Cinematic wide shot, slow push in.";

const res = await fetch(`${BASE}/prompt`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ prompt }),
});
const { prompt_id } = await res.json();

let history;
while (true) {
  history = await (await fetch(`${BASE}/history/${prompt_id}`)).json();
  if (Object.keys(history).length) break;
  await new Promise((r) => setTimeout(r, 5000));
}

for (const node of Object.values(history[prompt_id].outputs)) {
  for (const item of [...(node.gifs ?? []), ...(node.videos ?? []), ...(node.images ?? [])]) {
    const q = new URLSearchParams({
      filename: item.filename,
      subfolder: item.subfolder,
      type: item.type,
    });
    const buf = Buffer.from(await (await fetch(`${BASE}/view?${q}`)).arrayBuffer());
    await fs.writeFile(item.filename, buf);
    console.log("saved", item.filename);
  }
}
```

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/prompt` | Queue `{"prompt": <workflow_api>}`; returns `prompt_id` |
| `GET` | `/history/{prompt_id}` | Job result; empty object until finished |
| `GET` | `/view?filename=&subfolder=&type=` | Fetch an output file |
| `GET` | `/queue` | Current queue state |
| `POST` | `/interrupt` | Cancel the running job |
| `WS` | `/ws?clientId=` | Live progress events |

---

## Special Thanks

Warm thanks to the community members whose bug reports and feature ideas helped improve MiniMax H3 Studio:

- sikoraentertainment
- Boloschniposa
- diamond204a
- anth7777
- mangpepe1945-stack

Your feedback on video continuation, file selection, queue control, LoRAs, scene workflow, translations, and rendering reliability directly shaped these updates.

---

## License

The model is covered by the [MiniMax H3 Community License](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE). Review it before commercial use. ComfyUI is GPL-3.0.
