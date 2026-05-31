from app.models.base_model import BaseModel


class BonusTypeModel(BaseModel):
    """
    Handles DB operations for bonus_types.
    Also contains the stacking resolution engine — the core math
    that computes a character's final modifier for any given stat.
    """

    def get_all(self) -> list[dict]:
        sql = "SELECT * FROM bonus_types ORDER BY name ASC"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql)
            return cursor.fetchall()

    def get_by_id(self, bonus_type_id: int) -> dict | None:
        sql = "SELECT * FROM bonus_types WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (bonus_type_id,))
            return cursor.fetchone()

    def get_by_name(self, name: str) -> dict | None:
        sql = "SELECT * FROM bonus_types WHERE name = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (name,))
            return cursor.fetchone()

    # ------------------------------------------------------------------
    # STACKING RESOLUTION ENGINE
    # ------------------------------------------------------------------

    def resolve_modifiers(self, effects: list[dict]) -> int:
        """
        Given a list of active effect rows (each with keys: modifier,
        bonus_type_name, always_stacks), applies PF1e stacking rules
        and returns the final net modifier for a stat.

        Rules:
          - always_stacks = TRUE  → every modifier sums (dodge, untyped, penalties)
          - always_stacks = FALSE → only the single highest modifier per type applies
          - Penalties (negative modifiers) always stack regardless of type

        This method is pure logic — it receives pre-fetched rows and
        returns an integer. No DB calls happen here.
        """
        if not effects:
            return 0

        # Separate always-stacking effects from typed bonuses
        always_stack_total = 0
        typed_bonuses: dict[str, int] = {}  # type_name -> highest modifier seen

        for effect in effects:
            modifier     = effect["modifier"]
            type_name    = effect["bonus_type_name"]
            always_stacks = effect["always_stacks"]

            # Penalties always stack (even from "typed" sources)
            if modifier < 0:
                always_stack_total += modifier
                continue

            if always_stacks:
                always_stack_total += modifier
            else:
                # Keep only the highest bonus for this type
                if type_name not in typed_bonuses or modifier > typed_bonuses[type_name]:
                    typed_bonuses[type_name] = modifier

        typed_total = sum(typed_bonuses.values())
        return always_stack_total + typed_total

    def resolve_modifiers_for_stat(
        self, character_id: int, stat_id: int
    ) -> dict:
        """
        Full pipeline: fetches all active effects targeting a stat for a
        character, resolves all three effect types, runs resolve_modifiers(),
        and returns a breakdown dict:

        {
            "stat_id":       int,
            "net_modifier":  int,
            "effects":       [list of contributing effect rows],
            "suppressed":    [list of effects that lost to a higher typed bonus]
        }

        Effect type resolution:
          Fixed:             uses e.modifier directly
          Investment-scaled: uses eam.current_modifier (user-entered)
          Formula-scaled:    computes base_value + floor((stat_value * multiplier) / divisor)
                             where stat_value is the character's current resolved value
                             for scaling_stat_id
        """
        sql = """
            SELECT
                e.id                    AS effect_id,
                e.modifier,
                e.pool_allocation_id,
                e.condition_note,
                e.base_value,
                e.scaling_stat_id,
                e.multiplier,
                e.divisor,
                bt.name                 AS bonus_type_name,
                bt.always_stacks,
                s.name                  AS source_name,
                eam.current_modifier    AS investment_modifier,
                sc_stat.name            AS scaling_stat_name
            FROM character_sources cs
            JOIN effects e              ON e.source_id     = cs.source_id
            JOIN bonus_types bt         ON bt.id           = e.bonus_type_id
            JOIN sources s              ON s.id            = e.source_id
            LEFT JOIN effect_active_modifiers eam
                                        ON eam.effect_id   = e.id
                                       AND eam.character_id = %s
            LEFT JOIN stats sc_stat     ON sc_stat.id      = e.scaling_stat_id
            WHERE cs.character_id = %s
              AND cs.is_active    = TRUE
              AND e.stat_id       = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, character_id, stat_id))
            raw_effects = cursor.fetchall()

        # Resolve each effect to a working integer modifier
        effects = []
        for row in raw_effects:
            e = dict(row)

            if e["scaling_stat_id"] is not None:
                # Formula-scaled: base_value + floor((stat_value * multiplier) / divisor)
                stat_value = self._get_base_stat_value(character_id, e["scaling_stat_id"])
                base       = e["base_value"] or 0
                computed   = base + int((stat_value * float(e["multiplier"])) / e["divisor"])
                e["modifier"] = computed
                e["modifier_display"] = (
                    f"{base:+d} + floor({e['scaling_stat_name']} "
                    f"× {e['multiplier']} ÷ {e['divisor']}) = {computed:+d}"
                )

            elif e["pool_allocation_id"] is not None:
                # Investment-scaled: user-entered value
                inv = e["investment_modifier"]
                if inv is None or inv == 0:
                    continue   # uninvested — contributes nothing
                e["modifier"] = inv
                e["modifier_display"] = f"{inv:+d} (invested)"

            else:
                # Fixed modifier
                e["modifier_display"] = f"{e['modifier']:+d}"

            effects.append(e)

        # Determine suppressed typed bonuses
        typed_best: dict[str, int] = {}
        for e in effects:
            if e["modifier"] >= 0 and not e["always_stacks"]:
                name = e["bonus_type_name"]
                if name not in typed_best or e["modifier"] > typed_best[name]:
                    typed_best[name] = e["modifier"]

        contributing, suppressed = [], []
        for e in effects:
            if e["modifier"] >= 0 and not e["always_stacks"]:
                if e["modifier"] < typed_best.get(e["bonus_type_name"], 0):
                    suppressed.append(e)
                    continue
            contributing.append(e)

        return {
            "stat_id":      stat_id,
            "net_modifier": self.resolve_modifiers(contributing),
            "effects":      contributing,
            "suppressed":   suppressed,
        }

    def _get_base_stat_value(self, character_id: int, stat_id: int) -> int:
        """
        Returns a character's base value for a stat, used when evaluating
        formula-scaled effects. Reads directly from character_stats.

        Note: this intentionally uses the base value only, not the fully
        resolved value, to avoid circular resolution (a stat that scales
        off itself). For ability modifiers as the scaling stat, the user
        should select the modifier stat (e.g. 'STR Mod') not the score,
        and ensure that stat's base value reflects the current modifier.
        """
        sql = """
            SELECT base_value FROM character_stats
            WHERE character_id = %s AND stat_id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, stat_id))
            row = cursor.fetchone()
            return row["base_value"] if row else 0


