from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class DiagnosisRequest(BaseModel):
    user_id: str
    consent: bool

class DiagnosisResult(BaseModel):
    risk_level: str # "High", "Low"
    score: float
    recommendations: str
