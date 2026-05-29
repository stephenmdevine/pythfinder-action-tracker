from app.controllers.base_controller import BaseController
from app.controllers.point_pool_controller import PointPoolController
from app.models.combat_model import CombatModel
from app.models.source_model import SourceModel


class CombatController(BaseController):
    """
    Manages the full combat session lifecycle for the Action Tracker screen:

        1. Start session — add participants, roll initiative
        2. Each turn     — activate sources (with action economy enforcement)
        3. Each round    — advance round, tick durations, expire sources
        4. End combat    — replenish encounter pools, clear transient state

    This is the most orchestration-heavy controller. It coordinates
    CombatModel, SourceModel, and PointPoolController so the View only
    needs to call one method per user action.
    """

    def __init__(self):
        self.combat      = CombatModel()
        self.sources     = SourceModel()
        self.pool_ctrl   = PointPoolController()

    # ------------------------------------------------------------------
    # SESSION MANAGEMENT
    # ------------------------------------------------------------------

    def start_combat(self, campaign_id: int, name: str = "") -> dict:
        try:
            session_id = self.combat.create_session(campaign_id, name)
            session    = self.combat.get_session(session_id)
            return self._ok(session, f"Combat session '{name or 'Unnamed'}' started.")
        except Exception as e:
            return self._err(f"Failed to start combat: {e}")

    def get_session(self, session_id: int) -> dict:
        try:
            session = self.combat.get_session(session_id)
            if not session:
                return self._err(f"Session {session_id} not found.")
            return self._ok(session)
        except Exception as e:
            return self._err(f"Failed to load session: {e}")

    def end_combat(self, session_id: int, character_ids: list[int]) -> dict:
        """
        Ends the combat session:
            - Marks session as ended
            - Deactivates all toggle/round sources on all PC participants
            - Replenishes encounter-type pools for all PC participants
        character_ids: list of full PC character ids in this session.
        """
        try:
            self.combat.end_session(session_id)

            replenished = []
            for character_id in character_ids:
                # Deactivate all non-permanent active sources
                active = self.sources.get_character_sources(
                    character_id, active_only=True
                )
                for cs in active:
                    if cs["duration_type"] != "permanent":
                        self.sources.set_active(cs["character_source_id"], False)

                # Replenish encounter pools
                result = self.pool_ctrl.replenish_after_encounter(character_id)
                if result["data"]:
                    replenished.extend(result["data"])

            msg = "Combat ended."
            if replenished:
                msg += f" Encounter pools restored: {', '.join(replenished)}."
            return self._ok(message=msg)
        except Exception as e:
            return self._err(f"Failed to end combat: {e}")

    def list_sessions(self, campaign_id: int) -> dict:
        try:
            sessions = self.combat.get_sessions_by_campaign(campaign_id)
            return self._ok(sessions)
        except Exception as e:
            return self._err(f"Failed to list sessions: {e}")

    # ------------------------------------------------------------------
    # PARTICIPANTS & INITIATIVE
    # ------------------------------------------------------------------

    def add_participant(
        self,
        session_id: int,
        initiative: int,
        current_hp: int,
        max_hp: int,
        character_id: int = None,
        display_name: str = "",
    ) -> dict:
        """
        Adds a combatant. Full PCs supply character_id; anonymous
        monsters/NPCs supply only display_name.
        """
        if character_id is None and not display_name.strip():
            return self._err("A display name is required for non-character participants.")
        try:
            participant_id = self.combat.add_participant(
                session_id, initiative, current_hp, max_hp,
                character_id, display_name.strip()
            )
            participants = self.combat.get_participants(session_id)
            return self._ok(
                participants,
                f"{'Character' if character_id else display_name} added to initiative."
            )
        except Exception as e:
            return self._err(f"Failed to add participant: {e}")

    def get_initiative_order(self, session_id: int) -> dict:
        """
        Returns participants sorted highest initiative first,
        annotated with the current session round.
        """
        try:
            session      = self.combat.get_session(session_id)
            participants = self.combat.get_participants(session_id)
            return self._ok({
                "round":        session["current_round"],
                "participants": participants,
            })
        except Exception as e:
            return self._err(f"Failed to load initiative order: {e}")

    def update_hp(
        self, session_id: int, participant_id: int, new_hp: int
    ) -> dict:
        try:
            self.combat.update_hp(participant_id, new_hp)
            participants = self.combat.get_participants(session_id)
            return self._ok(participants)
        except Exception as e:
            return self._err(f"Failed to update HP: {e}")

    def remove_participant(self, session_id: int, participant_id: int) -> dict:
        try:
            self.combat.remove_participant(participant_id)
            participants = self.combat.get_participants(session_id)
            return self._ok(participants, "Participant removed from combat.")
        except Exception as e:
            return self._err(f"Failed to remove participant: {e}")

    # ------------------------------------------------------------------
    # ROUND MANAGEMENT
    # ------------------------------------------------------------------

    def advance_round(
        self, session_id: int, character_ids: list[int]
    ) -> dict:
        """
        Advances to the next round:
            1. Increments the session round counter
            2. Ticks down duration on all active timed sources for each PC
            3. Returns any sources that just expired for UI notification

        character_ids: list of full PC character ids in this session.
        """
        try:
            new_round = self.combat.advance_round(session_id)
            expired_notices = []

            for character_id in character_ids:
                expired = self.sources.tick_rounds(character_id)
                for e in expired:
                    expired_notices.append(
                        f"'{e['name']}' expired on character {character_id}."
                    )

            return self._ok(
                {
                    "new_round": new_round,
                    "expired":   expired_notices,
                },
                f"Round {new_round} started."
                + (f" Expired: {', '.join(expired_notices)}" if expired_notices else "")
            )
        except Exception as e:
            return self._err(f"Failed to advance round: {e}")

    # ------------------------------------------------------------------
    # ACTION ECONOMY & SOURCE ACTIVATION
    # ------------------------------------------------------------------

    def activate_source_in_combat(
        self,
        session_id: int,
        character_id: int,
        character_source_id: int,
        round_number: int,
    ) -> dict:
        """
        The main Action Tracker method. Called when the user clicks
        a source button during their turn.

        Steps:
            1. Load the source to get its action cost and duration
            2. If it has an action cost, run the action economy check
            3. If allowed, activate the source and log the action
            4. Return the updated state for the UI to refresh

        Returns success with the updated source state, or failure with
        a human-readable reason the UI can display in a dialog.
        """
        try:
            # Fetch the character_source row joined with source detail
            char_sources = self.sources.get_character_sources(character_id)
            cs = next(
                (s for s in char_sources if s["character_source_id"] == character_source_id),
                None
            )
            if not cs:
                return self._err("Source not found on this character.")

            # --- Action economy check ---
            if cs["action_type_id"] is not None:
                allowed, reason = self.combat.can_take_action(
                    session_id        = session_id,
                    character_id      = character_id,
                    round_number      = round_number,
                    action_type_id    = cs["action_type_id"],
                    action_type_name  = cs["action_type_name"],
                    base_max          = 1,  # default; modifiers applied inside
                )
                if not allowed:
                    return self._err(reason)

                # Log the action spent
                self.combat.log_action(
                    session_id     = session_id,
                    character_id   = character_id,
                    action_type_id = cs["action_type_id"],
                    round_number   = round_number,
                    source_id      = cs["id"],
                )

            # --- Activate the source ---
            duration_value = None
            if cs["duration_type"] == "rounds":
                duration_value = cs["duration_value"]
            elif cs["duration_type"] == "until_next_turn":
                duration_value = 1

            self.sources.set_active(character_source_id, True, duration_value)

            # Return refreshed source list and action log for this round
            updated_sources = self.sources.get_character_sources(character_id)
            actions_spent   = self.combat.get_actions_spent(
                session_id, character_id, round_number
            )
            return self._ok(
                {
                    "sources":       updated_sources,
                    "actions_spent": actions_spent,
                },
                f"'{cs['name']}' activated."
            )
        except Exception as e:
            return self._err(f"Failed to activate source: {e}")

    def deactivate_source_in_combat(
        self,
        character_id: int,
        character_source_id: int,
    ) -> dict:
        """
        Manually deactivates a source mid-combat (e.g. the user drops
        a stance, a condition is cured, or a concentration spell ends).
        Does not refund the action that was spent to activate it.
        """
        try:
            self.sources.set_active(character_source_id, False)
            updated_sources = self.sources.get_character_sources(character_id)
            return self._ok(updated_sources, "Source deactivated.")
        except Exception as e:
            return self._err(f"Failed to deactivate source: {e}")

    def get_action_summary(
        self, session_id: int, character_id: int, round_number: int
    ) -> dict:
        """
        Returns a summary of actions spent and remaining for a character
        in the current round. Used to populate the action economy display
        in the Action Tracker UI.
        """
        try:
            spent     = self.combat.get_actions_spent(
                session_id, character_id, round_number
            )
            modifiers = self.combat.get_action_modifiers(character_id)

            # Count spent by type
            spent_counts: dict[str, int] = {}
            for entry in spent:
                name = entry["action_type_name"]
                spent_counts[name] = spent_counts.get(name, 0) + 1

            # Build modifier summary per action type
            modifier_summary: dict[str, int] = {}
            for m in modifiers:
                name = m["action_type_name"]
                modifier_summary[name] = modifier_summary.get(name, 0) + m["modifier"]

            return self._ok({
                "round":            round_number,
                "spent_counts":     spent_counts,
                "pool_modifiers":   modifier_summary,
                "spent_log":        spent,
            })
        except Exception as e:
            return self._err(f"Failed to load action summary: {e}")
