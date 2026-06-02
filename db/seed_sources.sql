-- ============================================================
-- PYTHFINDER ACTION TRACKER
-- Seed: Baseline Sources (Conditions & Combat Modifiers)
-- ============================================================
-- Run after seed.sql:
--   mysql -u root -p < db/seed_sources.sql
--
-- All sources here are global (campaign_id = NULL) and use
-- the 'Condition' and 'Other' source categories seeded earlier.
-- Effects reference stat IDs and bonus type IDs from seed.sql.
--
-- STAT IDs (from seed.sql insertion order — verify with:
--   SELECT id, name FROM stats ORDER BY id;)
-- We use subqueries by name to avoid hardcoded IDs that may
-- differ between installs.
-- ============================================================

USE pythfinder_tracker;

-- ============================================================
-- HELPER: ensure we have a 'Penalty' bonus type for negative
-- effects (seeded in seed.sql, but referenced heavily here)
-- ============================================================

-- ============================================================
-- CONDITIONS
-- ============================================================

-- BLINDED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Blinded',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'toggle',
    'The character cannot see. Takes a 50% miss chance, loses Dex bonus to AC, -2 penalty to AC, moves at half speed.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Armor Class'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Blinded: loses Dex bonus and takes -2 to AC'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Perception'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -4, 'Blinded: -4 to Perception checks');

-- CONFUSED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Confused',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'rounds',
    'Acts randomly each round. Roll d100 to determine action each turn.'
);

-- DAZZLED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Dazzled',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'toggle',
    'Impaired by light. Takes -1 penalty on attack rolls and sight-based Perception checks.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Attack Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -1, 'Dazzled: -1 on attack rolls'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Perception'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -1, 'Dazzled: -1 on sight-based Perception checks');

-- DEAFENED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Deafened',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'toggle',
    'Cannot hear. -4 penalty on Perception checks, 20% spell failure for spells with verbal components.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Perception'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -4, 'Deafened: -4 on Perception checks');

-- ENTANGLED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Entangled',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'toggle',
    'Ensnared. -2 attack rolls, -4 Dex. Cannot move unless strong enough to break or slip free.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Attack Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Entangled: -2 on attack rolls'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Dexterity'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -4, 'Entangled: -4 Dexterity');

-- EXHAUSTED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Exhausted',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'toggle',
    'Severely fatigued. -6 Str and Dex. Moves at half speed. Becomes fatigued after 1 hour of complete rest.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Strength'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -6, 'Exhausted: -6 Strength'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Dexterity'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -6, 'Exhausted: -6 Dexterity');

-- FATIGUED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Fatigued',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'toggle',
    'Cannot run or charge. -2 penalty to Strength and Dexterity.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Strength'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Fatigued: -2 Strength'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Dexterity'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Fatigued: -2 Dexterity');

-- FRIGHTENED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Frightened',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'rounds',
    'Flees from source of fear if possible. -2 on attack rolls, saving throws, skill checks, ability checks.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Attack Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Frightened: -2 on attack rolls'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Fortitude Save'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Frightened: -2 on saving throws'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Reflex Save'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Frightened: -2 on saving throws'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Will Save'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Frightened: -2 on saving throws');

-- GRAPPLED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Grappled',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'toggle',
    'Restrained by a creature. -2 attack rolls, -2 CMB, -4 Dex. Cannot move. Concentration DC +10 to cast spells.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Attack Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Grappled: -2 on attack rolls'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Combat Maneuver Bonus'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Grappled: -2 CMB (except to grapple)'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Dexterity'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -4, 'Grappled: -4 Dexterity');

-- NAUSEATED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Nauseated',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'rounds',
    'Experiencing stomach distress. Can only take a single move action per turn. Cannot attack, cast spells, concentrate on spells, or do anything requiring attention.'
);

-- PANICKED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Panicked',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'rounds',
    'Drops held items and flees. -2 on saving throws, skill checks, ability checks. Cannot cast spells or use special abilities requiring concentration.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Fortitude Save'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Panicked: -2 on saving throws'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Reflex Save'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Panicked: -2 on saving throws'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Will Save'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Panicked: -2 on saving throws');

-- PARALYZED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Paralyzed',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'rounds',
    'Frozen in place. Str and Dex effectively 0. Fliers fall. Swimmers may drown. Attackers get +4 to hit and can coup de grace.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Armor Class'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -4, 'Paralyzed: attackers get +4; treat as flat-footed'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Dexterity'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -6, 'Paralyzed: Dex effectively 0 (using -6 as approximation; set base Dex to 0 for full effect)');

-- PRONE
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Prone',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'toggle',
    'Lying on the ground. -4 penalty on melee attack rolls. +4 bonus to AC against ranged attacks, -4 AC penalty against melee attacks.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Attack Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -4, 'Prone: -4 on melee attack rolls'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Armor Class'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -4, 'Prone: -4 AC against melee attacks');

-- SHAKEN
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Shaken',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'rounds',
    'Rattled. -2 penalty on attack rolls, saving throws, skill checks, and ability checks.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Attack Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Shaken: -2 on attack rolls'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Fortitude Save'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Shaken: -2 on saving throws'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Reflex Save'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Shaken: -2 on saving throws'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Will Save'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Shaken: -2 on saving throws');

