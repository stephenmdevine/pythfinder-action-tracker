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
        notes: str = "",
    ) -> dict:
        """
        Records a level-up event for a character.
        The new level is automatically the character's current highest level + 1.
        The caller (View) is responsible for then opening the source-assignment
        form so the user can add feats, class features, and spells gained.
        That assignment is handled by SourceController.assign_source_to_character().
        """
        character = self.characters.get_by_id(character_id)
        if not character:
            return self._err(f"Character {character_id} not found.")
        if not class_name.strip():
            return self._err("Class name cannot be empty.")

        try:
            current_level = self.characters.get_current_level(character_id)
            new_level     = current_level + 1
            level_id      = self.characters.add_level(
                character_id, new_level, class_name.strip(), notes.strip()
            )
            return self._ok(
                data={"level_id": level_id, "new_level": new_level},
                message=(
                    f"{character['name']} is now level {new_level} "
                    f"({class_name}). Add new feats and class features."
                ),
            )
        except Exception as e:
            return self._err(f"Failed to record level-up: {e}")

    def get_level_history(self, character_id: int) -> dict:
        try:
            history = self.characters.get_level_history(character_id)
            return self._ok(history)
        except Exception as e:
            return self._err(f"Failed to load level history: {e}")
