-- Spec 013 — Goal Pursuit: extend subagents table for DAG-based goal execution.
-- Idempotente vía ADD COLUMN IF NOT EXISTS.

ALTER TABLE subagents ADD COLUMN IF NOT EXISTS parent_goal_id UUID REFERENCES subagents(id);
ALTER TABLE subagents ADD COLUMN IF NOT EXISTS capability_token JSONB;
ALTER TABLE subagents ADD COLUMN IF NOT EXISTS goal_dag JSONB;

CREATE INDEX IF NOT EXISTS subagents_parent_goal_id_idx ON subagents (parent_goal_id);
