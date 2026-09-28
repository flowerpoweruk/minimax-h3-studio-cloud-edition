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
        self.assertEqual(body["ports"], ["8188/http", "22/tcp"])
        self.assertIn("H3_CLOUD_TOKEN", body["env"])
        self.assertIn("runpod/bootstrap.sh", body["args"])


if __name__ == "__main__":
    unittest.main()
