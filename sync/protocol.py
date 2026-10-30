"""Authenticated HTTPS client for node-to-node event exchange."""
from __future__ import annotations

import os
import requests


class SyncProtocolError(RuntimeError):
    pass


def exchange(*, endpoint: str, token: str, node_id: str,
             events: list[dict], timeout: int = 20) -> dict:
    if not endpoint.startswith("https://"):
        raise SyncProtocolError("Sync endpoint must use HTTPS")
    if not token or not node_id:
        raise SyncProtocolError("SYNC_TOKEN and SYNC_NODE_ID are required")
    response = requests.post(
        endpoint.rstrip("/") + "/v1/sync/exchange",
        json={"node_id": node_id, "events": events},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=timeout,
    )
    if response.status_code != 200:
        raise SyncProtocolError(f"Sync server returned HTTP {response.status_code}")
    try:
        result = response.json()
    except ValueError as exc:
        raise SyncProtocolError("Sync server returned invalid JSON") from exc
    if not isinstance(result, dict) or "accepted" not in result:
        raise SyncProtocolError("Sync server response schema is invalid")
    return result
