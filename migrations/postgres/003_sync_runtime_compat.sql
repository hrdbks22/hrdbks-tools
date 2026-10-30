-- Extend the original foundation schema without discarding its audit history.
ALTER TABLE sync_events ADD COLUMN IF NOT EXISTS base_version BIGINT NOT NULL DEFAULT 0;
ALTER TABLE sync_events ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE sync_events ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE sync_events ADD COLUMN IF NOT EXISTS last_error TEXT;
ALTER TABLE sync_events ADD COLUMN IF NOT EXISTS synced_at TIMESTAMPTZ;

ALTER TABLE sync_events DROP CONSTRAINT IF EXISTS sync_events_status_check;
ALTER TABLE sync_events ADD CONSTRAINT sync_events_status_check
    CHECK (status IN ('pending','applied','conflict','rejected','retry','synced'));

ALTER TABLE sync_conflicts ADD COLUMN IF NOT EXISTS remote_base_version BIGINT NOT NULL DEFAULT 0;
ALTER TABLE sync_conflicts ADD COLUMN IF NOT EXISTS remote_payload JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE sync_conflicts ADD COLUMN IF NOT EXISTS resolution_note TEXT;

CREATE TABLE IF NOT EXISTS sync_entity_state (
    entity_type TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (entity_type, entity_key)
);
CREATE TABLE IF NOT EXISTS sync_inbox (
    event_id UUID PRIMARY KEY,
    source_node_id UUID NOT NULL REFERENCES sync_nodes(node_id),
    status TEXT NOT NULL DEFAULT 'received'
        CHECK (status IN ('received','applied','conflict','rejected')),
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sync_checkpoints (
    peer_node_id UUID PRIMARY KEY REFERENCES sync_nodes(node_id),
    last_success_at TIMESTAMPTZ,
    last_event_id UUID,
    last_error TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sync_events_retry
    ON sync_events(status, next_attempt_at, received_at);
