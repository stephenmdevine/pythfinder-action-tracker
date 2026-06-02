-- ============================================================
-- PYTHFINDER ACTION TRACKER
-- Migration v004 — Campaign-scoped Sources
-- ============================================================
-- Run after v003:
--   mysql -u root -p < db/migrations/v004_campaign_sources.sql
-- ============================================================

USE pythfinder_tracker;

ALTER TABLE sources
    ADD COLUMN campaign_id INT NULL AFTER id,
    ADD CONSTRAINT fk_source_campaign
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        ON DELETE CASCADE;

-- NULL campaign_id = global source (visible in all campaigns)
-- Set campaign_id  = campaign-specific source

-- Index for fast filtering
CREATE INDEX idx_sources_campaign ON sources(campaign_id);