class EffectModel(BaseModel):
    """
    Handles DB operations for effects — the individual mechanical
    changes that a source applies to a stat.
    """

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create(
        self,
        source_id: int,
        stat_id: int,
        bonus_type_id: int,
        modifier: int = None,
        condition_note: str = "",
        base_value: int = None,
        scaling_stat_id: int = None,
        multiplier: float = 1.0,
        divisor: int = 1,
    ) -> int:
        """
        Adds an effect to a source. Returns the new effect id.

        Exactly one effect type must be specified:
          Fixed:             pass modifier (int)
          Formula-scaled:    pass scaling_stat_id; optionally base_value,
                             multiplier, divisor
          Investment-scaled: pass neither — call set_pool_allocation() after

        modifier: positive = bonus, negative = penalty.
        condition_note: free-text reminder, e.g.
            "Only on attack rolls against flat-footed targets."
        base_value: flat addend for formula effects (default 0).
        scaling_stat_id: FK to stats — the stat whose value drives scaling.
        multiplier: scaling factor applied to the stat value (default 1.0).
        divisor: divisor applied after multiplying (default 1).
        """
        sql = """
            INSERT INTO effects
                (source_id, stat_id, bonus_type_id, modifier, condition_note,
                 base_value, scaling_stat_id, multiplier, divisor)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (
                source_id, stat_id, bonus_type_id, modifier, condition_note,
                base_value, scaling_stat_id, multiplier, divisor
            ))
            return cursor.lastrowid

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_by_id(self, effect_id: int) -> dict | None:
        sql = """
            SELECT e.*, s.name AS source_name, st.name AS stat_name,
                   bt.name AS bonus_type_name, bt.always_stacks
            FROM effects e
            JOIN sources     s  ON s.id  = e.source_id
            JOIN stats       st ON st.id = e.stat_id
            JOIN bonus_types bt ON bt.id = e.bonus_type_id
            WHERE e.id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (effect_id,))
            return cursor.fetchone()

    def get_by_source(self, source_id: int) -> list[dict]:
        """
        Returns all effects for a given source, with stat and bonus type names.
        Uses effect_id alias to keep dict shape consistent with all other queries.
        """
        sql = """
            SELECT e.id AS effect_id, e.source_id, e.stat_id, e.bonus_type_id,
                   e.modifier, e.condition_note, e.pool_allocation_id,
                   e.base_value, e.scaling_stat_id, e.multiplier, e.divisor,
                   st.name AS stat_name, st.abbreviation,
                   bt.name AS bonus_type_name, bt.always_stacks,
                   sc.name AS scaling_stat_name
            FROM effects e
            JOIN stats       st  ON st.id  = e.stat_id
            JOIN bonus_types bt  ON bt.id  = e.bonus_type_id
            LEFT JOIN stats  sc  ON sc.id  = e.scaling_stat_id
            WHERE e.source_id = %s
            ORDER BY st.category ASC, st.name ASC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (source_id,))
            return cursor.fetchall()

    def get_all_active_for_character(self, character_id: int) -> list[dict]:
        """
        Returns every active effect currently applying to a character,
        across all active sources. Used for a full character modifier summary.

        All three effect types are included. Formula-scaled effects include
        raw scaling parameters — the caller (controller or view) is responsible
        for evaluating the formula using current stat values if a computed
        display value is needed. For fully resolved values per stat, use
        BonusTypeModel.resolve_modifiers_for_stat() instead.
        """
        sql = """
            SELECT
                e.id                    AS effect_id,
                e.modifier,
                e.pool_allocation_id,
                e.base_value,
                e.scaling_stat_id,
                e.multiplier,
                e.divisor,
                e.condition_note,
                st.id                   AS stat_id,
                st.name                 AS stat_name,
                st.abbreviation,
                bt.name                 AS bonus_type_name,
                bt.always_stacks,
                s.name                  AS source_name,
                sc_stat.name            AS scaling_stat_name,
                COALESCE(eam.current_modifier, e.modifier) AS resolved_modifier
            FROM character_sources cs
            JOIN effects     e      ON e.source_id    = cs.source_id
            JOIN stats       st     ON st.id           = e.stat_id
            JOIN bonus_types bt     ON bt.id           = e.bonus_type_id
            JOIN sources     s      ON s.id            = e.source_id
            LEFT JOIN stats sc_stat ON sc_stat.id      = e.scaling_stat_id
            LEFT JOIN effect_active_modifiers eam
                                    ON eam.effect_id   = e.id
                                   AND eam.character_id = %s
            WHERE cs.character_id = %s
              AND cs.is_active    = TRUE
            ORDER BY st.category ASC, st.name ASC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, character_id))
            raw = cursor.fetchall()

        # Exclude uninvested pool-linked effects
        return [
            dict(row) for row in raw
            if not (
                row["pool_allocation_id"] is not None
                and (row["resolved_modifier"] or 0) == 0
            )
        ]

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(
        self,
        effect_id: int,
        stat_id: int = None,
        bonus_type_id: int = None,
        modifier: int = None,
        condition_note: str = None,
        base_value: int = None,
        scaling_stat_id: int = None,
        multiplier: float = None,
        divisor: int = None,
    ) -> None:
        fields, values = [], []
        if stat_id is not None:
            fields.append("stat_id = %s");         values.append(stat_id)
        if bonus_type_id is not None:
            fields.append("bonus_type_id = %s");   values.append(bonus_type_id)
        if modifier is not None:
            fields.append("modifier = %s");         values.append(modifier)
        if condition_note is not None:
            fields.append("condition_note = %s");   values.append(condition_note)
        if base_value is not None:
            fields.append("base_value = %s");       values.append(base_value)
        if scaling_stat_id is not None:
            fields.append("scaling_stat_id = %s");  values.append(scaling_stat_id)
        if multiplier is not None:
            fields.append("multiplier = %s");       values.append(multiplier)
        if divisor is not None:
            fields.append("divisor = %s");          values.append(divisor)

        if not fields:
            return

        values.append(effect_id)
        sql = f"UPDATE effects SET {', '.join(fields)} WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, tuple(values))

    def set_formula_scaling(
        self,
        effect_id: int,
        scaling_stat_id: int,
        base_value: int = 0,
        multiplier: float = 1.0,
        divisor: int = 1,
    ) -> None:
        """
        Marks an effect as formula-scaled and sets its scaling parameters.
        Clears modifier and pool_allocation_id — the three effect types
        are mutually exclusive.
        """
        sql = """
            UPDATE effects
            SET modifier           = NULL,
                pool_allocation_id = NULL,
                scaling_stat_id    = %s,
                base_value         = %s,
                multiplier         = %s,
                divisor            = %s
            WHERE id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (scaling_stat_id, base_value, multiplier, divisor, effect_id))

    def set_pool_allocation(self, effect_id: int, pool_allocation_id: int) -> None:
        """
        Links an effect to a pool allocation, marking it as investment-scaled.
        Sets modifier to NULL at the same time — an effect cannot have both
        a fixed modifier and an allocation link simultaneously.
        """
        sql = """
            UPDATE effects
            SET pool_allocation_id = %s,
                modifier           = NULL
            WHERE id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (pool_allocation_id, effect_id))

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete(self, effect_id: int) -> None:
        sql = "DELETE FROM effects WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (effect_id,))

    def delete_all_for_source(self, source_id: int) -> None:
        """Removes all effects belonging to a source (e.g. before re-adding them)."""
        sql = "DELETE FROM effects WHERE source_id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (source_id,))
