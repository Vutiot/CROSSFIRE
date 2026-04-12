"""Scope map schemas for case directory metadata."""

from pydantic import BaseModel


class ScopeMapEntry(BaseModel):
    document_id: str
    scope_classification: str


class ScopeMap(BaseModel):
    case_id: str
    entries: list[ScopeMapEntry]
