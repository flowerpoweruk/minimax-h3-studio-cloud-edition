"""Runpod Pod settings and lifecycle management for H3 Studio Cloud Edition."""
from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any, Optional

import httpx


RUNPOD_API = "https://api.runpod.io/v2"
DEFAULT_IMAGE = "ghcr.io/flowerpoweruk/minimax-h3-studio-cloud-edition:runpod-v1.0.0"
DEFAULT_GPU = "NVIDIA RTX PRO 6000 Blackwell Server Edition"
LEGACY_RUNTIME_IMAGES = {
    "runpod/pytorch:1.0.3-cu1300-torch291-ubuntu2404",
}


def _mask(value: str, *, keep: int = 4) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if len(value) <= keep * 2:
        return "•" * len(value)
    return f"{value[:keep]}…{value[-keep:]}"


def _http_url(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
        value = "https://" + value.lstrip("/")
    return value.rstrip("/")


class RunpodCloud:
    """Persists cloud settings without ever returning secrets to the browser."""

    def __init__(self, path: Path, *, local_url: str = "http://127.0.0.1:8188"):
        self.path = Path(path)
        self.local_url = _http_url(local_url) or "http://127.0.0.1:8188"
        self._settings = self._load()

    @staticmethod
    def defaults() -> dict[str, Any]:
        return {
            "provider": "local",
            "api_key": "",
            "pod_id": "",
            "endpoint_url": "",
            "access_token": "",
            "gpu_type": DEFAULT_GPU,
            "cloud_type": "SECURE",
            "volume_gb": 150,
            "network_volume_id": "",
            "image": DEFAULT_IMAGE,
        }

    def _load(self) -> dict[str, Any]:
        data = self.defaults()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data.update(raw)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        # Existing Cloud Edition installs used a stock PyTorch image plus a
        # long startup bootstrap. Transparently move those settings to the
        # pinned, prebuilt runtime; custom user-supplied images stay untouched.
        if str(data.get("image") or "").strip() in LEGACY_RUNTIME_IMAGES:
            data["image"] = DEFAULT_IMAGE
        data["provider"] = "runpod" if data.get("provider") == "runpod" else "local"
        return data

    def save(self, patch: dict[str, Any]) -> dict[str, Any]:
        allowed = set(self.defaults())
        for key, value in patch.items():
            if key not in allowed or value is None:
                continue
            if key in {"volume_gb"}:
                self._settings[key] = max(80, min(1000, int(value)))
            else:
                self._settings[key] = str(value).strip()
        self._settings["provider"] = (
            "runpod" if self._settings.get("provider") == "runpod" else "local"
        )
        self._settings["cloud_type"] = (
            "COMMUNITY" if self._settings.get("cloud_type") == "COMMUNITY" else "SECURE"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._settings, indent=2), encoding="utf-8")
        tmp.replace(self.path)
        return self.public()

    def ensure_access_token(self) -> str:
        token = str(self._settings.get("access_token") or "").strip()
        if not token:
            token = secrets.token_urlsafe(32)
            self.save({"access_token": token})
        return token

    @property
    def provider(self) -> str:
        return str(self._settings.get("provider") or "local")

    @property
    def api_key(self) -> str:
        return str(self._settings.get("api_key") or "").strip()

    @property
    def pod_id(self) -> str:
        return str(self._settings.get("pod_id") or "").strip()

    @property
    def endpoint_url(self) -> str:
        explicit = _http_url(str(self._settings.get("endpoint_url") or ""))
        if explicit:
            return explicit
        if self.pod_id:
            return f"https://{self.pod_id}-8188.proxy.runpod.net"
        return ""

    @property
    def comfy_url(self) -> str:
        if self.provider == "runpod" and self.endpoint_url:
            return self.endpoint_url
        return self.local_url

    @property
    def comfy_headers(self) -> dict[str, str]:
        token = str(self._settings.get("access_token") or "").strip()
        if self.provider == "runpod" and token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def public(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "api_key_set": bool(self.api_key),
            "api_key_masked": _mask(self.api_key),
            "pod_id": self.pod_id,
            "endpoint_url": self.endpoint_url,
            "access_token_set": bool(self._settings.get("access_token")),
            "access_token_masked": _mask(str(self._settings.get("access_token") or "")),
            "gpu_type": self._settings.get("gpu_type") or DEFAULT_GPU,
            "cloud_type": self._settings.get("cloud_type") or "SECURE",
            "volume_gb": int(self._settings.get("volume_gb") or 150),
            "network_volume_id": self._settings.get("network_volume_id") or "",
            "image": self._settings.get("image") or DEFAULT_IMAGE,
            "comfy_url": self.comfy_url,
        }

    @staticmethod
    def public_pod(pod: dict[str, Any]) -> dict[str, Any]:
        """Return lifecycle details without forwarding Pod secrets to the browser."""
        if not isinstance(pod, dict):
            return {}
        return {
            key: pod.get(key)
            for key in (
                "id",
                "name",
                "status",
                "desiredStatus",
                "image",
                "cloud",
                "ports",
                "gpu",
                "createdAt",
                "startedAt",
            )
            if pod.get(key) is not None
        }

    @staticmethod
    def _pod_exposes_port(pod: dict[str, Any], port: int) -> bool:
        expected = str(port)
        for item in pod.get("ports") or []:
            if isinstance(item, str) and item.split("/", 1)[0] == expected:
                return True
            if isinstance(item, dict) and str(item.get("private") or "") == expected:
                return True
        runtime = pod.get("runtime") or {}
        for item in runtime.get("ports") or []:
            if isinstance(item, dict) and str(item.get("private") or "") == expected:
                return True
        return False

    def readiness_diagnostic(
        self,
        pod: Optional[dict[str, Any]] = None,
        *,
        online: bool = False,
        pod_error: str = "",
    ) -> dict[str, Any]:
        """Explain the difference between a reachable Pod and ready ComfyUI."""
        pod = pod if isinstance(pod, dict) else {}
        status = str(pod.get("status") or pod.get("desiredStatus") or "").upper()
        saved_endpoint = _http_url(str(self._settings.get("endpoint_url") or ""))
        derived_endpoint = (
            f"https://{self.pod_id}-8188.proxy.runpod.net" if self.pod_id else ""
        )
        custom_endpoint = bool(saved_endpoint and saved_endpoint != derived_endpoint)
        port_exposed = self._pod_exposes_port(pod, 8188)
        if online:
            return {
                "code": "ready",
                "message": f"Runpod ComfyUI connected at {self.comfy_url}.",
                "pod_status": status,
                "comfy_port_exposed": port_exposed,
            }
        if pod_error:
            return {
                "code": "pod_api_error",
                "message": f"Runpod API error: {pod_error}",
                "pod_status": status,
                "comfy_port_exposed": port_exposed,
            }
        if not self.pod_id:
            message = "No Runpod Pod is attached. Create a managed Pod or enter an existing Pod ID."
            code = "pod_missing"
        elif not pod:
            message = "The Runpod API key or Pod ID could not be verified. Check them, save, and test again."
            code = "pod_unverified"
        elif status and status != "RUNNING":
            message = f"Pod {self.pod_id} is {status}. Start it, wait for setup, then press Test again."
            code = "pod_not_running"
        elif not custom_endpoint and not port_exposed:
            message = (
                f"Pod {self.pod_id} is running, but it does not expose ComfyUI on port 8188. "
                "A stock PyTorch/Jupyter Pod is not enough. Use Create managed Pod, or install "
                "Cloud Edition on this Pod and expose 8188/http."
            )
            code = "comfy_port_missing"
        else:
            message = (
                f"Pod {self.pod_id} is running, but ComfyUI has not responded at {self.comfy_url}. "
                "If this is a managed Pod, its first setup may still be downloading the H3 models."
            )
            code = "comfy_not_ready"
        return {
            "code": code,
            "message": message,
            "pod_status": status,
            "comfy_port_exposed": port_exposed,
        }

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError("Runpod API key is not configured")
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def _request(
        self, method: str, path: str, *, json_body: Optional[dict] = None
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.request(
                method,
                f"{RUNPOD_API}/{path.lstrip('/')}",
                headers=self._headers(),
                json=json_body,
            )
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail") or response.json().get("title")
            except Exception:
                detail = response.text
            raise RuntimeError(f"Runpod {response.status_code}: {detail or 'request failed'}")
        if response.status_code == 204 or not response.content:
            return {}
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}

    async def pod(self) -> dict[str, Any]:
        if not self.pod_id:
            return {}
        return await self._request("GET", f"pods/{self.pod_id}")

    async def list_pods(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "pods")
        return list(data.get("pods") or [])

    async def pod_action(self, action: str) -> dict[str, Any]:
        if action not in {"start", "stop"}:
            raise ValueError("action must be start or stop")
        if not self.pod_id:
            raise ValueError("Runpod Pod ID is not configured")
        return await self._request(
            "POST", f"pods/{self.pod_id}/action", json_body={"action": action}
        )

    async def create_pod(self) -> dict[str, Any]:
        token = self.ensure_access_token()
        settings = self._settings
        cloud_type = str(settings.get("cloud_type") or "SECURE").upper()
        network_volume_id = str(settings.get("network_volume_id") or "").strip()
        if network_volume_id and cloud_type != "SECURE":
            raise ValueError(
                "Runpod Network Volumes require Secure Cloud. Select Secure Cloud "
                "or clear the Network Volume ID before creating a Pod."
            )
        network_volume: dict[str, Any] = {}
        if network_volume_id:
            network_volume = await self._request(
                "GET", f"network-volumes/{network_volume_id}"
            )
            data_center = str(network_volume.get("dataCenter") or "").strip()
            if not data_center:
                raise RuntimeError(
                    "Runpod did not return a datacenter for the configured Network "
                    "Volume; refusing to create a Pod with uncertain storage placement."
                )
        body: dict[str, Any] = {
            "name": "minimax-h3-studio-cloud-edition",
            "image": settings.get("image") or DEFAULT_IMAGE,
            "cloud": cloud_type,
            "disk": 40,
            "ports": ["8188/http"],
            "startSsh": False,
            # Managed Pods install both T2V and reference-video weights once so
            # every Studio mode works after a restart without another setup.
            "env": {
                "H3_CLOUD_TOKEN": token,
                "H3_DOWNLOAD_REF2V": "1",
                "H3_ALLOW_MODEL_DOWNLOAD": "1",
            },
            "gpu": {
                "id": settings.get("gpu_type") or DEFAULT_GPU,
                "count": 1,
                "allowedCudaVersions": ["13.0"],
            },
        }
        if network_volume_id:
            body["mounts"] = {
                "network": [{"volumeId": network_volume_id, "path": "/workspace"}]
            }
            body["dataCenterIds"] = [str(network_volume["dataCenter"])]
        else:
            body["mounts"] = {
                "persistent": {
                    "size": int(settings.get("volume_gb") or 150),
                    "path": "/workspace",
                }
            }
        pod = await self._request("POST", "pods", json_body=body)
        pod_id = str(pod.get("id") or "").strip()
        if pod_id:
            self.save({"pod_id": pod_id, "endpoint_url": "", "provider": "runpod"})
        return pod
