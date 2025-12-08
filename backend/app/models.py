"""Database models."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class ConsentStatus(str, enum.Enum):
    pending = "pending"
    granted = "granted"
    declined = "declined"


class DiagnosticStatus(str, enum.Enum):
    draft = "draft"
    awaiting_upload = "awaiting_upload"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    sessions: list["DiagnosticSession"] = Relationship(back_populates="user")


class DiagnosticSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    status: DiagnosticStatus = Field(default=DiagnosticStatus.draft)
    consent_status: ConsentStatus = Field(default=ConsentStatus.pending)
    purchased: bool = Field(default=False)
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    recommendations: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    video_path: Optional[str] = None
    processed_scanpath_path: Optional[str] = None

    user: Optional[User] = Relationship(back_populates="sessions")


class VideoArtifact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="diagnosticsession.id")
    artifact_type: str = Field(default="raw")
    file_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