-- SICKENED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Sickened',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'toggle',
    '-2 on attack rolls, weapon damage rolls, saving throws, skill checks, ability checks.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Attack Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Sickened: -2 on attack rolls'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Damage Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Sickened: -2 on weapon damage rolls'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Fortitude Save'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Sickened: -2 on saving throws'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Reflex Save'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Sickened: -2 on saving throws'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Will Save'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Sickened: -2 on saving throws');

-- STAGGERED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Staggered',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'toggle',
    'Reduced to a single move or standard action each round. Cannot take full-round actions.'
);

-- STUNNED
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Stunned',
    (SELECT id FROM source_categories WHERE name = 'Condition'),
    'rounds',
    'Drops everything held, cannot take actions, -2 AC penalty, loses Dex bonus to AC.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Armor Class'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Stunned: -2 AC, loses Dex bonus');

-- ============================================================
-- COMBAT MODIFIERS
-- ============================================================

-- CHARGING
INSERT INTO sources (campaign_id, name, source_category_id, duration_type,
    action_type_id, description)
VALUES (NULL,
    'Charging',
    (SELECT id FROM source_categories WHERE name = 'Other'),
    'until_next_turn',
    (SELECT id FROM action_types WHERE name = 'Full-Round'),
    'Moving and attacking in one action. +2 bonus on melee attack rolls, -2 AC until next turn.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Attack Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Untyped'),
        2, 'Charging: +2 on melee attack rolls'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Armor Class'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -2, 'Charging: -2 AC until next turn');

-- FLANKING
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Flanking',
    (SELECT id FROM source_categories WHERE name = 'Other'),
    'toggle',
    'You and an ally threaten the same enemy from opposite sides. +2 flanking bonus on melee attack rolls against that enemy.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Attack Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Untyped'),
        2, 'Flanking: +2 on melee attack rolls against flanked enemy');

-- FIGHTING DEFENSIVELY
INSERT INTO sources (campaign_id, name, source_category_id, duration_type,
    action_type_id, description)
VALUES (NULL,
    'Fighting Defensively',
    (SELECT id FROM source_categories WHERE name = 'Other'),
    'until_next_turn',
    (SELECT id FROM action_types WHERE name = 'Standard'),
    'Choosing to fight cautiously. -4 on all attacks for the round, +2 dodge bonus to AC.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Attack Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -4, 'Fighting Defensively: -4 on all attacks'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Armor Class'),
        (SELECT id FROM bonus_types WHERE name = 'Dodge'),
        2, 'Fighting Defensively: +2 dodge bonus to AC');

-- TOTAL DEFENSE
INSERT INTO sources (campaign_id, name, source_category_id, duration_type,
    action_type_id, description)
VALUES (NULL,
    'Total Defense',
    (SELECT id FROM source_categories WHERE name = 'Other'),
    'until_next_turn',
    (SELECT id FROM action_types WHERE name = 'Standard'),
    'Focusing entirely on defense. +4 dodge bonus to AC. Cannot attack or cast offensive spells.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Armor Class'),
        (SELECT id FROM bonus_types WHERE name = 'Dodge'),
        4, 'Total Defense: +4 dodge bonus to AC');

-- COVER (PARTIAL)
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Cover (Partial)',
    (SELECT id FROM source_categories WHERE name = 'Other'),
    'toggle',
    'At least half of your body is covered. +4 bonus to AC, +2 bonus on Reflex saving throws.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Armor Class'),
        (SELECT id FROM bonus_types WHERE name = 'Untyped'),
        4, 'Partial Cover: +4 bonus to AC'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Reflex Save'),
        (SELECT id FROM bonus_types WHERE name = 'Untyped'),
        2, 'Partial Cover: +2 on Reflex saves');

-- COVER (FULL)
INSERT INTO sources (campaign_id, name, source_category_id, duration_type, description)
VALUES (NULL,
    'Cover (Full)',
    (SELECT id FROM source_categories WHERE name = 'Other'),
    'toggle',
    'Completely concealed behind an obstacle. Cannot be targeted by most attacks.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Armor Class'),
        (SELECT id FROM bonus_types WHERE name = 'Untyped'),
        8, 'Full Cover: effectively untargetable; +8 AC shown for edge cases');

-- POWER ATTACK
INSERT INTO sources (campaign_id, name, source_category_id, duration_type,
    action_type_id, description)
VALUES (NULL,
    'Power Attack',
    (SELECT id FROM source_categories WHERE name = 'Feat'),
    'until_next_turn',
    (SELECT id FROM action_types WHERE name = 'Free'),
    'Trade accuracy for damage. Penalty on attack rolls, bonus on damage. Bonus is doubled for two-handed weapons and halved for off-hand. See variant sources for two-handed version.'
);

INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
VALUES
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Attack Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Penalty'),
        -1, 'Power Attack: penalty scales with BAB (-1 per 4 BAB, min -1). Update this value manually as BAB increases.'),
    (LAST_INSERT_ID(),
        (SELECT id FROM stats WHERE name = 'Damage Roll'),
        (SELECT id FROM bonus_types WHERE name = 'Untyped'),
        2, 'Power Attack: bonus scales with BAB (+2 per 4 BAB, min +2). Update manually as BAB increases.');
