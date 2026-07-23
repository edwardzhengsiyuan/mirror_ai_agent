"""Validated contracts for the LLM-authored layer of MingShu."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class EvidenceClaim(BaseModel):
    text: str = Field(min_length=1, max_length=260)
    evidence_ids: list[str] = Field(min_length=1)
    confidence: Literal["high", "medium", "low"]
    plain_language_reason: str = Field(min_length=1, max_length=360)

    @field_validator("evidence_ids")
    @classmethod
    def evidence_ids_must_be_unique(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("evidence_ids must be unique")
        return values


class LuckCycleAssessment(BaseModel):
    cycle_id: str = Field(pattern=r"^fact:dayun:\d{2}$")
    name: str = Field(min_length=2, max_length=8)
    start_year: int = Field(ge=1800, le=2300)
    end_year: int = Field(ge=1800, le=2310)
    score: int = Field(ge=0, le=100)
    confidence: Literal["high", "medium", "low"]
    headline: str = Field(min_length=2, max_length=32)
    opportunities: list[EvidenceClaim] = Field(default_factory=list, max_length=4)
    tensions: list[EvidenceClaim] = Field(default_factory=list, max_length=4)
    key_years: list[int] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def years_are_consistent(self) -> "LuckCycleAssessment":
        if self.end_year < self.start_year:
            raise ValueError("end_year must not be earlier than start_year")
        if any(year < self.start_year or year > self.end_year for year in self.key_years):
            raise ValueError("key_years must fall inside the luck-cycle range")
        return self


class WuxingPreferenceAssessment(BaseModel):
    schema_version: Literal["mingshu-wuxing/1.0"]
    priority_basis: Literal["geju", "tiaohou", "balanced"]
    favorable_elements: list[str] = Field(min_length=1, max_length=5)
    unfavorable_elements: list[str] = Field(default_factory=list, max_length=5)
    useful_stems: list[str] = Field(default_factory=list, max_length=10)
    cautious_stems: list[str] = Field(default_factory=list, max_length=10)
    basis_summary: str = Field(min_length=20, max_length=600)
    evidence_ids: list[str] = Field(min_length=1)
    luck_cycles: list[LuckCycleAssessment] = Field(min_length=1, max_length=9)

    @field_validator("favorable_elements", "unfavorable_elements")
    @classmethod
    def validate_element_codes(cls, values: list[str]) -> list[str]:
        allowed = {
            "WUXING:MU",
            "WUXING:HUO",
            "WUXING:TU",
            "WUXING:JIN",
            "WUXING:SHUI",
        }
        if any(value not in allowed for value in values):
            raise ValueError("element values must use WUXING:* codes")
        if len(values) != len(set(values)):
            raise ValueError("element values must be unique")
        return values

    @field_validator("useful_stems", "cautious_stems")
    @classmethod
    def validate_stem_codes(cls, values: list[str]) -> list[str]:
        allowed = {
            "GAN:JIA",
            "GAN:YI",
            "GAN:BING",
            "GAN:DING",
            "GAN:WU",
            "GAN:JI",
            "GAN:GENG",
            "GAN:XIN",
            "GAN:REN",
            "GAN:GUI",
        }
        if any(value not in allowed for value in values):
            raise ValueError("stem values must use GAN:* codes")
        if len(values) != len(set(values)):
            raise ValueError("stem values must be unique")
        return values

    @model_validator(mode="after")
    def lists_do_not_conflict(self) -> "WuxingPreferenceAssessment":
        if set(self.favorable_elements) & set(self.unfavorable_elements):
            raise ValueError("an element cannot be both favorable and unfavorable")
        if set(self.useful_stems) & set(self.cautious_stems):
            raise ValueError("a stem cannot be both useful and cautious")
        cycle_ids = [item.cycle_id for item in self.luck_cycles]
        if len(cycle_ids) != len(set(cycle_ids)):
            raise ValueError("luck cycle ids must be unique")
        return self


class ChapterDraft(BaseModel):
    schema_version: Literal["mingshu-chapter/1.0"]
    spread_slug: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=40)
    deck: str = Field(min_length=10, max_length=140)
    claims: list[EvidenceClaim] = Field(min_length=1, max_length=10)
    knowledge_card_codes: list[str] = Field(default_factory=list, max_length=12)
    reader_takeaways: list[str] = Field(min_length=1, max_length=5)
    uncertainty_note: str | None = Field(default=None, max_length=240)


def _extract_json(text: str) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty JSON content")
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    raw = fenced.group(1).strip() if fenced else text.strip()
    if not raw.startswith("{"):
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError("no JSON object found")
        raw = match.group(0)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("JSON output must be an object")
    return value


def parse_wuxing_assessment(text: str) -> WuxingPreferenceAssessment:
    return WuxingPreferenceAssessment.model_validate(_extract_json(text))


def parse_chapter_draft(text: str) -> ChapterDraft:
    return ChapterDraft.model_validate(_extract_json(text))


def validate_wuxing_assessment(text: str) -> tuple[bool, str]:
    try:
        parse_wuxing_assessment(text)
    except Exception as exc:
        return False, str(exc)
    return True, ""


def validate_chapter_draft(text: str) -> tuple[bool, str]:
    try:
        parse_chapter_draft(text)
    except Exception as exc:
        return False, str(exc)
    return True, ""


def collect_fact_ids(facts: dict) -> set[str]:
    """Collect evidence identifiers exposed by the stable fact layer."""
    result: set[str] = set()

    def walk(value: object) -> None:
        if isinstance(value, dict):
            identifier = value.get("id")
            if isinstance(identifier, str) and identifier:
                result.add(identifier)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(facts)
    return result


def validate_chapter_evidence(chapter: ChapterDraft, facts: dict) -> tuple[bool, str]:
    """Ensure a chapter only cites evidence present in the current chart."""
    available = collect_fact_ids(facts)
    cited = {
        evidence_id
        for claim in chapter.claims
        for evidence_id in claim.evidence_ids
    }
    missing = sorted(cited - available)
    if missing:
        return False, f"chapter cites unknown evidence ids: {', '.join(missing)}"
    return True, ""


def validate_wuxing_evidence(
    assessment: WuxingPreferenceAssessment,
    facts: dict,
    *,
    require_all_cycles: bool = True,
    cycle_limit: int | None = 9,
) -> tuple[bool, str]:
    """Validate evidence ids and exact luck-cycle identities for a chart."""
    available = collect_fact_ids(facts)
    cited = set(assessment.evidence_ids)
    for cycle in assessment.luck_cycles:
        for claim in [*cycle.opportunities, *cycle.tensions]:
            cited.update(claim.evidence_ids)
    missing_evidence = sorted(cited - available)
    if missing_evidence:
        return False, f"assessment cites unknown evidence ids: {', '.join(missing_evidence)}"

    actual_cycle_list = [
        item
        for item in facts.get("luck_cycles") or []
        if not item.get("is_pre_luck")
    ]
    if cycle_limit is not None:
        actual_cycle_list = actual_cycle_list[:cycle_limit]
    actual_cycles = {
        item.get("id"): item
        for item in actual_cycle_list
    }
    assessed_ids = {item.cycle_id for item in assessment.luck_cycles}
    unknown_cycles = sorted(assessed_ids - set(actual_cycles))
    if unknown_cycles:
        return False, f"assessment cites unknown luck cycles: {', '.join(unknown_cycles)}"
    if require_all_cycles:
        missing_cycles = sorted(set(actual_cycles) - assessed_ids)
        if missing_cycles:
            return False, f"assessment is missing luck cycles: {', '.join(missing_cycles)}"
    for item in assessment.luck_cycles:
        actual = actual_cycles[item.cycle_id]
        if (
            actual.get("name") != item.name
            or actual.get("start_year") != item.start_year
            or actual.get("end_year") != item.end_year
        ):
            return False, f"luck-cycle identity mismatch for {item.cycle_id}"
    return True, ""


def apply_luck_scores(facts: dict, assessment: WuxingPreferenceAssessment) -> dict:
    """Return a copy of facts with validated dayun scores attached."""
    result = deepcopy(facts)
    by_id = {item.cycle_id: item for item in assessment.luck_cycles}
    for cycle in result.get("luck_cycles") or []:
        item = by_id.get(cycle.get("id"))
        if not item:
            continue
        if (
            cycle.get("name") != item.name
            or cycle.get("start_year") != item.start_year
            or cycle.get("end_year") != item.end_year
        ):
            raise ValueError(f"luck-cycle identity mismatch for {item.cycle_id}")
        cycle["score"] = item.score
        cycle["score_status"] = "validated"
        cycle["assessment"] = item.model_dump()

    result["wuxing_preferences"] = assessment.model_dump()
    timeline = ((result.get("visuals") or {}).get("dayun_timeline") or {})
    for point in timeline.get("series") or []:
        item = by_id.get(point.get("id"))
        if item:
            point["score"] = item.score
            point["confidence"] = item.confidence
            point["headline"] = item.headline
    timeline["score_note"] = "走势分数来自已校验的五行喜忌与大运评估合同。"
    return result
