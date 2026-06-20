-- v007_fix_skill_duplicates.sql
-- Removes duplicate skill rows introduced by running v006 multiple times
-- and clears the abbreviation column which incorrectly stored the skill name.
--
-- Strategy: for each skill name, keep the lowest id and delete the rest.
-- Then clear abbreviations on all skill rows.

-- Step 1: delete duplicate skill rows, keeping the lowest id per name
DELETE FROM stats
WHERE category = 'skill'
  AND id NOT IN (
      SELECT min_id FROM (
          SELECT MIN(id) AS min_id
          FROM stats
          WHERE category = 'skill'
          GROUP BY name
      ) AS keepers
  );

-- Step 2: clear the abbreviation column for all skill rows
UPDATE stats
SET abbreviation = ''
WHERE category = 'skill';
