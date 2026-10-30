-- Runtime tables for transactional outbox/inbox and conflict-safe entity replication.
CREATE TABLE IF NOT EXISTS sync_entity_state (
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (entity_type, entity_id)
);

ALTER TABLE sync_events
    ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS last_error TEXT,
    ADD COLUMN IF NOT EXISTS synced_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_sync_events_pending
    ON sync_events(status, next_attempt_at, created_at);

CREATE TABLE IF NOT EXISTS sync_inbox (
    event_id UUID PRIMARY KEY,
    source_node_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'received'
        CHECK (status IN ('received','applied','conflict','rejected')),
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE sync_conflicts
    ADD COLUMN IF NOT EXISTS event_id UUID,
    ADD COLUMN IF NOT EXISTS local_version BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS remote_base_version BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS local_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS remote_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS resolution_note TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_sync_conflicts_event
    ON sync_conflicts(event_id) WHERE event_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS sync_checkpoints (
    peer_node_id TEXT PRIMARY KEY,
    last_success_at TIMESTAMPTZ,
    last_event_id UUID,
    last_error TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
