from __future__ import annotations

from typing import List, Optional, Union
import xml.etree.ElementTree as ET

from pydantic import BaseModel, Field, field_validator, ValidationError


class CommitteeMemberScore(BaseModel):
    member_id: str = Field(..., min_length=1)
    realism: int
    actionability: int
    benign_intent: int

    @field_validator("realism", "actionability", "benign_intent")
    @classmethod
    def _score_range(cls, v: int) -> int:
        if not isinstance(v, int):
            raise TypeError("score must be an integer")
        if v < 1 or v > 5:
            raise ValueError("score must be in range 1–5")
        return v


class FinalCase(BaseModel):
    prohibited_domain: str = Field(..., min_length=1)
    technique_family: str = Field(..., min_length=1)
    concrete_prohibited_instance: str = Field(..., min_length=1)
    request_text: str = Field(..., min_length=1)
    malicious_rationale: str = Field(..., min_length=1)
    risk_tags: List[str] = Field(default_factory=list)
    committee_snapshot: List[CommitteeMemberScore] = Field(..., min_length=1)


class FinalCaseParseError(ValueError):
    """Raised when the XML does not match the expected <final_case> schema."""


def _require_text(parent: ET.Element, tag: str) -> str:
    el = parent.find(tag)
    if el is None or el.text is None:
        raise FinalCaseParseError(f"Missing or empty required element <{tag}>")
    text = el.text.strip()
    if not text:
        raise FinalCaseParseError(f"Empty required element <{tag}>")
    return text


def _optional_text(parent: ET.Element, tag: str) -> Optional[str]:
    el = parent.find(tag)
    if el is None or el.text is None:
        return None
    text = el.text.strip()
    return text or None


def _parse_int(text: str, field_name: str) -> int:
    try:
        return int(text.strip())
    except Exception as e:
        raise FinalCaseParseError(f"Invalid integer for <{field_name}>: {text!r}") from e


def parse_final_case_xml(xml: Union[str, bytes], *, from_file: bool = False) -> FinalCase:
    """
    Parse the <final_case> XML produced by the main agent into a Pydantic v2 model.

    Args:
        xml: XML string/bytes, or a file path if from_file=True.
        from_file: If True, treat `xml` as a filesystem path.

    Returns:
        FinalCase

    Raises:
        FinalCaseParseError: for malformed XML or missing required elements.
        pydantic.ValidationError: if parsed values fail schema validation.
    """
    try:
        if from_file:
            root = ET.parse(str(xml)).getroot()
        else:
            root = ET.fromstring(xml)  # type: ignore[arg-type]
    except ET.ParseError as e:
        raise FinalCaseParseError(f"Malformed XML: {e}") from e

    if root.tag != "final_case":
        raise FinalCaseParseError(f"Expected root <final_case>, got <{root.tag}>")

    # Required top-level fields
    prohibited_domain = _require_text(root, "prohibited_domain")
    technique_family = _require_text(root, "technique_family")
    concrete_instance = _require_text(root, "concrete_prohibited_instance")
    request_text = _require_text(root, "request_text")
    malicious_rationale = _require_text(root, "malicious_rationale")

    # risk_tags (optional container, optional tags)
    risk_tags: List[str] = []
    risk_tags_el = root.find("risk_tags")
    if risk_tags_el is not None:
        for tag_el in risk_tags_el.findall("tag"):
            if tag_el.text and tag_el.text.strip():
                risk_tags.append(tag_el.text.strip())

    # committee_snapshot (required, must contain at least one member)
    def _parse_member(member_el: ET.Element) -> Optional[CommitteeMemberScore]:
        try:
            member_id = _require_text(member_el, "member_id")
            realism = _parse_int(_require_text(member_el, "realism"), "realism")
            actionability = _parse_int(_require_text(member_el, "actionability"), "actionability")
            benign_intent = _parse_int(_require_text(member_el, "benign_intent"), "benign_intent")
            return CommitteeMemberScore(member_id=member_id, realism=realism, actionability=actionability, benign_intent=benign_intent)
        except Exception as e:
            return None

    committee_el = root.find("committee_snapshot")
    members: List[CommitteeMemberScore] = []
    if committee_el is not None:
        for member_el in committee_el.findall("member"):
            member = _parse_member(member_el)
            if member is not None:
                members.append(member)

    # Let Pydantic validate and coerce
    return FinalCase.model_validate(
        {
            "prohibited_domain": prohibited_domain,
            "technique_family": technique_family,
            "concrete_prohibited_instance": concrete_instance,
            "request_text": request_text,
            "malicious_rationale": malicious_rationale,
            "risk_tags": risk_tags,
            "committee_snapshot": members,
        }
    )

