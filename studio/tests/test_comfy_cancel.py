import asyncio
import unittest
from unittest.mock import patch

from lib.comfy import ComfyClient


class _Response:
    status_code = 200
    content = b'{"cancelled": true}'

    def json(self):
        return {"cancelled": True}

    def raise_for_status(self):
        return None


class _AsyncClient:
    def __init__(self, calls, *args, **kwargs):
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _Response()


class ComfyCancelTests(unittest.TestCase):
    def test_cancel_prompt_uses_targeted_job_endpoint(self):
        calls = []
        client = ComfyClient("https://example.invalid", headers={"Authorization": "Bearer test"})
        with patch(
            "lib.comfy.httpx.AsyncClient",
            side_effect=lambda *args, **kwargs: _AsyncClient(calls, *args, **kwargs),
        ):
            cancelled = asyncio.run(client.cancel_prompt("prompt-123"))

        self.assertTrue(cancelled)
        self.assertEqual(calls, [("https://example.invalid/api/jobs/prompt-123/cancel", {})])

    def test_interrupt_sends_prompt_id_when_known(self):
        calls = []
        client = ComfyClient("https://example.invalid")
        with patch(
            "lib.comfy.httpx.AsyncClient",
            side_effect=lambda *args, **kwargs: _AsyncClient(calls, *args, **kwargs),
        ):
            asyncio.run(client.interrupt("prompt-456"))

        self.assertEqual(
            calls,
            [("https://example.invalid/interrupt", {"json": {"prompt_id": "prompt-456"}})],
        )


if __name__ == "__main__":
    unittest.main()
