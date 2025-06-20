# novelist_cli/models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class ChapterBeat(BaseModel):
    summary: str
    target_words: int | None = Field(None, ge=50)
    sub_plots: List[str] = []

class Chapter(BaseModel):
    number: int = Field(..., ge=1)
    title: str
    beats: List[ChapterBeat]

class Outline(BaseModel):
    title: str
    genre: str
    target_length: int = Field(..., ge=1000)
    chapters: List[Chapter]
    metadata: Dict[str, Any] = {}

class StyleGuide(BaseModel):
    voice: str
    tense: str
    sentence_length: str = "moderate"
    lexical_density: str = "moderate"
    tone: str | None = None
    banned_cliches: List[str] = []
    rules: Dict[str, str] = {}
