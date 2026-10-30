-- Runtime extensions compatible with the canonical entity_key/UUID schema.
-- Keep this migration idempotent; 003 adds compatibility columns and checkpoints.
ALTER TABLE sync_events
    ADD COLUMN IF NOT EXISTS base_version BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS last_error TEXT,
    ADD COLUMN IF NOT EXISTS synced_at TIMESTAMPTZ;

ALTER TABLE sync_events DROP CONSTRAINT IF EXISTS sync_events_status_check;
ALTER TABLE sync_events ADD CONSTRAINT sync_events_status_check
    CHECK (status IN ('pending','applied','conflict','rejected','retry','synced'));

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

CREATE INDEX IF NOT EXISTS idx_sync_events_retry
    ON sync_events(status, next_attempt_at, occurred_at);
