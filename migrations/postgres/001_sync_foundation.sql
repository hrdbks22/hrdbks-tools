BEGIN;
CREATE TABLE IF NOT EXISTS sync_nodes (
 node_id UUID PRIMARY KEY, node_name TEXT NOT NULL,
 node_type TEXT NOT NULL CHECK (node_type IN ('lan','cloud')),
 last_seen_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sync_events (
 event_id UUID PRIMARY KEY, origin_node_id UUID NOT NULL REFERENCES sync_nodes(node_id),
 entity_type TEXT NOT NULL, entity_key TEXT NOT NULL,
 operation TEXT NOT NULL CHECK (operation IN ('insert','update','delete')),
 entity_version BIGINT NOT NULL CHECK (entity_version > 0),
 payload JSONB NOT NULL, occurred_at TIMESTAMPTZ NOT NULL,
 received_at TIMESTAMPTZ NOT NULL DEFAULT now(), applied_at TIMESTAMPTZ,
 status TEXT NOT NULL DEFAULT 'pending'
   CHECK (status IN ('pending','applied','conflict','rejected')),
 error_message TEXT,
 UNIQUE(origin_node_id, entity_type, entity_key, entity_version)
);
CREATE INDEX IF NOT EXISTS idx_sync_events_pending ON sync_events(status, received_at) WHERE status='pending';
CREATE INDEX IF NOT EXISTS idx_sync_events_entity ON sync_events(entity_type, entity_key, entity_version);
CREATE TABLE IF NOT EXISTS sync_conflicts (
 conflict_id UUID PRIMARY KEY, event_id UUID NOT NULL REFERENCES sync_events(event_id),
 entity_type TEXT NOT NULL, entity_key TEXT NOT NULL,
 local_version BIGINT NOT NULL, incoming_version BIGINT NOT NULL,
 local_payload JSONB NOT NULL, incoming_payload JSONB NOT NULL,
 status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','resolved','dismissed')),
 resolution TEXT, resolved_by TEXT, resolved_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sync_conflicts_open ON sync_conflicts(created_at) WHERE status='open';
CREATE TABLE IF NOT EXISTS audit_log (
 audit_id UUID PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL,
 entity_type TEXT NOT NULL, entity_key TEXT NOT NULL,
 before_data JSONB, after_data JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMIT;
