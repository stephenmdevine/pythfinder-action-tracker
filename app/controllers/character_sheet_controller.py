"""
character_sheet_controller.py

Controller for the Character Sheet panel.
Handles fetching base stats, resolving stacked modifiers, and character metadata.
Returns {"success": bool, "data": any, "message": str} dicts throughout.
"""

from app.models.character_model import CharacterModel
from app.models.stat_model import StatModel
from app.models.effect_model import BonusTypeModel
from app.models.point_pool_model import PointPoolModel
from app.models.source_model import SourceModel
from app.controllers.base_controller import BaseController


# PF1e skill → governing ability abbreviation
# Used to pull the live ability modifier for each skill row.
_SKILL_ABILITY: dict[str, str] = {
    "Acrobatics":          "DEX",
    "Appraise":            "INT",
    "Bluff":               "CHA",
    "Climb":               "STR",
    "Craft":               "INT",
    "Diplomacy":           "CHA",
    "Disable Device":      "DEX",
    "Disguise":            "CHA",
    "Escape Artist":       "DEX",
    "Fly":                 "DEX",
    "Handle Animal":       "CHA",
    "Heal":                "WIS",
    "Intimidate":          "CHA",
    "Knowledge (Arcana)":          "INT",
    "Knowledge (Dungeoneering)":   "INT",
    "Knowledge (Engineering)":     "INT",
    "Knowledge (Geography)":       "INT",
    "Knowledge (History)":         "INT",
    "Knowledge (Local)":           "INT",
    "Knowledge (Nature)":          "INT",
    "Knowledge (Nobility)":        "INT",
    "Knowledge (Planes)":          "INT",
    "Knowledge (Religion)":        "INT",
    "Linguistics":         "INT",
    "Perception":          "WIS",
    "Perform":             "CHA",
    "Profession":          "WIS",
    "Ride":                "DEX",
    "Sense Motive":        "WIS",
    "Sleight of Hand":     "DEX",
    "Spellcraft":          "INT",
    "Stealth":             "DEX",
    "Survival":            "WIS",
    "Swim":                "STR",
    "Use Magic Device":    "CHA",
}

_PREFIX_ABILITY: dict[str, str] = {
    "Craft":      "INT",
    "Perform":    "CHA",
    "Profession": "WIS",
    "Knowledge":  "INT",
}

def _governing_ability(skill_name: str) -> str:
    """
    Return the governing ability abbreviation for a skill.
    Handles Craft/Perform/Profession/Knowledge variants by prefix match.
    Falls back to empty string if unknown (custom skills).
    """
    if skill_name in _SKILL_ABILITY:
        return _SKILL_ABILITY[skill_name]
    for prefix, ability in _PREFIX_ABILITY.items():
        if skill_name.startswith(prefix):
            return ability
    return ""


