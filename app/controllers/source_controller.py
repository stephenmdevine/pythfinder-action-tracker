from app.controllers.base_controller import BaseController
from app.models.source_model import SourceModel
from app.models.effect_model import EffectModel, BonusTypeModel
from app.models.stat_model import StatModel


class SourceController(BaseController):
    """
    Manages the source and effect library, and the assignment of
    sources to characters.

    A source is the thing (feat, spell, condition, class feature, etc.)
    An effect is what it mechanically does (modifier to a stat).
    A character_source is the link between a character and a source.

    This controller is used both in the 'library management' screens
    (creating and editing sources) and in the 'character management'
    screens (assigning sources to a character, toggling activation).
    """

    def __init__(self):
        self.sources    = SourceModel()
        self.effects    = EffectModel()
        self.bonus_types = BonusTypeModel()
        self.stats      = StatModel()

    # ------------------------------------------------------------------
    # SOURCE LIBRARY
    # ------------------------------------------------------------------

    def create_source(
        self,
        name: str,
        source_category_id: int,
        duration_type: str,
        duration_value: int = None,
        action_type_id: int = None,
        description: str = "",
    ) -> dict:
        if not name.strip():
            return self._err("Source name cannot be empty.")
        try:
            source_id = self.sources.create(
                name=name.strip(),
                source_category_id=source_category_id,
                duration_type=duration_type,
                duration_value=duration_value,
                action_type_id=action_type_id,
                description=description.strip(),
            )
            source = self.sources.get_by_id(source_id)
            return self._ok(source, f"Source '{name}' created.")
        except ValueError as e:
            return self._err(str(e))
        except Exception as e:
            return self._err(f"Failed to create source: {e}")

    def get_source(self, source_id: int) -> dict:
        try:
            source = self.sources.get_by_id(source_id)
            if not source:
                return self._err(f"Source {source_id} not found.")
            # Include effects in the detail view
            source["effects"] = self.effects.get_by_source(source_id)
            return self._ok(source)
        except Exception as e:
            return self._err(f"Failed to load source: {e}")

    def list_sources(self, source_category_id: int = None) -> dict:
        try:
            sources = self.sources.get_all(source_category_id)
            return self._ok(sources)
        except Exception as e:
            return self._err(f"Failed to list sources: {e}")

    def search_sources(self, query: str) -> dict:
        if not query.strip():
            return self._err("Search query cannot be empty.")
        try:
            results = self.sources.search_by_name(query.strip())
            return self._ok(results)
        except Exception as e:
            return self._err(f"Search failed: {e}")

    def update_source(self, source_id: int, **kwargs) -> dict:
        try:
            self.sources.update(source_id, **kwargs)
            source = self.sources.get_by_id(source_id)
            source["effects"] = self.effects.get_by_source(source_id)
            return self._ok(source, "Source updated.")
        except Exception as e:
            return self._err(f"Failed to update source: {e}")

    def delete_source(self, source_id: int) -> dict:
        try:
            source = self.sources.get_by_id(source_id)
            if not source:
                return self._err(f"Source {source_id} not found.")
            self.sources.delete(source_id)
            return self._ok(message=f"Source '{source['name']}' deleted.")
        except Exception as e:
            return self._err(f"Failed to delete source: {e}")

    # ------------------------------------------------------------------
    # EFFECTS (on a source)
    # ------------------------------------------------------------------

    def add_effect(
        self,
        source_id: int,
        stat_id: int,
        bonus_type_id: int,
        modifier: int = None,
        condition_note: str = "",
        pool_allocation_id: int = None,
        scaling_stat_id: int = None,
        base_value: int = None,
        multiplier: float = 1.0,
        divisor: int = 1,
    ) -> dict:
        """
        Adds an effect to a source. Exactly one effect type must be specified:
          Fixed:             pass modifier (int)
          Formula-scaled:    pass scaling_stat_id; optionally base_value,
                             multiplier, divisor
          Investment-scaled: pass pool_allocation_id
        """
        # Validate: exactly one effect type
        type_count = sum([
            modifier is not None,
            scaling_stat_id is not None,
            pool_allocation_id is not None,
        ])
        if type_count == 0:
            return self._err(
                "An effect must have a fixed modifier, a scaling stat, "
                "or a pool allocation link."
            )
        if type_count > 1:
            return self._err(
                "An effect can only have one type: fixed, formula-scaled, "
                "or investment-scaled."
            )
        try:
            effect_id = self.effects.create(
                source_id       = source_id,
                stat_id         = stat_id,
                bonus_type_id   = bonus_type_id,
                modifier        = modifier,
                condition_note  = condition_note.strip(),
                base_value      = base_value,
                scaling_stat_id = scaling_stat_id,
                multiplier      = multiplier,
                divisor         = divisor,
            )
            if pool_allocation_id is not None:
                self.effects.set_pool_allocation(effect_id, pool_allocation_id)
            elif scaling_stat_id is not None:
                self.effects.set_formula_scaling(
                    effect_id, scaling_stat_id,
                    base_value or 0, multiplier, divisor
                )

            effect = self.effects.get_by_id(effect_id)
            return self._ok(effect, "Effect added.")
        except Exception as e:
            return self._err(f"Failed to add effect: {e}")

    def update_effect(self, effect_id: int, **kwargs) -> dict:
        try:
            self.effects.update(effect_id, **kwargs)
            effect = self.effects.get_by_id(effect_id)
            return self._ok(effect, "Effect updated.")
        except Exception as e:
            return self._err(f"Failed to update effect: {e}")

    def delete_effect(self, effect_id: int) -> dict:
        try:
            self.effects.delete(effect_id)
            return self._ok(message="Effect removed.")
        except Exception as e:
            return self._err(f"Failed to delete effect: {e}")

    def list_effects_for_source(self, source_id: int) -> dict:
        try:
            effects = self.effects.get_by_source(source_id)
            return self._ok(effects)
        except Exception as e:
            return self._err(f"Failed to load effects: {e}")

    # ------------------------------------------------------------------
    # REFERENCE DATA (for populating dropdowns in the UI)
    # ------------------------------------------------------------------

    def list_categories(self) -> dict:
        try:
            return self._ok(self.sources.get_all_categories())
        except Exception as e:
            return self._err(f"Failed to load categories: {e}")

    def list_bonus_types(self) -> dict:
        try:
            return self._ok(self.bonus_types.get_all())
        except Exception as e:
            return self._err(f"Failed to load bonus types: {e}")

    def list_stats(self, category: str = None) -> dict:
        try:
            return self._ok(self.stats.get_all(category))
        except Exception as e:
            return self._err(f"Failed to load stats: {e}")

    # ------------------------------------------------------------------
    # ASSIGNING SOURCES TO CHARACTERS
    # ------------------------------------------------------------------

    def assign_source_to_character(
        self, character_id: int, source_id: int
    ) -> dict:
        """
        Gives a character access to a source (learns a feat, gains a condition, etc.)
        For permanent sources, also sets them active immediately.
        For toggle/rounds/timed sources, leaves them inactive until the user activates.
        """
        try:
            source = self.sources.get_by_id(source_id)
            if not source:
                return self._err(f"Source {source_id} not found.")

            character_source_id = self.sources.assign_to_character(
                character_id, source_id
            )

            # Permanent sources are always on — activate immediately
            if source["duration_type"] == "permanent":
                self.sources.set_active(character_source_id, True)

            result = {
                "character_source_id": character_source_id,
                "source":              source,
            }
            return self._ok(result, f"'{source['name']}' assigned to character.")
        except Exception as e:
            return self._err(f"Failed to assign source: {e}")

    def remove_source_from_character(self, character_source_id: int) -> dict:
        try:
            self.sources.remove_from_character(character_source_id)
            return self._ok(message="Source removed from character.")
        except Exception as e:
            return self._err(f"Failed to remove source: {e}")

    def list_character_sources(
        self, character_id: int, active_only: bool = False
    ) -> dict:
        try:
            sources = self.sources.get_character_sources(character_id, active_only)
            return self._ok(sources)
        except Exception as e:
            return self._err(f"Failed to load character sources: {e}")

    def activate_source(
        self,
        character_source_id: int,
        duration_type: str,
        duration_value: int = None,
    ) -> dict:
        """
        Activates a source on a character.
        For 'rounds' sources, duration_value must be provided.
        For 'until_next_turn', duration_value is set to 1 automatically.
        """
        try:
            rounds = None
            if duration_type == "rounds":
                if not duration_value:
                    return self._err(
                        "Rounds duration required for this source. "
                        "How many rounds does it last?"
                    )
                rounds = duration_value
            elif duration_type == "until_next_turn":
                rounds = 1

            self.sources.set_active(character_source_id, True, rounds)
            return self._ok(message="Source activated.")
        except Exception as e:
            return self._err(f"Failed to activate source: {e}")

    def deactivate_source(self, character_source_id: int) -> dict:
        try:
            self.sources.set_active(character_source_id, False)
            return self._ok(message="Source deactivated.")
        except Exception as e:
            return self._err(f"Failed to deactivate source: {e}")
