-- v008_add_speed_stat.sql
-- Adds Speed as a stat in the 'other' category so CharacterInitDialog
-- can save it alongside ability scores during character creation.
-- INSERT IGNORE is safe to re-run.

INSERT IGNORE INTO stats (name, abbreviation, category)
VALUES ('Speed', 'SPD', 'other');
