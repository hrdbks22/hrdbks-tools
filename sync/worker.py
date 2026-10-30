"""One-shot bidirectional sync worker; schedule every minute with systemd/cron."""
from __future__ import annotations

import os
import sys

from sync.engine import connect, pending_events, acknowledge_events, record_sync_error, receive_event
from sync.protocol import exchange, SyncProtocolError


def run_once() -> dict:
    dsn = os.environ.get("DATABASE_URL", "")
    endpoint = os.environ.get("SYNC_ENDPOINT", "")
    token = os.environ.get("SYNC_TOKEN", "")
    node_id = os.environ.get("SYNC_NODE_ID", "")
    if not all((dsn, endpoint, token, node_id)):
        raise RuntimeError("DATABASE_URL, SYNC_ENDPOINT, SYNC_TOKEN, and SYNC_NODE_ID are required")

    with connect(dsn) as conn:
        outgoing = pending_events(conn)
        serializable = []
        for event in outgoing:
            item = dict(event)
            for key, value in list(item.items()):
                if hasattr(value, "isoformat"):
                    item[key] = value.isoformat()
                elif key == "event_id" and value is not None:
                    item[key] = str(value)
                elif key == "node_id" and value is not None:
                    item[key] = str(value)
            serializable.append(item)

        try:
            response = exchange(endpoint=endpoint, token=token, node_id=node_id,
                                events=serializable)
        except Exception as exc:
            record_sync_error(conn, [str(x["event_id"]) for x in outgoing], str(exc))
            raise

        acknowledge_events(conn, response.get("accepted", []) + response.get("duplicates", []))
        conflicted = response.get("conflicts", [])
        if conflicted:
            conn.execute(
                "UPDATE sync_events SET status='conflict',last_error='Remote node reported a version conflict' WHERE event_id=ANY(%s)",
                (conflicted,),
            )
        for event in response.get("events", []):
            receive_event(conn, event, receiver_node_id=node_id)

        return {
            "sent": len(serializable),
            "accepted": len(response.get("accepted", [])),
            "received": len(response.get("events", [])),
            "conflicts": len(response.get("conflicts", [])),
        }


if __name__ == "__main__":
    try:
        print(run_once())
    except (RuntimeError, SyncProtocolError, OSError) as exc:
        print(f"Sync gagal: {exc}", file=sys.stderr)
        sys.exit(1)
