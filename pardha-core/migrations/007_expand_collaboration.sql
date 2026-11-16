ALTER TABLE objectives ADD COLUMN IF NOT EXISTS business_name TEXT;
UPDATE objectives SET business_name = 'Pardha' WHERE business_name IS NULL;
ALTER TABLE objectives ALTER COLUMN business_name SET NOT NULL;

ALTER TABLE objectives DROP CONSTRAINT IF EXISTS ck_objective_status;
UPDATE objectives SET status = CASE
    WHEN lower(status) = 'completed' THEN 'COMPLETED'
    WHEN lower(status) IN ('cancelled', 'blocked') THEN 'BLOCKED'
    WHEN lower(status) IN ('active', 'in_progress') THEN 'IN_PROGRESS'
    ELSE 'NEW'
END;
ALTER TABLE objectives ALTER COLUMN status SET DEFAULT 'NEW';
ALTER TABLE objectives ADD CONSTRAINT ck_objective_status CHECK (
    status IN ('NEW', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED')
);

ALTER TABLE agent_collaborations ADD COLUMN IF NOT EXISTS event_type TEXT;
UPDATE agent_collaborations SET event_type = upper(action) WHERE event_type IS NULL;
ALTER TABLE agent_collaborations ALTER COLUMN event_type SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_objectives_business_name ON objectives (business_name);
CREATE INDEX IF NOT EXISTS ix_agent_collaborations_event_type ON agent_collaborations (event_type);
