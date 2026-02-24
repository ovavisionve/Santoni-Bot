-- Migration: Add confidence_score column to messages table
-- Date: 2026-02-24
-- Description: Adds confidence_score (float) for tracking routing and data confidence per interaction
--
-- Run: docker compose exec backend python -c "
-- from app.database import SessionLocal; from sqlalchemy import text
-- db = SessionLocal()
-- db.execute(text(open('migrations/add_confidence_score.sql').read()))
-- db.commit()
-- db.close()
-- print('Migration applied successfully')
-- "

-- Add confidence_score column (nullable float, 0.0 to 1.0)
ALTER TABLE messages ADD COLUMN IF NOT EXISTS confidence_score FLOAT;

-- Index for efficient filtering in confidence reports
CREATE INDEX IF NOT EXISTS ix_messages_confidence_score ON messages (confidence_score)
WHERE confidence_score IS NOT NULL;
