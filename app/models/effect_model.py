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
        character, runs resolve_modifiers(), and returns a breakdown dict:

        {
            "stat_id":       int,
            "net_modifier":  int,
            "effects":       [list of contributing effect rows],
            "suppressed":    [list of effects that lost to a higher typed bonus]
        }
        """
        sql = """
            SELECT
                e.id            AS effect_id,
                e.modifier,
                e.condition_note,
                bt.name         AS bonus_type_name,
                bt.always_stacks,
                s.name          AS source_name
            FROM character_sources cs
            JOIN effects e     ON e.source_id    = cs.source_id
            JOIN bonus_types bt ON bt.id         = e.bonus_type_id
            JOIN sources s     ON s.id           = e.source_id
            WHERE cs.character_id = %s
              AND cs.is_active    = TRUE
              AND e.stat_id       = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, stat_id))
            effects = cursor.fetchall()

        # Determine which typed bonuses are suppressed
        typed_best: dict[str, int] = {}
        for e in effects:
            if e["modifier"] >= 0 and not e["always_stacks"]:
                name = e["bonus_type_name"]
                if name not in typed_best or e["modifier"] > typed_best[name]:
                    typed_best[name] = e["modifier"]

        contributing = []
        suppressed   = []
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
        modifier: int,
        condition_note: str = "",
    ) -> int:
        """
        Adds an effect to a source. Returns the new effect id.

        modifier: positive = bonus, negative = penalty.
        condition_note: free-text reminder for the user, e.g.
            "Only applies on attack rolls against flat-footed targets."
        """
        sql = """
            INSERT INTO effects (source_id, stat_id, bonus_type_id, modifier, condition_note)
            VALUES (%s, %s, %s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (source_id, stat_id, bonus_type_id, modifier, condition_note))
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
        """
        sql = """
            SELECT e.*, st.name AS stat_name, st.abbreviation,
                   bt.name AS bonus_type_name, bt.always_stacks
            FROM effects e
            JOIN stats       st ON st.id = e.stat_id
            JOIN bonus_types bt ON bt.id = e.bonus_type_id
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
        """
        sql = """
            SELECT
                e.id            AS effect_id,
                e.modifier,
                e.condition_note,
                st.id           AS stat_id,
                st.name         AS stat_name,
                st.abbreviation,
                bt.name         AS bonus_type_name,
                bt.always_stacks,
                s.name          AS source_name
            FROM character_sources cs
            JOIN effects     e  ON e.source_id  = cs.source_id
            JOIN stats       st ON st.id         = e.stat_id
            JOIN bonus_types bt ON bt.id         = e.bonus_type_id
            JOIN sources     s  ON s.id          = e.source_id
            WHERE cs.character_id = %s
              AND cs.is_active    = TRUE
            ORDER BY st.category ASC, st.name ASC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id,))
            return cursor.fetchall()

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
    ) -> None:
        fields, values = [], []
        if stat_id is not None:
            fields.append("stat_id = %s"); values.append(stat_id)
        if bonus_type_id is not None:
            fields.append("bonus_type_id = %s"); values.append(bonus_type_id)
        if modifier is not None:
            fields.append("modifier = %s"); values.append(modifier)
        if condition_note is not None:
            fields.append("condition_note = %s"); values.append(condition_note)

        if not fields:
            return

        values.append(effect_id)
        sql = f"UPDATE effects SET {', '.join(fields)} WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, tuple(values))

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
