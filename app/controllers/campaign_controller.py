from app.controllers.base_controller import BaseController
from app.models.campaign_model import CampaignModel
from app.models.character_model import CharacterModel


class CampaignController(BaseController):
    """
    Handles campaign and character lifecycle:
        - Campaign CRUD
        - Character creation and editing
        - Leveling up (recording level events and new sources)

    Does not touch stats, sources, or inventory — those belong to
    CharacterSheetController and SourceController respectively.
    """

    def __init__(self):
        self.campaigns  = CampaignModel()
        self.characters = CharacterModel()

    # ------------------------------------------------------------------
    # CAMPAIGNS
    # ------------------------------------------------------------------

    def create_campaign(self, name: str, description: str = "") -> dict:
        if not name.strip():
            return self._err("Campaign name cannot be empty.")
        try:
            campaign_id = self.campaigns.create(name.strip(), description.strip())
            campaign    = self.campaigns.get_by_id(campaign_id)
            return self._ok(campaign, f"Campaign '{name}' created.")
        except Exception as e:
            return self._err(f"Failed to create campaign: {e}")

    def get_campaign(self, campaign_id: int) -> dict:
        try:
            campaign = self.campaigns.get_by_id(campaign_id)
            if not campaign:
                return self._err(f"Campaign {campaign_id} not found.")
            return self._ok(campaign)
        except Exception as e:
            return self._err(f"Failed to load campaign: {e}")

    def list_campaigns(self) -> dict:
        try:
            return self._ok(self.campaigns.get_all())
        except Exception as e:
            return self._err(f"Failed to list campaigns: {e}")

    def update_campaign(self, campaign_id: int, name: str = None, description: str = None) -> dict:
        try:
            self.campaigns.update(campaign_id, name=name, description=description)
            campaign = self.campaigns.get_by_id(campaign_id)
            return self._ok(campaign, "Campaign updated.")
        except Exception as e:
            return self._err(f"Failed to update campaign: {e}")

    def delete_campaign(self, campaign_id: int) -> dict:
        try:
            campaign = self.campaigns.get_by_id(campaign_id)
            if not campaign:
                return self._err(f"Campaign {campaign_id} not found.")
            self.campaigns.delete(campaign_id)
            return self._ok(message=f"Campaign '{campaign['name']}' deleted.")
        except Exception as e:
            return self._err(f"Failed to delete campaign: {e}")

    # ------------------------------------------------------------------
    # CHARACTERS
    # ------------------------------------------------------------------

    def create_character(
        self,
        campaign_id: int,
        name: str,
        is_pc: bool = True,
        notes: str = "",
    ) -> dict:
        if not name.strip():
            return self._err("Character name cannot be empty.")
        campaign = self.campaigns.get_by_id(campaign_id)
        if not campaign:
            return self._err(f"Campaign {campaign_id} not found.")
        try:
            character_id = self.characters.create(
                campaign_id, name.strip(), is_pc, notes.strip()
            )
            character = self.characters.get_by_id(character_id)
            return self._ok(character, f"Character '{name}' created.")
        except Exception as e:
            return self._err(f"Failed to create character: {e}")

    def initialize_character_stats(
        self, character_id: int, stat_values: dict
    ) -> dict:
        """
        Sets initial stat values for a newly created character.
        stat_values: {stat_id: value, ...}
        Called immediately after create_character, from the
        CharacterInitDialog in the view layer.
        """
        from app.models.stat_model import StatModel
        stats = StatModel()
        errors = []
        for stat_id, value in stat_values.items():
            try:
                stats.set_base_value(character_id, stat_id, value)
            except Exception as e:
                errors.append(f"Stat {stat_id}: {e}")
        if errors:
            return self._err(f"Some stats failed: {'; '.join(errors)}")
        return self._ok(message="Character stats initialized.")

    def get_core_stats(self) -> dict:
        """
        Returns the subset of stats shown in the initialization modal:
        ability scores, their modifiers, core combat stats, and saves.
        Used to populate the CharacterInitDialog.
        """
        from app.models.stat_model import StatModel
        stats = StatModel()
        try:
            ability  = stats.get_all(category="ability")
            combat   = stats.get_all(category="combat")
            saves    = stats.get_all(category="save")
            return self._ok({
                "ability": ability,
                "combat":  combat,
                "saves":   saves,
            })
        except Exception as e:
            return self._err(f"Failed to load stats: {e}")

    def get_character(self, character_id: int) -> dict:
        try:
            character = self.characters.get_by_id(character_id)
            if not character:
                return self._err(f"Character {character_id} not found.")
            return self._ok(character)
        except Exception as e:
            return self._err(f"Failed to load character: {e}")

    def list_characters(self, campaign_id: int) -> dict:
        try:
            characters = self.characters.get_all_by_campaign(campaign_id)
            return self._ok(characters)
        except Exception as e:
            return self._err(f"Failed to list characters: {e}")

    def update_character(
        self, character_id: int, name: str = None, notes: str = None
    ) -> dict:
        try:
            self.characters.update(character_id, name=name, notes=notes)
            character = self.characters.get_by_id(character_id)
            return self._ok(character, "Character updated.")
        except Exception as e:
            return self._err(f"Failed to update character: {e}")

    def delete_character(self, character_id: int) -> dict:
        try:
            character = self.characters.get_by_id(character_id)
            if not character:
                return self._err(f"Character {character_id} not found.")
            self.characters.delete(character_id)
            return self._ok(message=f"Character '{character['name']}' deleted.")
        except Exception as e:
            return self._err(f"Failed to delete character: {e}")

    # ------------------------------------------------------------------
    # LEVELING UP
    # ------------------------------------------------------------------

    def level_up(
        self,
        character_id: int,
        class_name: str,
        hp_gained: int = 0,
        skill_points: int = 0,
        ability_score_increase: str = "",
        feats: list[str] = None,
        class_features: list[str] = None,
        notes: str = "",
        campaign_id: int = None,
    ) -> dict:
        """
        Records a full level-up event for a character.

        - Increments level and records the class_name
        - Creates stub sources for any feats/class features that don't exist yet
        - Assigns all new sources to the character
        - Returns a summary of what was created vs found

        hp_gained, skill_points, ability_score_increase are stored in notes
        for reference — the user applies these manually to their stat block.
        """
        from app.controllers.source_controller import SourceController

        character = self.characters.get_by_id(character_id)
        if not character:
            return self._err(f"Character {character_id} not found.")
        if not class_name.strip():
            return self._err("Class name cannot be empty.")

        try:
            current_level = self.characters.get_current_level(character_id)
            new_level     = current_level + 1

            # Build a summary note
            note_parts = []
            if hp_gained:
                note_parts.append(f"HP gained: {hp_gained}")
            if skill_points:
                note_parts.append(f"Skill points: {skill_points}")
            if ability_score_increase:
                note_parts.append(f"Ability score increase: {ability_score_increase}")
            if notes:
                note_parts.append(notes)
            full_notes = " | ".join(note_parts)

            self.characters.add_level(
                character_id, new_level, class_name.strip(), full_notes
            )

            sc             = SourceController()
            assigned       = []
            created        = []
            skipped        = []
            feat_cat_id    = self._get_category_id("Feat")
            feature_cat_id = self._get_category_id("Class Feature")

            # Pre-fetch already-assigned source IDs once — avoids a DB call
            # per loop iteration and sidesteps any column-name ambiguity.
            existing_result  = sc.list_character_sources(character_id)
            already_assigned = set()
            if existing_result["success"]:
                already_assigned = {s["source_id"] for s in existing_result["data"]}

            def _process(name: str, cat_id: int):
                name = name.strip()
                if not name:
                    return
                result = sc.get_or_create_source(name, cat_id, campaign_id)
                if not result["success"]:
                    skipped.append(name)
                    return
                sid = result["data"]["source_id"]
                if result["data"]["created"]:
                    created.append(name)
                if sid not in already_assigned:
                    sc.assign_source_to_character(character_id, sid)
                    assigned.append(name)
                    already_assigned.add(sid)

            for feat_name in (feats or []):
                _process(feat_name, feat_cat_id)

            for feature_name in (class_features or []):
                _process(feature_name, feature_cat_id)

            summary = (
                f"{character['name']} is now level {new_level} ({class_name})."
            )
            if created:
                summary += f" New sources created: {', '.join(created)}."
            if skipped:
                summary += f" Could not process: {', '.join(skipped)}."

            return self._ok(
                data={
                    "new_level": new_level,
                    "created":   created,
                    "assigned":  assigned,
                    "skipped":   skipped,
                },
                message=summary,
            )
        except Exception as e:
            return self._err(f"Failed to record level-up: {e}")

    def _get_category_id(self, name: str) -> int | None:
        """Helper: looks up a source_category id by name."""
        from app.models.source_model import SourceModel
        cats = SourceModel().get_all_categories()
        for c in cats:
            if c["name"] == name:
                return c["id"]
        return None

    def get_level_history(self, character_id: int) -> dict:
        try:
            history = self.characters.get_level_history(character_id)
            return self._ok(history)
        except Exception as e:
            return self._err(f"Failed to load level history: {e}")
