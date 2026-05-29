from app.controllers.base_controller import BaseController
from app.models.character_model import CharacterModel
from app.models.stat_model import StatModel
from app.models.effect_model import BonusTypeModel
from app.models.source_model import SourceModel

# PF1e light load limits by Strength score (lbs)
# Index = Strength score. Scores above 29 follow a x4 pattern per +10 STR.
_LIGHT_LOAD_BY_STR = {
    1: 3,   2: 6,   3: 10,  4: 13,  5: 16,  6: 20,  7: 23,  8: 26,
    9: 30,  10: 33, 11: 38, 12: 43, 13: 50, 14: 58, 15: 66, 16: 76,
    17: 86, 18: 100,19: 116,20: 133,21: 153,22: 173,23: 200,24: 233,
    25: 266,26: 306,27: 346,28: 400,29: 466,
}


def _light_load_limit(strength_score: int) -> float:
    """
    Returns the light load limit in lbs for a given Strength score.
    Handles scores above 29 using PF1e's x4-per-10 progression.
    """
    if strength_score <= 0:
        return 0.0
    if strength_score <= 29:
        return float(_LIGHT_LOAD_BY_STR.get(strength_score, 0))
    # Each +10 STR above 29 multiplies the limit by 4
    steps  = (strength_score - 20) // 10
    base   = _LIGHT_LOAD_BY_STR[29]
    return float(base * (4 ** steps))


class CharacterSheetController(BaseController):
    """
    Assembles the full resolved view of a character:
        - Base stat values from character_stats
        - Active modifiers resolved through the stacking engine
        - Final computed values (base + net modifier)
        - Active sources summary
        - Encumbrance

    This controller is read-heavy — it gathers and shapes data for display.
    Writes (setting base values, activating sources) are small and targeted.
    """

    def __init__(self):
        self.characters  = CharacterModel()
        self.stats       = StatModel()
        self.bonus_types = BonusTypeModel()
        self.sources     = SourceModel()

    # ------------------------------------------------------------------
    # FULL CHARACTER SHEET
    # ------------------------------------------------------------------

    def get_character_sheet(self, character_id: int) -> dict:
        """
        Returns a fully resolved character sheet dict:
        {
            "character":   { ...character row... },
            "level":       int,
            "stats": [
                {
                    "stat_id":      int,
                    "name":         str,
                    "abbreviation": str,
                    "category":     str,
                    "base_value":   int,
                    "net_modifier": int,
                    "final_value":  int,
                    "breakdown":    [ ...contributing effect rows... ],
                    "suppressed":   [ ...suppressed effect rows... ],
                },
                ...
            ],
            "active_sources": [ ...character_source rows... ],
            "encumbrance": {
                "total_weight_lbs": float,
                "light_load_limit": float,
                "label":            str,   # 'Light', 'Medium', 'Heavy', 'Over Limit'
            }
        }
        """
        character = self.characters.get_by_id(character_id)
        if not character:
            return self._err(f"Character {character_id} not found.")

        try:
            level         = self.characters.get_current_level(character_id)
            base_values   = self.stats.get_all_base_values(character_id)
            active_sources = self.sources.get_character_sources(
                character_id, active_only=True
            )
            encumbrance = self._resolve_encumbrance(character_id, base_values)

            stat_rows = []
            for row in base_values:
                resolution = self.bonus_types.resolve_modifiers_for_stat(
                    character_id, row["stat_id"]
                )
                final_value = self.stats.get_computed_value(
                    character_id,
                    row["stat_id"],
                    resolution["net_modifier"],
                )
                stat_rows.append({
                    "stat_id":      row["stat_id"],
                    "name":         row["name"],
                    "abbreviation": row["abbreviation"],
                    "category":     row["category"],
                    "base_value":   row["base_value"],
                    "net_modifier": resolution["net_modifier"],
                    "final_value":  final_value,
                    "breakdown":    resolution["effects"],
                    "suppressed":   resolution["suppressed"],
                })

            return self._ok({
                "character":      character,
                "level":          level,
                "stats":          stat_rows,
                "active_sources": active_sources,
                "encumbrance":    encumbrance,
            })
        except Exception as e:
            return self._err(f"Failed to build character sheet: {e}")

    def get_single_stat(self, character_id: int, stat_id: int) -> dict:
        """
        Returns the resolved value for a single stat.
        Used to refresh one row in the UI after a source is toggled.
        """
        try:
            base_value  = self.stats.get_base_value(character_id, stat_id)
            resolution  = self.bonus_types.resolve_modifiers_for_stat(
                character_id, stat_id
            )
            final_value = base_value + resolution["net_modifier"]
            return self._ok({
                "base_value":   base_value,
                "net_modifier": resolution["net_modifier"],
                "final_value":  final_value,
                "breakdown":    resolution["effects"],
                "suppressed":   resolution["suppressed"],
            })
        except Exception as e:
            return self._err(f"Failed to resolve stat: {e}")

    # ------------------------------------------------------------------
    # SETTING BASE STAT VALUES
    # ------------------------------------------------------------------

    def set_base_stat(
        self, character_id: int, stat_id: int, base_value: int
    ) -> dict:
        """
        Sets a character's base value for a stat.
        Called from the character editor when the user inputs ability scores,
        base attack bonus, saving throw bases, etc.
        """
        try:
            self.stats.set_base_value(character_id, stat_id, base_value)
            return self.get_single_stat(character_id, stat_id)
        except Exception as e:
            return self._err(f"Failed to set stat: {e}")

    def set_base_stats_bulk(
        self, character_id: int, stat_values: dict[int, int]
    ) -> dict:
        """
        Sets multiple base stat values at once.
        stat_values: {stat_id: base_value, ...}
        Used when first creating a character and entering the full stat block.
        """
        errors = []
        try:
            for stat_id, value in stat_values.items():
                try:
                    self.stats.set_base_value(character_id, stat_id, value)
                except Exception as e:
                    errors.append(f"Stat {stat_id}: {e}")

            if errors:
                return self._err(
                    f"Some stats failed to save: {'; '.join(errors)}"
                )
            return self._ok(message="Base stats saved.")
        except Exception as e:
            return self._err(f"Failed to save stats: {e}")

    # ------------------------------------------------------------------
    # ENCUMBRANCE (internal helper)
    # ------------------------------------------------------------------

    def _resolve_encumbrance(
        self, character_id: int, base_values: list[dict]
    ) -> dict:
        """
        Resolves encumbrance for the character sheet.
        Looks up the Strength score from base_values, computes the
        light load limit, then fetches total carried weight.

        Importing InventoryModel here (not at module level) avoids a
        circular dependency since InventoryController also uses this controller.
        """
        from app.models.inventory_model import InventoryModel
        inventory = InventoryModel()

        str_score = next(
            (r["base_value"] for r in base_values if r["abbreviation"] == "STR"),
            10  # default to 10 if not set
        )
        # Also add any active STR modifiers
        str_stat = self.stats.get_by_name("Strength")
        str_bonus = 0
        if str_stat:
            resolution = self.bonus_types.resolve_modifiers_for_stat(
                character_id, str_stat["id"]
            )
            str_bonus = resolution["net_modifier"]

        effective_str   = str_score + str_bonus
        light_limit     = _light_load_limit(effective_str)
        total_weight    = inventory.get_total_weight(character_id)
        label           = inventory.get_encumbrance_label(total_weight, light_limit)

        return {
            "total_weight_lbs": total_weight,
            "light_load_limit": light_limit,
            "label":            label,
        }
