-- v006_seed_skills.sql
-- Seeds all Pathfinder 1e core skills into the stats table.
-- Uses INSERT IGNORE so re-running is safe on existing installs.
-- Each skill row: category = 'skill', abbreviation left blank
-- (skills are identified by name, not abbreviation).

INSERT IGNORE INTO stats (name, abbreviation, category) VALUES
    ('Acrobatics',                  '', 'skill'),
    ('Appraise',                    '', 'skill'),
    ('Bluff',                       '', 'skill'),
    ('Climb',                       '', 'skill'),
    ('Craft',                       '', 'skill'),
    ('Diplomacy',                   '', 'skill'),
    ('Disable Device',              '', 'skill'),
    ('Disguise',                    '', 'skill'),
    ('Escape Artist',               '', 'skill'),
    ('Fly',                         '', 'skill'),
    ('Handle Animal',               '', 'skill'),
    ('Heal',                        '', 'skill'),
    ('Intimidate',                  '', 'skill'),
    ('Knowledge (Arcana)',          '', 'skill'),
    ('Knowledge (Dungeoneering)',   '', 'skill'),
    ('Knowledge (Engineering)',     '', 'skill'),
    ('Knowledge (Geography)',       '', 'skill'),
    ('Knowledge (History)',         '', 'skill'),
    ('Knowledge (Local)',           '', 'skill'),
    ('Knowledge (Nature)',          '', 'skill'),
    ('Knowledge (Nobility)',        '', 'skill'),
    ('Knowledge (Planes)',          '', 'skill'),
    ('Knowledge (Religion)',        '', 'skill'),
    ('Linguistics',                 '', 'skill'),
    ('Perception',                  '', 'skill'),
    ('Perform',                     '', 'skill'),
    ('Profession',                  '', 'skill'),
    ('Ride',                        '', 'skill'),
    ('Sense Motive',                '', 'skill'),
    ('Sleight of Hand',             '', 'skill'),
    ('Spellcraft',                  '', 'skill'),
    ('Stealth',                     '', 'skill'),
    ('Survival',                    '', 'skill'),
    ('Swim',                        '', 'skill'),
    ('Use Magic Device',            '', 'skill');
