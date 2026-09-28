"""Bearer-token reverse proxy exposing a private ComfyUI API on Runpod."""
from __future__ import annotations

import asyncio
import os
from typing import Iterable

from aiohttp import ClientSession, ClientTimeout, WSMsgType, web


UPSTREAM = os.getenv("H3_COMFY_UPSTREAM", "http://127.0.0.1:8189").rstrip("/")
TOKEN = os.getenv("H3_CLOUD_TOKEN", "").strip()
HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "authorization",
}


def _headers(items: Iterable[tuple[str, str]]) -> dict[str, str]:
    return {k: v for k, v in items if k.lower() not in HOP_HEADERS}


@web.middleware
async def require_token(request: web.Request, handler):
    if not TOKEN:
        return web.json_response({"error": "H3_CLOUD_TOKEN is not configured"}, status=503)
    if request.headers.get("Authorization", "") != f"Bearer {TOKEN}":
        return web.json_response({"error": "unauthorized"}, status=401)
    return await handler(request)


async def websocket_proxy(request: web.Request) -> web.WebSocketResponse:
    downstream = web.WebSocketResponse(max_msg_size=8 * 1024 * 1024)
    await downstream.prepare(request)
    upstream_url = UPSTREAM.replace("http://", "ws://").replace("https://", "wss://")
    upstream_url += request.rel_url.path_qs
    async with request.app["client"].ws_connect(upstream_url, max_msg_size=8 * 1024 * 1024) as upstream:
        async def down_to_up():
            async for msg in downstream:
                if msg.type == WSMsgType.TEXT:
                    await upstream.send_str(msg.data)
                elif msg.type == WSMsgType.BINARY:
                    await upstream.send_bytes(msg.data)
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                    break

        async def up_to_down():
            async for msg in upstream:
                if msg.type == WSMsgType.TEXT:
                    await downstream.send_str(msg.data)
                elif msg.type == WSMsgType.BINARY:
                    await downstream.send_bytes(msg.data)
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                    break

        tasks = [asyncio.create_task(down_to_up()), asyncio.create_task(up_to_down())]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*done, *pending, return_exceptions=True)
    return downstream


async def http_proxy(request: web.Request) -> web.StreamResponse:
    if request.path == "/ws":
        return await websocket_proxy(request)
    url = UPSTREAM + request.rel_url.path_qs
    body = request.content.iter_chunked(1024 * 1024)
    async with request.app["client"].request(
        request.method,
        url,
        headers=_headers(request.headers.items()),
        data=body,
        allow_redirects=False,
    ) as response:
        downstream = web.StreamResponse(
            status=response.status,
            reason=response.reason,
            headers=_headers(response.headers.items()),
        )
        await downstream.prepare(request)
        async for chunk in response.content.iter_chunked(1024 * 1024):
            await downstream.write(chunk)
        await downstream.write_eof()
        return downstream


async def client_context(app: web.Application):
    app["client"] = ClientSession(timeout=ClientTimeout(total=None, connect=30))
    yield
    await app["client"].close()


def main() -> None:
    app = web.Application(middlewares=[require_token], client_max_size=2 * 1024**3)
    app.cleanup_ctx.append(client_context)
    app.router.add_route("*", "/{path:.*}", http_proxy)
    web.run_app(
        app,
        host="0.0.0.0",
        port=int(os.getenv("H3_PROXY_PORT", "8188")),
        access_log=None,
    )


if __name__ == "__main__":
    main()
