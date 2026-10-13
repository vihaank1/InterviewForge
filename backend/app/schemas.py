"""Typed HTTP requests and validated model-response data.

AI output schemas intentionally avoid JSON Schema length/range keywords: some
structured-output providers do not support them. Local validators still enforce
basic safety and scoring bounds after parsing.
"""
from typing import Literal
from pydantic import BaseModel, Field, field_validator

Track = Literal['backend', 'frontend', 'systems', 'ml', 'general']
Difficulty = Literal['Easy', 'Medium', 'Hard']

class StartSession(BaseModel):
    role: str = Field(min_length=2, max_length=80)
    track: Track = 'backend'
    difficulty: Difficulty = 'Medium'

class SubmitAnswer(BaseModel):
    answer: str = Field(min_length=3, max_length=12000)

class DesignRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=3000)
    candidate_design: str | None = Field(default=None, max_length=12000)

    @field_validator('candidate_design')
    @classmethod
    def normalize_design(cls, value: str | None):
        return (value.strip() or None) if value is not None else None

class Question(BaseModel):
    question: str
    focus: str

    @field_validator('question', 'focus')
    @classmethod
    def meaningful_text(cls, value: str):
        if not (2 <= len(value.strip()) <= 1500):
            raise ValueError('Expected a bounded, nonempty model response')
        return value.strip()

class Rubric(BaseModel):
    accuracy: int
    reasoning: int
    tradeoffs: int
    clarity: int

    @field_validator('accuracy', 'reasoning', 'tradeoffs', 'clarity')
    @classmethod
    def ten_point_scale(cls, value: int):
        if not 0 <= value <= 10:
            raise ValueError('Rubric rating must be between 0 and 10')
        return value

class Evaluation(BaseModel):
    rubric: Rubric
    strengths: list[str]
    improvements: list[str]
    weak_spots: list[str]
    feedback: str

    @field_validator('strengths', 'improvements')
    @classmethod
    def has_specific_points(cls, value: list[str]):
        if not 1 <= len(value) <= 5:
            raise ValueError('Expected one to five points')
        return value

    @field_validator('weak_spots')
    @classmethod
    def bounded_weak_spots(cls, value: list[str]):
        if len(value) > 5:
            raise ValueError('Too many weak spots')
        return value

    @field_validator('feedback')
    @classmethod
    def bounded_feedback(cls, value: str):
        if not 10 <= len(value.strip()) <= 3000:
            raise ValueError('Invalid feedback length')
        return value.strip()

class Architecture(BaseModel):
    summary: str
    services: list[str]
    databases: list[str]
    caching: list[str]
    apis: list[str]
    scaling_strategy: str
    tradeoffs: list[str]
    assumptions: list[str]
    diagram: str

    @field_validator('diagram')
    @classmethod
    def valid_diagram_header(cls, value: str):
        if len(value) > 8000 or not value.lstrip().startswith(('flowchart ', 'graph ')):
            raise ValueError('Expected a bounded Mermaid graph/flowchart')
        return value

    @field_validator('services', 'databases', 'caching', 'apis', 'tradeoffs', 'assumptions')
    @classmethod
    def bounded_lists(cls, value: list[str]):
        if len(value) > 20:
            raise ValueError('Too many architecture elements')
        return value

class DesignRubric(BaseModel):
    scalability: int
    reliability: int
    tradeoffs: int
    clarity: int

    @field_validator('scalability', 'reliability', 'tradeoffs', 'clarity')
    @classmethod
    def ten_point_scale(cls, value: int):
        if not 0 <= value <= 10:
            raise ValueError('Rubric rating must be between 0 and 10')
        return value

class DesignEvaluation(BaseModel):
    rubric: DesignRubric
    strengths: list[str]
    risks: list[str]
    improvements: list[str]
    feedback: str

    @field_validator('strengths', 'risks', 'improvements')
    @classmethod
    def bounded_points(cls, value: list[str]):
        if not 1 <= len(value) <= 6:
            raise ValueError('Expected one to six points')
        return value

    @field_validator('feedback')
    @classmethod
    def bounded_feedback(cls, value: str):
        if not 10 <= len(value.strip()) <= 3000:
            raise ValueError('Invalid feedback length')
        return value.strip()
