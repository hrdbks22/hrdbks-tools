"""Small authenticated sync API. Run behind HTTPS reverse proxy only."""
from __future__ import annotations

import hmac
import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from sync.engine import connect, receive_event, pending_events, acknowledge_events

app = FastAPI(title="HRD Tools Sync Service", version="1.0.0")
DSN = os.environ.get("DATABASE_URL", "")
SYNC_TOKEN = os.environ.get("SYNC_TOKEN", "")
NODE_ID = os.environ.get("SYNC_NODE_ID", "")


class ExchangeRequest(BaseModel):
    node_id: str = Field(min_length=1, max_length=100)
    events: list[dict] = Field(default_factory=list, max_length=500)


@app.get("/health")
def health():
    return {"service": "hrd-sync", "configured": bool(DSN and SYNC_TOKEN and NODE_ID)}


@app.post("/v1/sync/exchange")
def exchange(body: ExchangeRequest, authorization: str | None = Header(default=None)):
    expected = f"Bearer {SYNC_TOKEN}"
    if not SYNC_TOKEN or not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not DSN or not NODE_ID:
        raise HTTPException(status_code=503, detail="Sync service is not configured")
    if body.node_id == NODE_ID:
        raise HTTPException(status_code=400, detail="Source and destination nodes must differ")
    if len(body.events) > 500:
        raise HTTPException(status_code=413, detail="Too many events")
    accepted, conflicts, duplicates = [], [], []
    with connect(DSN) as conn:
        for event in body.events:
            try:
                result = receive_event(conn, event, receiver_node_id=NODE_ID)
            except (KeyError, ValueError, TypeError) as exc:
                raise HTTPException(status_code=422, detail=f"Invalid event: {exc}") from exc
            if result == "applied": accepted.append(event["event_id"])
            elif result == "conflict": conflicts.append(event["event_id"])
            else: duplicates.append(event["event_id"])
        outgoing = pending_events(conn)
        acknowledge_events(conn, accepted + duplicates)
    return {"accepted": accepted, "conflicts": conflicts,
            "duplicates": duplicates, "events": outgoing}