class CharacterSheetController(BaseController):

    def __init__(self):
        self.character_model = CharacterModel()
        self.stat_model      = StatModel()
        self.bonus_type_model = BonusTypeModel()
        self.source_model    = SourceModel()
        self.point_pool_model = PointPoolModel()

    # ------------------------------------------------------------------
    # Character metadata
    # ------------------------------------------------------------------

    def get_character_sheet(self, character_id: int) -> dict:
        """
        Assembles the full stat sheet for the panel in one call.
        Returns:
        {
            "character": { ...character row... },
            "level":     int,
            "stats":     [ ...resolved stat rows, skill category excluded... ],
        }
        Skill data is fetched separately via get_skill_stats() so each
        section can fail and be handled independently.
        """
        try:
            character = self.character_model.get_by_id(character_id)
            if not character:
                return {"success": False, "data": None,
                        "message": f"Character {character_id} not found."}

            level = self.character_model.get_current_level(character_id)

            stats_result = self.get_effective_stat_values(character_id)
            if not stats_result["success"]:
                return stats_result

            # Exclude skill-category rows — those go to the Skills tab
            stats = [
                s for s in stats_result["data"]
                if s.get("stat_category", "").lower() != "skill"
            ]

            return {"success": True, "data": {
                "character": character,
                "level":     level,
                "stats":     stats,
            }, "message": ""}
        except Exception as e:
            return {"success": False, "data": None, "message": str(e)}


    def get_character(self, character_id: int) -> dict:
        """Return full character row plus derived display fields."""
        try:
            character = self.character_model.get_by_id(character_id)
            if not character:
                return {"success": False, "data": None, "message": "Character not found."}
            return {"success": True, "data": character, "message": ""}
        except Exception as e:
            return {"success": False, "data": None, "message": str(e)}

    def get_character_levels(self, character_id: int) -> dict:
        """Return all level rows for a character, ordered ascending."""
        try:
            rows = self.character_model.get_level_history(character_id)
            return {"success": True, "data": rows, "message": ""}
        except Exception as e:
            return {"success": False, "data": [], "message": str(e)}

    # ------------------------------------------------------------------
    # Stats & resolved modifiers
    # ------------------------------------------------------------------

    def get_all_stats(self) -> dict:
        """Return every stat definition row."""
        try:
            rows = self.stat_model.get_all()
            return {"success": True, "data": rows, "message": ""}
        except Exception as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_base_stat_values(self, character_id: int) -> dict:
        """
        Return a dict keyed by stat_id of the character's base stat values
        (the raw numbers stored in character_stats, not yet modified by sources).
        Shape: {stat_id: {"stat_id": int, "stat_name": str, "base_value": int}}
        """
        try:
            rows = self.stat_model.get_all_base_values(character_id)
            data = {r["stat_id"]: r for r in rows}
            return {"success": True, "data": data, "message": ""}
        except Exception as e:
            return {"success": False, "data": {}, "message": str(e)}

    def get_resolved_modifiers(self, character_id: int) -> dict:
        """
        Run the stacking engine for every stat and return a list of resolved
        modifier summaries, one entry per stat that has at least one active effect.

        Each entry:
        {
            "stat_id": int,
            "stat_name": str,
            "net_modifier": int,       # after stacking rules applied
            "contributing": [...],     # effects that count
            "suppressed": [...],       # typed bonuses overridden by a higher same-type
        }
        """
        try:
            stats_result = self.get_all_stats()
            if not stats_result["success"]:
                return {"success": False, "data": [], "message": stats_result["message"]}

            resolved = []
            for stat in stats_result["data"]:
                stat_id = stat["id"]
                result = self.bonus_type_model.resolve_modifiers_for_stat(
                    character_id=character_id,
                    stat_id=stat_id,
                )
                # resolve_modifiers_for_stat returns a dict with at least:
                # {"net_modifier": int, "contributing": [...], "suppressed": [...]}
                if result["net_modifier"] != 0 or result["effects"]:
                    resolved.append({
                        "stat_id": stat_id,
                        "stat_name": stat["name"],
                        "net_modifier": result["net_modifier"],
                        "effects": result.get("effects", []),
                        "suppressed": result.get("suppressed", []),
                    })

            return {"success": True, "data": resolved, "message": ""}
        except Exception as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_effective_stat_values(self, character_id: int) -> dict:
        """
        Merge base values with resolved modifiers to produce the final displayed
        value for each stat.

        Returns a list of dicts:
        {
            "stat_id": int,
            "stat_name": str,
            "base_value": int,
            "net_modifier": int,
            "effective_value": int,
            "contributing": [...],
            "suppressed": [...],
        }
        Sorted by stat category then name (ability scores first, then combat stats, then saves).
        """
        try:
            base_result = self.get_base_stat_values(character_id)
            mod_result = self.get_resolved_modifiers(character_id)
            stats_result = self.get_all_stats()

            if not base_result["success"]:
                return base_result
            if not mod_result["success"]:
                return mod_result
            if not stats_result["success"]:
                return stats_result

            base_map = base_result["data"]           # {stat_id: row}
            mod_map = {r["stat_id"]: r for r in mod_result["data"]}

            rows = []
            for stat in stats_result["data"]:
                sid = stat["id"]
                base_row = base_map.get(sid, {})
                mod_row = mod_map.get(sid, {})

                base_val = base_row.get("base_value", 0)
                net_mod = mod_row.get("net_modifier", 0)

                rows.append({
                    "stat_id": sid,
                    "name": stat["name"],
                    "abbreviation": stat.get("abbreviation", ""),
                    "category": stat.get("category", ""),
                    "stat_category": stat.get("category", ""),
                    "base_value": base_val,
                    "net_modifier": net_mod,
                    "final_value": base_val + net_mod,
                    "breakdown": mod_row.get("effects", []),
                    "suppressed": mod_row.get("suppressed", []),
                })

            # Sort: ability scores first, then combat, then saves, then rest
            category_order = {
                "ability": 0,
                "combat": 1,
                "save": 2,
            }
            rows.sort(key=lambda r: (
                category_order.get(r["stat_category"].lower(), 9),
                r["name"],
            ))

            return {"success": True, "data": rows, "message": ""}
        except Exception as e:
            return {"success": False, "data": [], "message": str(e)}

    # ------------------------------------------------------------------
    # Active sources (for the modifier breakdown tooltip / detail pane)
    # ------------------------------------------------------------------

    def get_active_sources(self, character_id: int) -> dict:
        """
        Return character sources that are currently active (is_active = 1).
        """
        try:
            rows = self.source_model.get_character_sources(character_id)
            active = [r for r in rows if r.get("is_active")]
            return {"success": True, "data": active, "message": ""}
        except Exception as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_all_character_sources(self, character_id: int) -> dict:
        """Return all sources assigned to a character regardless of active state."""
        try:
            rows = self.source_model.get_character_sources(character_id)
            return {"success": True, "data": rows, "message": ""}
        except Exception as e:
            return {"success": False, "data": [], "message": str(e)}

    def activate_source(self, character_source_id: int) -> dict:
        """Set a character source to active."""
        try:
            self.source_model.set_active(character_source_id, True)
            return {"success": True, "data": None, "message": "Source activated."}
        except Exception as e:
            return {"success": False, "data": None, "message": str(e)}

    def deactivate_source(self, character_source_id: int) -> dict:
        """Set a character source to inactive."""
        try:
            self.source_model.set_active(character_source_id, False)
            return {"success": True, "data": None, "message": "Source deactivated."}
        except Exception as e:
            return {"success": False, "data": None, "message": str(e)}

    # ------------------------------------------------------------------
    # Point pools
    # ------------------------------------------------------------------

    def get_point_pools(self, character_id: int) -> dict:
        """Return all point pools for a character with current / max values."""
        try:
            rows = self.point_pool_model.get_for_character(character_id)
            return {"success": True, "data": rows, "message": ""}
        except Exception as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_skill_stats(self, character_id: int) -> dict:
        """
        Return all skill-category stats for a character with:
          - ranks       : base_value from character_stats
          - ability_abbr: governing ability abbreviation (e.g. "DEX")
          - ability_modifier: live resolved value of that ability score's modifier
          - net_modifier: stacking engine result for bonuses applied directly
                          to this skill stat (feats, racial, etc.)
          - breakdown / suppressed: effect lists for the breakdown pane
          - final_value: ranks + ability_modifier + net_modifier

        Skills with no character_stats row yet are included with ranks = 0
        so every core skill always appears on the sheet.
        """
        try:
            # All skill stat definitions
            all_skills = self.stat_model.get_all(category="skill")
            print(f"[DEBUG skills] all_skills count: {len(all_skills)}")
            if all_skills:
                print(f"[DEBUG skills] sample: {all_skills[0]}")

            # Character's recorded base values (ranks)
            base_rows = self.stat_model.get_all_base_values(character_id)
            print(f"[DEBUG skills] base_rows count: {len(base_rows)}")
            ranks_map = {
                r["stat_id"]: r["base_value"]
                for r in base_rows
                if r.get("category", "").lower() == "skill"
            }

            # Resolve all ability scores once so we can look up modifiers cheaply
            ability_stats = self.stat_model.get_all(category="ability")
            ability_finals: dict[str, int] = {}
            for ab in ability_stats:
                resolution = self.bonus_type_model.resolve_modifiers_for_stat(
                    character_id, ab["id"]
                )
                base_val = self.stat_model.get_base_value(character_id, ab["id"])
                final_score = base_val + resolution["net_modifier"]
                # Store modifier (not score) keyed by abbreviation
                ability_finals[ab["abbreviation"]] = (final_score - 10) // 2

            rows = []
            for skill in all_skills:
                sid        = skill["id"]
                name       = skill["name"]
                ranks      = ranks_map.get(sid, 0)
                ab_abbr    = _governing_ability(name)
                ab_mod     = ability_finals.get(ab_abbr, 0)

                # Stacking engine for bonuses applied directly to this skill
                resolution = self.bonus_type_model.resolve_modifiers_for_stat(
                    character_id, sid
                )
                net_mod = resolution["net_modifier"]

                rows.append({
                    "stat_id":          sid,
                    "name":             name,
                    "category":         "skill",
                    "ability_abbr":     ab_abbr,
                    "ability_modifier": ab_mod,
                    "ranks":            ranks,
                    "net_modifier":     net_mod,
                    "final_value":      ranks + ab_mod + net_mod,
                    "breakdown":        resolution.get("effects", []),
                    "suppressed":       resolution.get("suppressed", []),
                })

            return {"success": True, "data": rows, "message": ""}
        except Exception as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_feats_and_abilities(self, character_id: int) -> dict:
        """
        Returns character sources grouped into display categories for the
        Feats & Abilities tab. Groups:
          - Feats           (category_name = 'Feat')
          - Class Features  (category_name = 'Class Feature')
          - Racial Abilities (category_name = 'Racial Ability')
          - Other           (everything else that isn't Condition/Other combat modifier)

        Each item: source_id, character_source_id, name, description,
                   category_name, duration_type, is_active
        """
        _EXCLUDED = {"Condition", "Other"}
        _GROUP_ORDER = ["Feat", "Class Feature", "Racial Ability"]

        try:
            rows = self.source_model.get_character_sources(character_id)

            grouped: dict[str, list[dict]] = {}
            for row in rows:
                cat = row.get("category_name", "Other")
                if cat in _EXCLUDED:
                    continue
                grouped.setdefault(cat, [])
                grouped[cat].append(row)

            # Build ordered output: known groups first, then remainder alphabetically
            ordered = []
            seen = set()
            for cat in _GROUP_ORDER:
                if cat in grouped:
                    ordered.append({
                        "category": cat,
                        "items": sorted(grouped[cat], key=lambda r: r["name"]),
                    })
                    seen.add(cat)
            for cat in sorted(grouped):
                if cat not in seen:
                    ordered.append({
                        "category": cat,
                        "items": sorted(grouped[cat], key=lambda r: r["name"]),
                    })

            return {"success": True, "data": ordered, "message": ""}
        except Exception as e:
            return {"success": False, "data": [], "message": str(e)}

