"""PostgreSQL integration tests for the sync engine.

Run with TEST_DATABASE_URL pointing at a disposable PostgreSQL database.
"""
import os
import unittest
import uuid

from sync.engine import connect, enqueue_change, pending_events, receive_event


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "TEST_DATABASE_URL not configured")
class SyncPostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn = os.environ["TEST_DATABASE_URL"]
        cls.node_a = str(uuid.uuid4())
        cls.node_b = str(uuid.uuid4())
        with connect(cls.dsn) as conn:
            conn.execute(
                "INSERT INTO sync_nodes(node_id,node_name,node_type) VALUES (%s,%s,'lan'),(%s,%s,'cloud')",
                (cls.node_a, "test-lan", cls.node_b, "test-cloud"),
            )

    @classmethod
    def tearDownClass(cls):
        with connect(cls.dsn) as conn:
            conn.execute("DELETE FROM sync_events WHERE origin_node_id = ANY(%s)", ([cls.node_a, cls.node_b],))
            conn.execute("DELETE FROM sync_inbox WHERE source_node_id = ANY(%s)", ([cls.node_a, cls.node_b],))
            conn.execute("DELETE FROM sync_entity_state WHERE entity_key LIKE 'test:%'")
            conn.execute("DELETE FROM sync_conflicts WHERE entity_key LIKE 'test:%'")
            conn.execute("DELETE FROM sync_nodes WHERE node_id = ANY(%s)", ([cls.node_a, cls.node_b],))

    def test_outbox_delivery_is_idempotent(self):
        entity_id = "test:" + str(uuid.uuid4())
        with connect(self.dsn) as conn:
            event_id = enqueue_change(
                conn, node_id=self.node_a, entity_type="test_entity",
                entity_id=entity_id, operation="insert",
                payload={"value": "first"}, base_version=0,
            )
            outgoing = [e for e in pending_events(conn) if str(e["event_id"]) == event_id]
            self.assertEqual(len(outgoing), 1)
            event = outgoing[0]
            event["event_id"] = str(event["event_id"])
            event["node_id"] = str(event["node_id"])
            event["created_at"] = event["created_at"].isoformat()
        with connect(self.dsn) as conn:
            self.assertEqual(receive_event(conn, event, receiver_node_id=self.node_b), "applied")
        with connect(self.dsn) as conn:
            self.assertEqual(receive_event(conn, event, receiver_node_id=self.node_b), "duplicate")
            state = conn.execute(
                "SELECT version,payload FROM sync_entity_state WHERE entity_type=%s AND entity_key=%s",
                ("test_entity", entity_id),
            ).fetchone()
            self.assertEqual(state["version"], 1)
            self.assertEqual(state["payload"]["value"], "first")

    def test_stale_base_version_creates_conflict(self):
        entity_id = "test:" + str(uuid.uuid4())
        event = {
            "event_id": str(uuid.uuid4()), "node_id": self.node_a,
            "entity_type": "test_entity", "entity_id": entity_id,
            "operation": "update", "payload": {"value": "remote"},
            "base_version": 2, "entity_version": 3,
        }
        with connect(self.dsn) as conn:
            conn.execute(
                "INSERT INTO sync_entity_state(entity_type,entity_key,version,payload) VALUES (%s,%s,1,%s::jsonb)",
                ("test_entity", entity_id, '{"value":"local"}'),
            )
            self.assertEqual(receive_event(conn, event, receiver_node_id=self.node_b), "conflict")
            row = conn.execute(
                "SELECT status FROM sync_conflicts WHERE event_id=%s", (event["event_id"],)
            ).fetchone()
            self.assertEqual(row["status"], "open")


if __name__ == "__main__":
    unittest.main()
