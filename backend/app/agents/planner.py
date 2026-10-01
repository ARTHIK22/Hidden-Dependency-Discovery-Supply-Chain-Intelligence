import re

from app.agents.schemas import InvestigationPlan


_DEPTHS = {"standard": 1, "deep": 2, "maximum": 3}
_TARGET_PATTERNS = (
    re.compile(
        r"\b([A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*)*)[’']s\b"
    ),
    re.compile(
        r"\b(?:behind|of|for|at)\s+"
        r"([A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*)*)"
    ),
)
_FOCUS_TERMS = (
    "rare-earth",
    "rare earth",
    "semiconductor",
    "lithium",
    "battery",
    "cobalt",
    "graphite",
    "solar",
    "electric vehicle",
    "supply chain",
)
_STOP_WORDS = {
    "a", "an", "and", "behind", "chain", "dependencies", "dependency",
    "discover", "find", "hidden", "identify", "in", "investigate", "map",
    "of", "our", "supply", "the", "upstream", "with",
}
_TARGET_PREFIXES = {"find", "identify", "investigate", "map", "discover"}


def _normalize_goal(goal: str) -> str:
    normalized = re.sub(r"\s+", " ", goal).strip()
    normalized = re.sub(r"^find\b", "Discover", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"^investigate\b", "Investigate", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"^identify\b", "Identify", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"^map\b", "Map", normalized, flags=re.IGNORECASE)
    if normalized and normalized[-1] not in ".!?":
        normalized += "."
    return normalized


def _extract_target(goal: str) -> str | None:
    for pattern in _TARGET_PATTERNS:
        match = pattern.search(goal)
        if match:
            target = re.sub(r"\s+", " ", match.group(1)).strip(" ,.;:")
            words = target.split()
            while words and words[0].lower() in _TARGET_PREFIXES:
                words.pop(0)
            target = " ".join(words)
            if target:
                return target
    return None


def _focus(goal: str, target: str | None) -> str:
    lowered = goal.lower()
    for term in _FOCUS_TERMS:
        if term in lowered:
            return term

    remaining = goal
    if target:
        remaining = re.sub(re.escape(target), " ", remaining, flags=re.IGNORECASE)
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]*", remaining)
    focus_words = [word.lower() for word in words if word.lower() not in _STOP_WORDS]
    return " ".join(focus_words[:4]) or "supply-chain"


class PlannerAgent:
    """Build a deterministic plan locally without implying LLM execution."""

    def plan(
        self,
        goal: str,
        depth: str = "deep",
        scope: dict[str, bool] | None = None,
    ) -> InvestigationPlan:
        requested_depth = _DEPTHS.get(depth)
        if requested_depth is None:
            raise ValueError(f"Unsupported investigation depth: {depth}")

        options = scope or {}
        target = _extract_target(goal)
        focus = _focus(goal, target)
        target_phrase = f" for {target}" if target else ""
        normalized_goal = _normalize_goal(goal)
        objective = f"Map {focus} supply-chain dependencies{target_phrase}."
        questions = [
            f"Which entities are directly connected to the requested {focus} supply chain{target_phrase}?",
        ]
        steps = [
            f"Identify direct suppliers and dependencies relevant to {focus}{target_phrase}.",
        ]
        entities = ["company", "supplier"]
        relationships = ["SUPPLIES", "DEPENDS_ON"]

        if requested_depth >= 2:
            steps.extend(
                [
                    "Trace upstream suppliers and manufacturers beyond the direct tier.",
                    "Identify relevant materials, components, and processing facilities.",
                ]
            )
            questions.extend(
                [
                    f"Which manufacturers and upstream suppliers support {focus}{target_phrase}?",
                    f"Which materials, components, or facilities are relevant to {focus}{target_phrase}?",
                ]
            )
            entities.extend(["manufacturer", "facility"])
            relationships.extend(["MANUFACTURES", "PROCESSES"])

        if requested_depth >= 3:
            steps.extend(
                [
                    "Expand through deeper tiers where the stated scope supports it.",
                    "Identify geographic dependencies and concentration points.",
                ]
            )
            questions.append(
                f"Which deeper-tier or geographic dependencies may affect {focus}{target_phrase}?"
            )
            entities.append("region")
            relationships.append("LOCATED_IN")

        if options.get("materials", True):
            entities.append("material")
            relationships.append("USES_MATERIAL")
        if options.get("geography", True):
            entities.append("region")
            if "LOCATED_IN" not in relationships:
                relationships.append("LOCATED_IN")
        if options.get("manufacturers", True) and requested_depth == 1:
            entities.append("manufacturer")
            relationships.append("MANUFACTURES")

        steps.append("Prepare planned relationships for evidence-backed verification.")
        requirements = [
            "Every discovered relationship must have supporting evidence.",
            "Relationships must include confidence information.",
            "Unverified relationships must not be represented as verified facts.",
        ]
        clarification = None
        if target is None:
            clarification = "Specify the company, organization, or supply chain to investigate."

        return InvestigationPlan.model_validate(
            {
                "target": target,
                "normalized_goal": normalized_goal,
                "objective": objective,
                "depth": requested_depth,
                "steps": steps,
                "research_questions": questions,
                "entity_types": list(dict.fromkeys(entities)),
                "relationship_types": list(dict.fromkeys(relationships)),
                "verification_requirements": requirements,
                "planner_mode": "local_demo",
                "target_clarification": clarification,
            }
        )