import re
from collections.abc import Iterable

from app.agents.schemas import InvestigationPlan
from app.research.models import ExtractedEntity, ExtractedRelationship, ResearchQuery, ResearchResult


_STOP_WORDS = {
    "a", "about", "and", "are", "behind", "by", "chain", "companies", "company",
    "connected", "dependency", "dependencies", "direct", "discover", "for", "from",
    "identify", "in", "investigate", "map", "of", "on", "or", "relevant", "supply",
    "the", "to", "which", "with", "their", "this", "that", "these", "those",
}
_ADMIN_STEP = re.compile(r"\bprepare\b.*\bverification\b", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9&.'-]*")
_NAMED_PHRASE = re.compile(
    r"\b[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*){0,4}\b"
)
_RELATION_PATTERNS: dict[str, tuple[str, ...]] = {
    "SUPPLIES": (r"supplies", r"supplied", r"provides", r"provided", r"delivers", r"delivered"),
    "MANUFACTURES": (r"manufactures", r"manufactured", r"produces", r"produced"),
    "PROCESSES": (r"processes", r"processed", r"refines", r"refined"),
    "DISTRIBUTES": (r"distributes", r"distributed", r"ships", r"shipped"),
    "DEPENDS_ON": (r"depends\s+on", r"relies\s+on", r"is\s+dependent\s+on"),
    "OWNS": (r"owns", r"owned\s+by"),
    "OPERATES": (r"operates", r"operated\s+by", r"runs"),
    "LOCATED_IN": (r"located\s+in", r"based\s+in", r"operates\s+in"),
    "USES_MATERIAL": (r"uses", r"utilizes", r"uses\s+material"),
    "CERTIFIED_BY": (r"certified\s+by", r"certification\s+by"),
}


def _words(text: str) -> list[str]:
    return [
        token
        for token in _WORD.findall(text)
        if token.casefold().strip(".'-") not in _STOP_WORDS
    ]


def _unique_casefold(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = re.sub(r"\s+", " ", value).strip(" ,.;:")
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


class ResearchAgent:
    """Build bounded, plan-derived queries and extract only source-backed mentions."""

    def generate_queries(self, plan: InvestigationPlan) -> list[ResearchQuery]:
        depth_limit = max(1, plan.depth * 2 - 1)
        steps = [step for step in plan.steps if not _ADMIN_STEP.search(step)][:depth_limit]
        if not steps:
            return []

        target = plan.target or ""
        topic_tokens = _words(plan.objective)
        if target:
            target_words = {word.casefold() for word in _WORD.findall(target)}
            topic_tokens = [word for word in topic_tokens if word.casefold() not in target_words]
        topic = " ".join(topic_tokens[:5])
        queries: list[ResearchQuery] = []
        for index, step in enumerate(steps):
            question = plan.research_questions[min(index, len(plan.research_questions) - 1)]
            step_terms = _words(step)
            question_terms = _words(question)
            terms = _unique_casefold(
                [
                    *([target] if target else []),
                    *([topic] if topic else []),
                    " ".join(step_terms[:5]),
                    " ".join(question_terms[:4]),
                    " ".join(plan.entity_types[:3]),
                    " ".join(kind.lower().replace("_", " ") for kind in plan.relationship_types[:3]),
                ]
            )
            depth_level = 1 if index == 0 else min(plan.depth, 2 + (index - 1) // 2)
            queries.append(
                ResearchQuery(
                    query=" ".join(terms)[:500],
                    purpose=f"{step} Research question: {question}",
                    entity_focus=plan.entity_types,
                    relationship_focus=plan.relationship_types,
                    depth=depth_level,
                    step_id=f"step-{index + 1}",
                )
            )
        return queries

    def extract_entities(
        self,
        result: ResearchResult,
        plan: InvestigationPlan,
        evidence_id: str,
    ) -> list[ExtractedEntity]:
        """Find named phrases in received source text; never infer names from a query."""
        text = f"{result.source_title}. {result.content}"
        names = _unique_casefold(_NAMED_PHRASE.findall(text))
        if plan.target and plan.target.casefold() in text.casefold():
            names = _unique_casefold([plan.target, *names])

        candidates: list[ExtractedEntity] = []
        for name in names:
            if len(name) < 2:
                continue
            kind = self._infer_entity_type(name, text, plan)
            context = self._context_for(name, text)
            candidates.append(
                ExtractedEntity(
                    name=name,
                    entity_type=kind,
                    description=context[:500] or None,
                    source_evidence_ids=[evidence_id],
                    confidence=0.55 if kind != "OTHER" else 0.4,
                )
            )
        return candidates

    def extract_relationships(
        self,
        result: ResearchResult,
        plan: InvestigationPlan,
    ) -> list[ExtractedRelationship]:
        """Extract a narrow set of explicit relation phrases from the source snippet."""
        allowed = {kind.upper() for kind in plan.relationship_types}
        extracted: list[ExtractedRelationship] = []
        for sentence in re.split(r"(?<=[.!?])\s+|[\r\n]+", result.content):
            sentence = sentence.strip()
            if not sentence:
                continue
            for relation_type, verbs in _RELATION_PATTERNS.items():
                if relation_type not in allowed:
                    continue
                verb_pattern = "|".join(verbs)
                match = re.search(
                    rf"(?P<left>[^,;:!?]{{1,160}}?)\s+(?P<verb>{verb_pattern})\s+(?P<right>[^,;:!?]{{1,160}}?)(?:[.!?]|$)",
                    sentence,
                    flags=re.IGNORECASE,
                )
                if match is None:
                    continue
                left_name = self._last_named_phrase(match.group("left"))
                right_name = self._first_named_phrase(match.group("right"))
                if not left_name or not right_name or left_name.casefold() == right_name.casefold():
                    continue
                if left_name.casefold() not in result.content.casefold() or right_name.casefold() not in result.content.casefold():
                    continue
                source_name, target_name = self._relationship_direction(
                    relation_type, match.group("verb"), left_name, right_name
                )
                extracted.append(
                    ExtractedRelationship(
                        source_entity=source_name,
                        target_entity=target_name,
                        relationship_type=relation_type,
                        evidence_text=sentence[:4000],
                        confidence=0.55,
                    )
                )
        unique: dict[tuple[str, str, str], ExtractedRelationship] = {}
        for relationship in extracted:
            key = (
                relationship.source_entity.casefold(),
                relationship.target_entity.casefold(),
                relationship.relationship_type,
            )
            unique.setdefault(key, relationship)
        return list(unique.values())

    @staticmethod
    def _infer_entity_type(name: str, text: str, plan: InvestigationPlan) -> str:
        if plan.target and name.casefold() == plan.target.casefold():
            return "COMPANY"
        before = text[max(0, text.casefold().find(name.casefold()) - 60):]
        before = before.casefold()
        after_index = text.casefold().find(name.casefold()) + len(name)
        after = text[after_index:after_index + 60].casefold()
        context = before + " " + after
        for marker, kind in (
            ("supplier", "SUPPLIER"),
            ("manufacturer", "MANUFACTURER"),
            ("facility", "FACILITY"),
            ("region", "REGION"),
            ("material", "MATERIAL"),
            ("logistics", "LOGISTICS_PROVIDER"),
            ("product", "PRODUCT"),
            ("certification", "CERTIFICATION"),
        ):
            if marker in context and kind.casefold() in {value.casefold() for value in plan.entity_types}:
                return kind
        if re.search(r"\b(?:inc\.?|corp\.?|corporation|ltd\.?|limited|llc|plc)\b", name, re.IGNORECASE):
            return "COMPANY"
        return "OTHER"

    @staticmethod
    def _context_for(name: str, text: str) -> str:
        start = text.casefold().find(name.casefold())
        return text[max(0, start - 90): min(len(text), start + len(name) + 160)] if start >= 0 else ""

    @staticmethod
    def _last_named_phrase(value: str) -> str | None:
        phrases = _NAMED_PHRASE.findall(value)
        return phrases[-1].strip(" ,.;:") if phrases else None

    @staticmethod
    def _first_named_phrase(value: str) -> str | None:
        phrases = _NAMED_PHRASE.findall(value)
        return phrases[0].strip(" ,.;:") if phrases else None

    @staticmethod
    def _relationship_direction(
        relationship_type: str,
        verb: str,
        left: str,
        right: str,
    ) -> tuple[str, str]:
        if relationship_type in {"SUPPLIES", "MANUFACTURES", "PROCESSES", "DISTRIBUTES", "OWNS", "OPERATES"} and "by" in verb:
            return right, left
        if relationship_type == "CERTIFIED_BY":
            return left, right
        if relationship_type == "LOCATED_IN":
            return left, right
        if relationship_type == "USES_MATERIAL":
            return left, right
        return left, right
