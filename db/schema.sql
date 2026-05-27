-- ============================================================
-- PATHFINDER 1E ACTION & CAMPAIGN TRACKER
-- Schema v1.0
-- ============================================================

CREATE DATABASE IF NOT EXISTS pathfinder_tracker
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE pathfinder_tracker;

-- ============================================================
-- CAMPAIGNS
-- ============================================================

CREATE TABLE campaigns (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- CHARACTERS
-- ============================================================

CREATE TABLE characters (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    campaign_id  INT NOT NULL,
    name         VARCHAR(255) NOT NULL,
    is_pc        BOOLEAN DEFAULT TRUE,  -- FALSE = lightweight NPC/monster
    notes        TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        ON DELETE CASCADE
);

-- One row per level-up event; class is free text (no class table needed)
CREATE TABLE character_levels (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    character_id INT NOT NULL,
    level        INT NOT NULL,
    class_name   VARCHAR(100),
    leveled_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes        TEXT,
    FOREIGN KEY (character_id) REFERENCES characters(id)
        ON DELETE CASCADE
);

-- ============================================================
-- STATS  (the things effects modify)
-- ============================================================

CREATE TABLE stats (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(20),
    category     VARCHAR(50)
    -- category values: 'ability', 'combat', 'save', 'skill', 'other'
);

-- ============================================================
-- BONUS TYPES  (drives stacking rules)
-- ============================================================

CREATE TABLE bonus_types (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    always_stacks BOOLEAN DEFAULT FALSE
    -- always_stacks TRUE: dodge, untyped, penalty
);

-- ============================================================
-- ACTION TYPES  (action economy)
-- ============================================================

CREATE TABLE action_types (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    description   TEXT,
    max_per_round INT DEFAULT 1
    -- max_per_round: Standard=1, Move=1, Swift=1, Free=99, etc.
    -- Full-Round consuming Standard+Move is handled in app logic
);

-- ============================================================
-- SOURCE CATEGORIES  (feat, spell, condition, class feature, item, etc.)
-- ============================================================

CREATE TABLE source_categories (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- ============================================================
-- SOURCES  (the things characters have or are affected by)
-- ============================================================

CREATE TABLE sources (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    name               VARCHAR(255) NOT NULL,
    source_category_id INT NOT NULL,
    duration_type      ENUM(
                           'permanent',       -- always on (Weapon Focus, ability scores)
                           'toggle',          -- on/off at will (Combat Expertise)
                           'rounds',          -- N rounds then expires (Haste)
                           'until_next_turn', -- expires start of your next turn (Power Attack)
                           'encounter',       -- lasts whole combat (some rage powers)
                           'timed'            -- minutes/hours (Mage Armor)
                       ) NOT NULL,
    duration_value     INT,           -- NULL for permanent/toggle; N for rounds/timed
    action_type_id     INT,           -- NULL if passive (no action to activate)
    description        TEXT,
    FOREIGN KEY (source_category_id) REFERENCES source_categories(id),
    FOREIGN KEY (action_type_id) REFERENCES action_types(id)
);

-- ============================================================
-- EFFECTS  (what a source actually does mechanically)
-- ============================================================

CREATE TABLE effects (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    source_id      INT NOT NULL,
    stat_id        INT NOT NULL,
    bonus_type_id  INT NOT NULL,
    modifier       INT NOT NULL,  -- positive = bonus, negative = penalty
    condition_note TEXT,          -- user reminder: "only when flanking", etc.
    FOREIGN KEY (source_id) REFERENCES sources(id)
        ON DELETE CASCADE,
    FOREIGN KEY (stat_id) REFERENCES stats(id),
    FOREIGN KEY (bonus_type_id) REFERENCES bonus_types(id)
);

-- ============================================================
-- CHARACTER STATS  (base values per character)
-- ============================================================

CREATE TABLE character_stats (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    character_id INT NOT NULL,
    stat_id      INT NOT NULL,
    base_value   INT NOT NULL DEFAULT 0,
    FOREIGN KEY (character_id) REFERENCES characters(id)
        ON DELETE CASCADE,
    FOREIGN KEY (stat_id) REFERENCES stats(id),
    UNIQUE KEY uq_char_stat (character_id, stat_id)
);

-- ============================================================
-- CHARACTER SOURCES  (what sources a character has access to)
-- ============================================================

CREATE TABLE character_sources (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    character_id     INT NOT NULL,
    source_id        INT NOT NULL,
    is_active        BOOLEAN DEFAULT FALSE,
    rounds_remaining INT,          -- NULL unless duration_type = 'rounds'
    FOREIGN KEY (character_id) REFERENCES characters(id)
        ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

-- ============================================================
-- COMBAT SESSIONS
-- ============================================================

CREATE TABLE combat_sessions (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    campaign_id   INT NOT NULL,
    name          VARCHAR(255),
    current_round INT DEFAULT 1,
    started_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at      DATETIME,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

-- All combatants: full PCs (character_id set) and lightweight NPCs/monsters (character_id NULL)
CREATE TABLE combat_participants (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    combat_session_id INT NOT NULL,
    character_id      INT,           -- NULL = anonymous monster/NPC
    display_name      VARCHAR(255),  -- used when character_id is NULL
    initiative        INT,
    current_hp        INT,
    max_hp            INT,
    is_active         BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (combat_session_id) REFERENCES combat_sessions(id)
        ON DELETE CASCADE,
    FOREIGN KEY (character_id) REFERENCES characters(id)
);

-- ============================================================
-- ACTION TRACKING  (action economy enforcement per round)
-- ============================================================

-- Log of actions spent; queried each round to check availability
CREATE TABLE combat_action_log (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    combat_session_id INT NOT NULL,
    character_id      INT NOT NULL,
    action_type_id    INT NOT NULL,
    round_number      INT NOT NULL,
    source_id         INT,           -- which source was activated, if any
    notes             TEXT,
    FOREIGN KEY (combat_session_id) REFERENCES combat_sessions(id)
        ON DELETE CASCADE,
    FOREIGN KEY (character_id) REFERENCES characters(id),
    FOREIGN KEY (action_type_id) REFERENCES action_types(id),
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

-- Sources that modify action pool (e.g. Haste grants +1 Standard)
CREATE TABLE character_action_modifiers (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    character_id   INT NOT NULL,
    action_type_id INT NOT NULL,
    modifier       INT NOT NULL,    -- +1 Haste, -1 Slow, etc.
    source_id      INT NOT NULL,    -- the source granting this modifier
    FOREIGN KEY (character_id) REFERENCES characters(id)
        ON DELETE CASCADE,
    FOREIGN KEY (action_type_id) REFERENCES action_types(id),
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

-- ============================================================
-- INVENTORY
-- ============================================================

CREATE TABLE item_categories (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
    -- e.g. Weapon, Armor, Consumable, Gear, Magic Item, Trade Good
);

CREATE TABLE items (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    name             VARCHAR(255) NOT NULL,
    item_category_id INT NOT NULL,
    weight_lbs       DECIMAL(6,2) DEFAULT 0.00,
    value_gold       DECIMAL(10,2) DEFAULT 0.00,  -- stored in gold pieces
    is_consumable    BOOLEAN DEFAULT FALSE,
    description      TEXT,
    FOREIGN KEY (item_category_id) REFERENCES item_categories(id)
);

CREATE TABLE character_inventory (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    character_id INT NOT NULL,
    item_id      INT NOT NULL,
    quantity     INT NOT NULL DEFAULT 1,
    is_equipped  BOOLEAN DEFAULT FALSE,
    notes        TEXT,         -- "masterwork", "+1 enhancement", "lit", etc.
    acquired_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(id)
        ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id)
);

-- Links inventory items that are also sources (wands, magic items, etc.)
CREATE TABLE item_source_links (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    item_id   INT NOT NULL,
    source_id INT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items(id)
        ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

-- ============================================================
-- WEALTH LEDGER
-- All wealth changes flow through here: coins, item acquisitions,
-- sales, income, expenses. Running total = SUM(credits) - SUM(debits).
-- ============================================================

CREATE TABLE wealth_ledger (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    character_id           INT NOT NULL,
    entry_type             ENUM('credit','debit') NOT NULL,
    platinum               INT DEFAULT 0,
    gold                   INT DEFAULT 0,
    silver                 INT DEFAULT 0,
    copper                 INT DEFAULT 0,
    description            TEXT,
    character_inventory_id INT,   -- set when entry is triggered by an inventory change
    session_date           DATE,
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(id)
        ON DELETE CASCADE,
    FOREIGN KEY (character_inventory_id) REFERENCES character_inventory(id)
        ON DELETE SET NULL
);
