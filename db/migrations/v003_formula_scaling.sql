-- ============================================================
-- PYTHFINDER ACTION TRACKER
-- Migration v003 — Formula-Scaled Effects
-- ============================================================
-- Run after v002:
--   mysql -u root -p < db/migrations/v003_formula_scaling.sql
-- ============================================================

USE pythfinder_tracker;

ALTER TABLE effects
    ADD COLUMN base_value       INT           NULL        AFTER modifier,
    ADD COLUMN scaling_stat_id  INT           NULL        AFTER base_value,
    ADD COLUMN multiplier       DECIMAL(5,2)  NOT NULL DEFAULT 1.00 AFTER scaling_stat_id,
    ADD COLUMN divisor          INT           NOT NULL DEFAULT 1    AFTER multiplier,
    ADD CONSTRAINT fk_effect_scaling_stat
        FOREIGN KEY (scaling_stat_id) REFERENCES stats(id)
        ON DELETE SET NULL;

-- ============================================================
-- Effect type summary after this migration:
--
--   Fixed:             modifier IS NOT NULL, pool_allocation_id IS NULL, scaling_stat_id IS NULL
--   Investment-scaled: modifier IS NULL,     pool_allocation_id IS NOT NULL, scaling_stat_id IS NULL
--   Formula-scaled:    modifier IS NULL,     pool_allocation_id IS NULL, scaling_stat_id IS NOT NULL
--
-- Computed value for formula-scaled effects:
--   base_value + FLOOR((scaling_stat_value * multiplier) / divisor)
-- ============================================================
