"""PostgreSQL transactional outbox/inbox primitives for HRD Tools.

Business writes and enqueue_change must share one transaction. Event UUIDs make
delivery idempotent; entity versions prevent silent last-write-wins conflicts.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

import psycopg
from psycopg.rows import dict_row


def connect(dsn: str):
    return psycopg.connect(dsn, row_factory=dict_row)


def enqueue_change(conn, *, node_id: str, entity_type: str, entity_id: str,
                   operation: str, payload: dict[str, Any], base_version: int = 0) -> str:
    if operation not in {"insert", "update", "delete"}:
        raise ValueError("operation must be insert, update, or delete")
    event_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO sync_events
           (event_id,origin_node_id,entity_type,entity_key,operation,payload,
            base_version,entity_version,occurred_at,status)
           VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,now(),'pending')""",
        (event_id, str(uuid.UUID(node_id)), entity_type, entity_id, operation,
         json.dumps(payload, ensure_ascii=False), base_version, base_version + 1),
    )
    return event_id


def pending_events(conn, limit: int = 200) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT event_id,origin_node_id AS node_id,entity_type,entity_key AS entity_id,
                  operation,payload,base_version,entity_version,occurred_at AS created_at
           FROM sync_events WHERE status IN ('pending','retry')
             AND next_attempt_at <= now()
           ORDER BY occurred_at,event_id LIMIT %s""",
        (max(1, min(limit, 500)),)
    ).fetchall()
    return [dict(row) for row in rows]


def acknowledge_events(conn, event_ids: list[str]) -> None:
    if event_ids:
        conn.execute(
            """UPDATE sync_events SET status='synced',synced_at=now(),applied_at=now(),
               last_error=NULL WHERE event_id=ANY(%s)""", (event_ids,)
        )


def record_sync_error(conn, event_ids: list[str], error: str) -> None:
    if event_ids:
        conn.execute(
            """UPDATE sync_events SET status='retry',attempts=attempts+1,error_message=%s,
               last_error=%s,next_attempt_at=now() + LEAST(interval '1 hour',
               interval '5 seconds' * power(2,LEAST(attempts,10)))
               WHERE event_id=ANY(%s)""", (error[:2000], error[:2000], event_ids)
        )


def receive_event(conn, event: dict[str, Any], *, receiver_node_id: str) -> str:
    event_id = str(uuid.UUID(str(event["event_id"])))
    source_node = str(uuid.UUID(str(event["node_id"])))
    # Verify that the event origin is a registered node before accepting it.
    registered = conn.execute(
        "SELECT node_id FROM sync_nodes WHERE node_id=%s", (source_node,)
    ).fetchone()
    if not registered:
        raise ValueError("Unregistered event origin node")
    inserted = conn.execute(
        """INSERT INTO sync_inbox(event_id,source_node_id,received_at)
           VALUES (%s,%s,now()) ON CONFLICT(event_id) DO NOTHING RETURNING event_id""",
        (event_id, source_node),
    ).fetchone()
    if not inserted:
        return "duplicate"

    # Persist the original immutable event in this node's outbox so it can be
    # relayed onward to other peers after local application.
    conn.execute(
        """INSERT INTO sync_events
           (event_id,origin_node_id,entity_type,entity_key,operation,payload,
            base_version,entity_version,occurred_at,status)
           VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,'applied')
           ON CONFLICT(event_id) DO NOTHING""",
        (event_id, source_node, event["entity_type"], event["entity_id"],
         event["operation"], json.dumps(event.get("payload") or {}, ensure_ascii=False),
         int(event["base_version"]), int(event["entity_version"]),
         event.get("created_at") or event.get("occurred_at")),
    )

    current = conn.execute(
        """SELECT version,payload FROM sync_entity_state
           WHERE entity_type=%s AND entity_key=%s FOR UPDATE""",
        (event["entity_type"], event["entity_id"]),
    ).fetchone()
    current_version = int(current["version"]) if current else 0
    base_version = int(event["base_version"])
    if current_version != base_version:
        conn.execute(
            """INSERT INTO sync_conflicts
               (conflict_id,event_id,entity_type,entity_key,local_version,incoming_version,
                remote_base_version,local_payload,incoming_payload,remote_payload,status,created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,'open',now())""",
            (str(uuid.uuid4()), event_id, event["entity_type"], event["entity_id"],
             current_version, int(event["entity_version"]), base_version,
             json.dumps(current["payload"] if current else {}),
             json.dumps(event.get("payload") or {}),
             json.dumps(event.get("payload") or {})),
        )
        conn.execute("UPDATE sync_inbox SET status='conflict' WHERE event_id=%s", (event_id,))
        conn.execute("UPDATE sync_events SET status='conflict' WHERE event_id=%s", (event_id,))
        return "conflict"

    payload = event.get("payload") or {}
    if event["operation"] == "delete":
        payload = {"_deleted": True}
    conn.execute(
        """INSERT INTO sync_entity_state(entity_type,entity_key,version,payload,updated_at)
           VALUES (%s,%s,%s,%s::jsonb,now())
           ON CONFLICT(entity_type,entity_key) DO UPDATE
           SET version=EXCLUDED.version,payload=EXCLUDED.payload,updated_at=now()""",
        (event["entity_type"], event["entity_id"], int(event["entity_version"]),
         json.dumps(payload, ensure_ascii=False)),
    )
    conn.execute("UPDATE sync_inbox SET status='applied' WHERE event_id=%s", (event_id,))
    return "applied"


def sync_status(conn) -> dict[str, int]:
    row = conn.execute(
        """SELECT count(*) FILTER (WHERE status IN ('pending','retry')) AS pending,
           count(*) FILTER (WHERE status IN ('synced','applied')) AS synced,
           count(*) FILTER (WHERE status='retry') AS retry FROM sync_events"""
    ).fetchone()
    conflicts = conn.execute("SELECT count(*) AS n FROM sync_conflicts WHERE status='open'").fetchone()
    return {"pending": row["pending"], "synced": row["synced"],
            "retry": row["retry"], "open_conflicts": conflicts["n"]}
