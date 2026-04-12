"""Anonymization mapping schemas for case directory metadata."""

from pydantic import BaseModel


class AnonymizationMapping(BaseModel):
    original: str
    anonymized: str
    entity_type: str
