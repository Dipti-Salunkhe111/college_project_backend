# schemas/testSchema.py
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

class Question(BaseModel):
    id: int
    text: str
    options: List[str]

class TestDataSchema(BaseModel):
    test_type: str
    questions: List[Question]

class QuestionSubmission(BaseModel):
    question_id: int
    question_text: str
    selected_answer: str

class PersonalityTestSubmission(BaseModel):
    questions_data: List[QuestionSubmission]