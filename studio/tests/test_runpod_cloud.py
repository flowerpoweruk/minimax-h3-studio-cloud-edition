from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from lib.runpod_cloud import DEFAULT_IMAGE, RunpodCloud


class RecordingRunpodCloud(RunpodCloud):
    def __init__(self, path: Path):
        super().__init__(path)
        self.calls = []

    async def _request(self, method: str, path: str, *, json_body=None):
        self.calls.append((method, path, json_body))
        if method == "POST" and path == "pods":
            return {"id": "pod-cloud-123", "desiredStatus": "RUNNING"}
        return {"id": "pod-cloud-123"}


class RunpodCloudTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "runpod_settings.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_defaults_to_local_without_exposing_secrets(self):
        cloud = RunpodCloud(self.path)
        public = cloud.public()
        self.assertEqual(public["provider"], "local")
        self.assertEqual(public["comfy_url"], "http://127.0.0.1:8188")
        self.assertNotIn("api_key", public)
        self.assertNotIn("access_token", public)

    def test_runpod_url_and_bearer_header(self):
        cloud = RunpodCloud(self.path)
        public = cloud.save(
            {
                "provider": "runpod",
                "api_key": "rpa_test_secret_value",
                "pod_id": "abc123",
                "access_token": "cloud-secret-token",
            }
        )
        self.assertEqual(public["comfy_url"], "https://abc123-8188.proxy.runpod.net")
        self.assertEqual(cloud.comfy_headers, {"Authorization": "Bearer cloud-secret-token"})
        self.assertNotIn("rpa_test_secret_value", json.dumps(public))
        self.assertNotIn("cloud-secret-token", json.dumps(public))

    def test_create_managed_pod_persists_id_and_auth(self):
        cloud = RecordingRunpodCloud(self.path)
        cloud.save({"provider": "runpod", "api_key": "rpa_test", "volume_gb": 160})
        pod = asyncio.run(cloud.create_pod())
        self.assertEqual(pod["id"], "pod-cloud-123")
        self.assertEqual(cloud.pod_id, "pod-cloud-123")
        self.assertTrue(cloud.public()["access_token_set"])
        method, path, body = cloud.calls[-1]
        self.assertEqual((method, path), ("POST", "pods"))
        self.assertEqual(body["image"], DEFAULT_IMAGE)
        self.assertEqual(body["mounts"]["persistent"]["size"], 160)
        self.assertEqual(body["ports"], ["8188/http"])
        self.assertFalse(body["startSsh"])
        self.assertEqual(body["gpu"]["allowedCudaVersions"], ["13.0"])
        self.assertIn("H3_CLOUD_TOKEN", body["env"])
        self.assertNotIn("args", body)
        self.assertTrue(body["image"].startswith("ghcr.io/flowerpoweruk/"))

    def test_network_volume_rejects_community_cloud_before_api_call(self):
        cloud = RecordingRunpodCloud(self.path)
        cloud.save(
            {
                "provider": "runpod",
                "api_key": "rpa_test",
                "cloud_type": "COMMUNITY",
                "network_volume_id": "network-volume-123",
            }
        )
        with self.assertRaisesRegex(ValueError, "require Secure Cloud"):
            asyncio.run(cloud.create_pod())
        self.assertEqual(cloud.calls, [])

    def test_legacy_stock_image_is_migrated_to_prebuilt_runtime(self):
        self.path.write_text(
            json.dumps({"image": "runpod/pytorch:1.0.3-cu1300-torch291-ubuntu2404"}),
            encoding="utf-8",
        )
        cloud = RunpodCloud(self.path)
        self.assertEqual(cloud.public()["image"], DEFAULT_IMAGE)

    def test_running_stock_pod_reports_missing_comfy_port(self):
        cloud = RunpodCloud(self.path)
        cloud.save(
            {
                "provider": "runpod",
                "pod_id": "stock-pod",
                "endpoint_url": "https://stock-pod-8188.proxy.runpod.net",
            }
        )
        pod = {
            "id": "stock-pod",
            "status": "RUNNING",
            "ports": ["8888/http", "22/tcp"],
            "runtime": {"ports": [{"private": 8888, "type": "http"}]},
        }
        diagnostic = cloud.readiness_diagnostic(pod, online=False)
        self.assertEqual(diagnostic["code"], "comfy_port_missing")
        self.assertIn("stock PyTorch/Jupyter Pod is not enough", diagnostic["message"])
        self.assertFalse(diagnostic["comfy_port_exposed"])

    def test_managed_pod_can_report_setup_still_running(self):
        cloud = RunpodCloud(self.path)
        cloud.save({"provider": "runpod", "pod_id": "managed-pod"})
        pod = {"id": "managed-pod", "status": "RUNNING", "ports": ["8188/http"]}
        diagnostic = cloud.readiness_diagnostic(pod, online=False)
        self.assertEqual(diagnostic["code"], "comfy_not_ready")
        self.assertTrue(diagnostic["comfy_port_exposed"])

    def test_public_pod_does_not_expose_environment_or_ssh(self):
        pod = {
            "id": "pod-1",
            "status": "RUNNING",
            "ports": ["8188/http"],
            "env": {"JUPYTER_PASSWORD": "secret"},
            "ssh": {"proxy": {"command": "secret-command"}},
        }
        public = RunpodCloud.public_pod(pod)
        self.assertEqual(public["id"], "pod-1")
        self.assertNotIn("env", public)
        self.assertNotIn("ssh", public)
        self.assertNotIn("secret", json.dumps(public))


if __name__ == "__main__":
    unittest.main()
