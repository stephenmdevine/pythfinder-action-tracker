-- ============================================================
-- Migration v005: Add Racial bonus type
-- Safe to run on existing databases — INSERT IGNORE skips if
-- a row with the same name already exists (requires UNIQUE on name).
-- ============================================================

USE pythfinder_tracker;

INSERT IGNORE INTO bonus_types (name, always_stacks)
VALUES ('Racial', FALSE);
