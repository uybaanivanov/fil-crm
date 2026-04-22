"""Клиент локального MoreLogin API (http://127.0.0.1:40000).

Дока: https://guide.morelogin.com/api-reference/local-api/local-api
Контракт ответа: {"code": 0, "msg": null, "data": {...}, "requestId": "..."}.
Ошибка — любой code != 0 или HTTP != 200.
"""
import os
from dataclasses import dataclass

import httpx

API_URL = os.environ.get("MORELOGIN_API_URL", "http://127.0.0.1:40000")
ENV_ID = os.environ.get("MORELOGIN_ENV_ID", "")
TIMEOUT = httpx.Timeout(60.0)


class MoreLoginError(RuntimeError):
    pass


@dataclass
class ProfileSession:
    env_id: str
    debug_port: int
    cdp_url: str  # http://127.0.0.1:<debug_port>


def _unwrap(r: httpx.Response) -> dict:
    if r.status_code != 200:
        raise MoreLoginError(f"http {r.status_code}: {r.text}")
    body = r.json()
    if body.get("code") != 0:
        raise MoreLoginError(f"api error: {body}")
    return body.get("data") or {}


async def start_profile(env_id: str | None = None) -> ProfileSession:
    eid = env_id or ENV_ID
    if not eid:
        raise MoreLoginError("MORELOGIN_ENV_ID не задан")
    async with httpx.AsyncClient(base_url=API_URL, timeout=TIMEOUT) as c:
        data = _unwrap(await c.post("/api/env/start", json={"envId": eid}))
    port = int(data["debugPort"])
    return ProfileSession(env_id=eid, debug_port=port, cdp_url=f"http://127.0.0.1:{port}")


async def stop_profile(env_id: str | None = None) -> None:
    eid = env_id or ENV_ID
    if not eid:
        raise MoreLoginError("MORELOGIN_ENV_ID не задан")
    async with httpx.AsyncClient(base_url=API_URL, timeout=TIMEOUT) as c:
        _unwrap(await c.post("/api/env/close", json={"envId": eid}))
