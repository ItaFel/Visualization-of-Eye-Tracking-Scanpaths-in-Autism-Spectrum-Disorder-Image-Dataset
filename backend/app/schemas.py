"""Pydantic schemas for API IO."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from backend.app.models import ConsentStatus, DiagnosticStatus


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: Optional[int] = None


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserRead(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class DiagnosticSessionBase(BaseModel):
    purchased: bool = False


class DiagnosticSessionCreate(DiagnosticSessionBase):
    pass


class DiagnosticSessionRead(DiagnosticSessionBase):
    id: int
    status: DiagnosticStatus
    consent_status: ConsentStatus
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    recommendations: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ConsentPayload(BaseModel):
    accepted: bool
    signed_by: Optional[str] = None


class DiagnosticResult(BaseModel):
    session_id: int
    status: DiagnosticStatus
    risk_score: Optional[float]
    risk_level: Optional[str]
    recommendations: Optional[str]


class UploadResponse(BaseModel):
    session_id: int
    artifact_path: str
    message: str
