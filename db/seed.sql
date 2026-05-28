-- ============================================================
-- PATHFINDER 1E ACTION & CAMPAIGN TRACKER
-- Seed Data v1.0
-- Run this after schema.sql
-- ============================================================

USE pythfinder_tracker;

-- ============================================================
-- STATS
-- ============================================================

INSERT INTO stats (name, abbreviation, category) VALUES
-- Ability Scores
('Strength',        'STR',  'ability'),
('Dexterity',       'DEX',  'ability'),
('Constitution',    'CON',  'ability'),
('Intelligence',    'INT',  'ability'),
('Wisdom',          'WIS',  'ability'),
('Charisma',        'CHA',  'ability'),

-- Ability Modifiers (derived, but useful to track separately for effects)
('Strength Modifier',       'STR Mod', 'ability'),
('Dexterity Modifier',      'DEX Mod', 'ability'),
('Constitution Modifier',   'CON Mod', 'ability'),
('Intelligence Modifier',   'INT Mod', 'ability'),
('Wisdom Modifier',         'WIS Mod', 'ability'),
('Charisma Modifier',       'CHA Mod', 'ability'),

-- Combat Stats
('Armor Class',             'AC',       'combat'),
('Touch AC',                'Touch AC', 'combat'),
('Flat-Footed AC',          'FF AC',    'combat'),
('Hit Points',              'HP',       'combat'),
('Base Attack Bonus',       'BAB',      'combat'),
('Combat Maneuver Bonus',   'CMB',      'combat'),
('Combat Maneuver Defense', 'CMD',      'combat'),
('Initiative',              'INIT',     'combat'),
('Attack Roll',             'ATK',      'combat'),
('Damage Roll',             'DMG',      'combat'),
('Speed',                   'SPD',      'combat'),

-- Saving Throws
('Fortitude Save', 'FORT', 'save'),
('Reflex Save',    'REF',  'save'),
('Will Save',      'WILL', 'save'),

-- Skills
('Acrobatics',        'Acrobatics',     'skill'),
('Appraise',          'Appraise',       'skill'),
('Bluff',             'Bluff',          'skill'),
('Climb',             'Climb',          'skill'),
('Craft',             'Craft',          'skill'),
('Diplomacy',         'Diplomacy',      'skill'),
('Disable Device',    'Disable Device', 'skill'),
('Disguise',          'Disguise',       'skill'),
('Escape Artist',     'Escape Artist',  'skill'),
('Fly',               'Fly',            'skill'),
('Handle Animal',     'Handle Animal',  'skill'),
('Heal',              'Heal',           'skill'),
('Intimidate',        'Intimidate',     'skill'),
('Knowledge Arcana',  'Know Arcana',    'skill'),
('Knowledge Dungeoneering', 'Know Dungeon', 'skill'),
('Knowledge Engineering',   'Know Eng',    'skill'),
('Knowledge Geography',     'Know Geo',    'skill'),
('Knowledge History',       'Know Hist',   'skill'),
('Knowledge Local',         'Know Local',  'skill'),
('Knowledge Nature',        'Know Nature', 'skill'),
('Knowledge Nobility',      'Know Nob',    'skill'),
('Knowledge Planes',        'Know Planes', 'skill'),
('Knowledge Religion',      'Know Relig',  'skill'),
('Linguistics',       'Linguistics',    'skill'),
('Perception',        'Perception',     'skill'),
('Perform',           'Perform',        'skill'),
('Profession',        'Profession',     'skill'),
('Ride',              'Ride',           'skill'),
('Sense Motive',      'Sense Motive',   'skill'),
('Sleight of Hand',   'Sleight of Hand','skill'),
('Spellcraft',        'Spellcraft',     'skill'),
('Stealth',           'Stealth',        'skill'),
('Survival',          'Survival',       'skill'),
('Swim',              'Swim',           'skill'),
('Use Magic Device',  'UMD',            'skill'),

-- Other
('Caster Level',      'CL',    'other'),
('Concentration',     'Conc',  'other'),
('Spell Resistance',  'SR',    'other'),
('Damage Reduction',  'DR',    'other'),
('Energy Resistance', 'ER',    'other'),
('Encumbrance',       'ENC',   'other');

-- ============================================================
-- BONUS TYPES
-- ============================================================

INSERT INTO bonus_types (name, always_stacks) VALUES
-- Typed bonuses (only highest applies per source)
('Alchemical',    FALSE),
('Armor',         FALSE),
('Circumstance',  FALSE),
('Competence',    FALSE),
('Deflection',    FALSE),
('Enhancement',   FALSE),
('Insight',       FALSE),
('Luck',          FALSE),
('Morale',        FALSE),
('Natural Armor', FALSE),
('Profane',       FALSE),
('Resistance',    FALSE),
('Sacred',        FALSE),
('Shield',        FALSE),
('Size',          FALSE),
('Trait',         FALSE),

-- Always-stacking types
('Dodge',         TRUE),   -- dodge bonuses always stack
('Untyped',       TRUE),   -- untyped bonuses always stack
('Penalty',       TRUE);   -- penalties always stack

-- ============================================================
-- ACTION TYPES
-- ============================================================

INSERT INTO action_types (name, description, max_per_round) VALUES
('Standard',    'A standard action allows you to do something, most commonly make an attack or cast a spell.', 1),
('Move',        'A move action allows you to move up to your speed or perform an action that takes a similar amount of time.', 1),
('Full-Round',  'A full-round action consumes all your effort during a round. You can only take a 5-foot step as movement.', 1),
('Swift',       'A swift action consumes a very small amount of time, but represents a larger expenditure of effort. You can only take one swift action per turn.', 1),
('Immediate',   'An immediate action is very similar to a swift action, but can be performed at any time — even if it is not your turn.', 1),
('Free',        'Free actions consume a negligible amount of time and effort. You may perform one or more free actions while taking another action normally.', 99),
('5-Foot Step', 'You can move 5 feet in any round when you do not perform any other kind of movement.', 1),
('Reaction',    'Some abilities trigger as a reaction to another event, outside of the normal action economy.', 99);

-- ============================================================
-- SOURCE CATEGORIES
-- ============================================================

INSERT INTO source_categories (name) VALUES
('Feat'),
('Spell'),
('Condition'),
('Class Feature'),
('Trait'),
('Magic Item'),
('Consumable'),
('Racial Ability'),
('Ability Score'),
('Equipment'),
('Other');

-- ============================================================
-- ITEM CATEGORIES
-- ============================================================

INSERT INTO item_categories (name) VALUES
('Weapon'),
('Armor'),
('Shield'),
('Potion'),
('Scroll'),
('Wand'),
('Rod'),
('Staff'),
('Ring'),
('Wondrous Item'),
('Consumable'),
('Adventuring Gear'),
('Trade Good'),
('Mount & Animal'),
('Vehicle'),
('Other');
