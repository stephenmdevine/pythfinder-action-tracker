from app.models.base_model import BaseModel


class CombatModel(BaseModel):
    """
    Handles DB operations for combat sessions, participants,
    the action log, and action economy enforcement.
    """

    # ------------------------------------------------------------------
    # COMBAT SESSIONS
    # ------------------------------------------------------------------

    def create_session(self, campaign_id: int, name: str = "") -> int:
        sql = """
            INSERT INTO combat_sessions (campaign_id, name, current_round)
            VALUES (%s, %s, 1)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (campaign_id, name))
            return cursor.lastrowid

    def get_session(self, session_id: int) -> dict | None:
        sql = "SELECT * FROM combat_sessions WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (session_id,))
            return cursor.fetchone()

    def get_sessions_by_campaign(self, campaign_id: int) -> list[dict]:
        sql = """
            SELECT * FROM combat_sessions
            WHERE campaign_id = %s
            ORDER BY started_at DESC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (campaign_id,))
            return cursor.fetchall()

    def advance_round(self, session_id: int) -> int:
        """
        Increments the round counter and returns the new round number.
        The controller is responsible for calling SourceModel.tick_rounds()
        for each PC participant after this.
        """
        sql = """
            UPDATE combat_sessions
            SET current_round = current_round + 1
            WHERE id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (session_id,))

        session = self.get_session(session_id)
        return session["current_round"]

    def end_session(self, session_id: int) -> None:
        sql = """
            UPDATE combat_sessions
            SET ended_at = NOW()
            WHERE id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (session_id,))

    # ------------------------------------------------------------------
    # COMBAT PARTICIPANTS
    # ------------------------------------------------------------------

    def add_participant(
        self,
        session_id: int,
        initiative: int,
        current_hp: int,
        max_hp: int,
        character_id: int = None,   # None for anonymous monsters/NPCs
        display_name: str = "",
    ) -> int:
        sql = """
            INSERT INTO combat_participants
                (combat_session_id, character_id, display_name,
                 initiative, current_hp, max_hp, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (
                session_id, character_id, display_name,
                initiative, current_hp, max_hp
            ))
            return cursor.lastrowid

    def get_participants(self, session_id: int, active_only: bool = True) -> list[dict]:
        """
        Returns participants ordered by initiative (highest first).
        Joins character name when character_id is set.
        """
        sql = """
            SELECT
                cp.*,
                COALESCE(c.name, cp.display_name) AS name
            FROM combat_participants cp
            LEFT JOIN characters c ON c.id = cp.character_id
            WHERE cp.combat_session_id = %s
        """
        params = [session_id]
        if active_only:
            sql += " AND cp.is_active = TRUE"
        sql += " ORDER BY cp.initiative DESC"

        with self.get_db() as (conn, cursor):
            cursor.execute(sql, tuple(params))
            return cursor.fetchall()

    def update_hp(self, participant_id: int, current_hp: int) -> None:
        sql = "UPDATE combat_participants SET current_hp = %s WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (current_hp, participant_id))

    def update_initiative(self, participant_id: int, initiative: int) -> None:
        sql = "UPDATE combat_participants SET initiative = %s WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (initiative, participant_id))

    def remove_participant(self, participant_id: int) -> None:
        """Marks a participant as inactive (defeated/fled) rather than deleting."""
        sql = "UPDATE combat_participants SET is_active = FALSE WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (participant_id,))

    # ------------------------------------------------------------------
    # ACTION ECONOMY
    # ------------------------------------------------------------------

    def log_action(
        self,
        session_id: int,
        character_id: int,
        action_type_id: int,
        round_number: int,
        source_id: int = None,
        notes: str = "",
    ) -> int:
        """
        Records an action spent by a character in a given round.
        Returns the new log entry id.
        """
        sql = """
            INSERT INTO combat_action_log
                (combat_session_id, character_id, action_type_id,
                 round_number, source_id, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (
                session_id, character_id, action_type_id,
                round_number, source_id, notes
            ))
            return cursor.lastrowid

    def get_actions_spent(
        self, session_id: int, character_id: int, round_number: int
    ) -> list[dict]:
        """
        Returns all action log entries for a character in a specific round.
        Used by the action economy check to see what's already been spent.
        """
        sql = """
            SELECT cal.*, at.name AS action_type_name, at.max_per_round
            FROM combat_action_log cal
            JOIN action_types at ON at.id = cal.action_type_id
            WHERE cal.combat_session_id = %s
              AND cal.character_id      = %s
              AND cal.round_number      = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (session_id, character_id, round_number))
            return cursor.fetchall()

    def get_action_modifiers(self, character_id: int) -> list[dict]:
        """
        Returns all active action pool modifiers for a character
        (e.g. +1 Standard from Haste).
        Only returns modifiers whose source is currently active.
        """
        sql = """
            SELECT cam.*, at.name AS action_type_name, at.max_per_round,
                   s.name AS source_name
            FROM character_action_modifiers cam
            JOIN action_types at ON at.id = cam.action_type_id
            JOIN sources      s  ON s.id  = cam.source_id
            JOIN character_sources cs ON cs.source_id = cam.source_id
                                     AND cs.character_id = cam.character_id
            WHERE cam.character_id = %s
              AND cs.is_active = TRUE
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id,))
            return cursor.fetchall()

    def can_take_action(
        self,
        session_id: int,
        character_id: int,
        round_number: int,
        action_type_id: int,
        action_type_name: str,
        base_max: int,
    ) -> tuple[bool, str]:
        """
        Core action economy check. Returns (allowed: bool, reason: str).

        Checks:
          1. Counts how many of this action type the character has already used.
          2. Applies any active modifiers (Haste, Slow, etc.).
          3. Applies the Full-Round mutual exclusion rule:
             - If a Full-Round action was taken, no Standard or Move allowed.
             - If a Standard was taken, no Full-Round allowed.

        Returns True with an empty reason string if the action is available.
        Returns False with a human-readable reason if it is not.
        """
        spent = self.get_actions_spent(session_id, character_id, round_number)
        modifiers = self.get_action_modifiers(character_id)

        # Build a dict of action_type_id -> count spent this round
        spent_counts: dict[int, int] = {}
        spent_names: dict[int, str] = {}
        for entry in spent:
            aid = entry["action_type_id"]
            spent_counts[aid] = spent_counts.get(aid, 0) + 1
            spent_names[aid]  = entry["action_type_name"]

        # Full-Round mutual exclusion
        full_round_id = self._get_action_type_id_by_name("Full-Round", spent)
        standard_id   = self._get_action_type_id_by_name("Standard",   spent)

        if action_type_name == "Full-Round" and standard_id and spent_counts.get(standard_id, 0) > 0:
            return False, "Cannot take a Full-Round action: a Standard action was already used this round."
        if action_type_name == "Full-Round" and full_round_id and spent_counts.get(full_round_id, 0) > 0:
            return False, "A Full-Round action has already been taken this round."
        if action_type_name in ("Standard", "Move") and full_round_id and spent_counts.get(full_round_id, 0) > 0:
            return False, f"Cannot take a {action_type_name} action: a Full-Round action was already used this round."

        # Compute effective max for this action type
        pool_modifier = sum(
            m["modifier"] for m in modifiers
            if m["action_type_id"] == action_type_id
        )
        effective_max = base_max + pool_modifier

        already_spent = spent_counts.get(action_type_id, 0)
        if already_spent >= effective_max:
            modifier_note = f" (modified by active sources)" if pool_modifier != 0 else ""
            return (
                False,
                f"No {action_type_name} actions remaining this round "
                f"(limit: {effective_max}{modifier_note})."
            )

        return True, ""

    def _get_action_type_id_by_name(
        self, name: str, spent_entries: list[dict]
    ) -> int | None:
        """Helper: find an action_type_id from already-fetched spent entries by name."""
        for entry in spent_entries:
            if entry["action_type_name"] == name:
                return entry["action_type_id"]
        return None

    def add_action_modifier(
        self,
        character_id: int,
        action_type_id: int,
        modifier: int,
        source_id: int,
    ) -> int:
        sql = """
            INSERT INTO character_action_modifiers
                (character_id, action_type_id, modifier, source_id)
            VALUES (%s, %s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, action_type_id, modifier, source_id))
            return cursor.lastrowid

    def remove_action_modifier(self, character_id: int, source_id: int) -> None:
        """Removes action pool modifiers granted by a specific source (e.g. Haste ended)."""
        sql = """
            DELETE FROM character_action_modifiers
            WHERE character_id = %s AND source_id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, source_id))
