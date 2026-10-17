# SPDX-License-Identifier: Apache-2.0
"""Public request schemas. Unknown and absent are different statements."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .structure import FIELD_KEYS


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Claim(Strict):
    state: Literal["stated", "inferred", "verified", "unknown", "not_visible", "conflicting"] = "unknown"
    values: list[str] = Field(default_factory=list, max_length=12)
    source: str = Field(default="import", min_length=1, max_length=300)
    note: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def check(self):
        self.values = sorted({v.strip() for v in self.values if v.strip()})
        if any(len(v) > 120 for v in self.values):
            raise ValueError("Part values must be at most 120 characters")
        if self.state in ("unknown", "not_visible") and self.values:
            raise ValueError("Unknown or invisible parts cannot have values")
        if self.state in ("stated", "inferred", "verified", "conflicting") and not self.values:
            raise ValueError("A known part requires a value; use 'none' for a known absence")
        return self


class ProductInput(Strict):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
    title: str = Field(min_length=1, max_length=1000)
    brand: str = Field(default="", max_length=200)
    category: str = Field(default="", max_length=100)
    identity_group: str = Field(default="", max_length=200)
    source_url: str = Field(default="", max_length=2000)
    rights: str = Field(min_length=1, max_length=1000)
    observed_at: str = Field(default="", max_length=50)
    parts: dict[str, Claim] = Field(default_factory=dict)

    @field_validator("parts")
    @classmethod
    def part_keys(cls, v):
        if set(v) - FIELD_KEYS:
            raise ValueError("Unknown part fields: " + ", ".join(sorted(set(v) - FIELD_KEYS)))
        return v


class PartEdit(Strict):
    snapshot: str = Field(min_length=64, max_length=64)
    field: str
    claim: Claim
    reviewer: str = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=1000)

    @field_validator("field")
    @classmethod
    def valid_field(cls, v):
        if v not in FIELD_KEYS:
            raise ValueError("Unknown part field")
        return v


class Review(Strict):
    a: str
    b: str
    snapshot_a: str = Field(min_length=64, max_length=64)
    snapshot_b: str = Field(min_length=64, max_length=64)
    relation: Literal["same_visible_design", "modified_design", "shared_detail", "different", "unsure"]
    changed: list[str] = Field(default_factory=list, max_length=30)
    reviewer: str = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=1000)
    smv_decision: Literal["not_reviewed", "needs_time_study", "accepted_for_trial", "rejected"] = (
        "not_reviewed"
    )
    smv_library_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def check(self):
        if self.a == self.b or set(self.changed) - FIELD_KEYS:
            raise ValueError("Choose different garments and valid changed parts")
        if self.relation == "same_visible_design" and self.changed:
            raise ValueError("A same-design review cannot have changed parts")
        self.changed = sorted(set(self.changed))
        return self
