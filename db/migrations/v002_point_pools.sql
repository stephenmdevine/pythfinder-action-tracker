-- ============================================================
-- PYTHFINDER ACTION TRACKER
-- Migration v002 — Point Pools & Investment-Scaled Effects
-- ============================================================
-- Run after schema.sql and seed.sql:
--   mysql -u root -p < db/migrations/v002_point_pools.sql
-- ============================================================

USE pythfinder_tracker;

-- ============================================================
-- POINT POOLS
-- A resource bucket attached to a character_source.
-- A source may have zero or one point pool.
-- ============================================================

CREATE TABLE point_pools (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    character_source_id     INT NOT NULL UNIQUE,    -- one pool per character_source
    max_points              INT NOT NULL,
    current_points          INT NOT NULL,
    replenish_type          ENUM('daily', 'encounter', 'manual') NOT NULL,
    notes                   TEXT,                   -- e.g. "Refills after 8hrs rest"
    FOREIGN KEY (character_source_id) REFERENCES character_sources(id)
        ON DELETE CASCADE
);

-- ============================================================
-- POOL ALLOCATIONS (sub-pools)
-- A parent point_pool can be divided into named child allocations.
-- Each allocation has its own current/max and is linked to a
-- specific character_source (the implement, focus school, etc.)
-- that draws from it.
--
-- Example — Occultist with 7 focus points:
--   parent pool (id=1): max=7, current=7
--     allocation (id=1): name="Transmutation", allocated=3, remaining=3
--     allocation (id=2): name="Divination",    allocated=4, remaining=4
-- ============================================================

CREATE TABLE pool_allocations (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    parent_pool_id          INT NOT NULL,
    character_source_id     INT NOT NULL,           -- the sub-source this allocation feeds
    name                    VARCHAR(255) NOT NULL,  -- e.g. "Transmutation implement"
    allocated_points        INT NOT NULL DEFAULT 0, -- points assigned from parent pool
    remaining_points        INT NOT NULL DEFAULT 0, -- points not yet spent from this allocation
    FOREIGN KEY (parent_pool_id) REFERENCES point_pools(id)
        ON DELETE CASCADE,
    FOREIGN KEY (character_source_id) REFERENCES character_sources(id)
        ON DELETE CASCADE
);

-- ============================================================
-- MODIFY effects TABLE
-- modifier becomes nullable. Either modifier (fixed) OR
-- pool_allocation_id (user-set dynamic value) is used — not both.
--
-- When pool_allocation_id is set, the active modifier value is
-- stored in effect_active_modifiers (see below) and updated
-- each time the user re-invests points.
-- ============================================================

ALTER TABLE effects
    MODIFY COLUMN modifier INT NULL,
    ADD COLUMN pool_allocation_id INT NULL
        AFTER modifier,
    ADD CONSTRAINT fk_effect_pool_allocation
        FOREIGN KEY (pool_allocation_id) REFERENCES pool_allocations(id)
        ON DELETE SET NULL;

-- ============================================================
-- EFFECT ACTIVE MODIFIERS
-- For investment-scaled effects, stores the user-entered modifier
-- value that is currently in effect for a given character.
-- One row per (effect_id, character_id) pair.
--
-- When the user re-invests points and enters a new bonus value,
-- this row is updated. The stacking engine reads from here
-- instead of effects.modifier for pool-linked effects.
-- ============================================================

CREATE TABLE effect_active_modifiers (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    effect_id       INT NOT NULL,
    character_id    INT NOT NULL,
    current_modifier INT NOT NULL DEFAULT 0,        -- user-entered value
    UNIQUE KEY uq_effect_character (effect_id, character_id),
    FOREIGN KEY (effect_id) REFERENCES effects(id)
        ON DELETE CASCADE,
    FOREIGN KEY (character_id) REFERENCES characters(id)
        ON DELETE CASCADE
);
