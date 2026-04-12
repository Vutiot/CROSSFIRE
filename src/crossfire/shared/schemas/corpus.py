"""Corpus document schemas."""

from pydantic import BaseModel


class Document(BaseModel):
    document_id: str
    source: str
    document_type: str
    source_case_id: str
    scope_classification: str
    content: str
