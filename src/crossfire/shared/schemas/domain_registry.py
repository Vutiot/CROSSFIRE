"""Domain registry schemas for case directory metadata."""

from pydantic import BaseModel


class DomainEntry(BaseModel):
    domain: str
    original_value: str
    anonymized_value: str


class DomainRegistry(BaseModel):
    case_id: str
    entries: list[DomainEntry]
