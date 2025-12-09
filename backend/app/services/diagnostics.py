"""Business logic for diagnostics workflow."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from backend.app import models
from backend.app.config import get_settings
from backend.app.database import session_scope
from backend.app.video_pipeline.service import VideoProcessingService

settings = get_settings()


class DiagnosticService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_session(self, user_id: int, purchased: bool) -> models.DiagnosticSession:
        diagnostic = models.DiagnosticSession(
            user_id=user_id,
            status=models.DiagnosticStatus.awaiting_upload,
            purchased=purchased,
        )
        self.session.add(diagnostic)
        self.session.commit()
        self.session.refresh(diagnostic)
        return diagnostic

    def get_session(self, session_id: int, user_id: Optional[int] = None) -> models.DiagnosticSession:
        diagnostic = self.session.get(models.DiagnosticSession, session_id)
        if diagnostic is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        if user_id and diagnostic.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        return diagnostic

    def record_consent(
        self, diagnostic: models.DiagnosticSession, accepted: bool
    ) -> models.DiagnosticSession:
        diagnostic.consent_status = (
            models.ConsentStatus.granted if accepted else models.ConsentStatus.declined
        )
        diagnostic.status = (
            models.DiagnosticStatus.awaiting_upload
            if accepted
            else models.DiagnosticStatus.draft
        )
        diagnostic.updated_at = datetime.utcnow()
        self.session.add(diagnostic)
        self.session.commit()
        self.session.refresh(diagnostic)
        return diagnostic

    def attach_video(self, diagnostic: models.DiagnosticSession, path: Path) -> models.DiagnosticSession:
        diagnostic.video_path = str(path)
        diagnostic.status = models.DiagnosticStatus.processing
        diagnostic.updated_at = datetime.utcnow()
        artifact = models.VideoArtifact(session_id=diagnostic.id, file_path=str(path))
        self.session.add(artifact)
        self.session.add(diagnostic)
        self.session.commit()
        self.session.refresh(diagnostic)
        return diagnostic

    def update_result(
        self,
        diagnostic: models.DiagnosticSession,
        result: dict,
    ) -> models.DiagnosticSession:
        diagnostic.risk_score = float(result.get("risk_score")) if result.get("risk_score") else None
        diagnostic.risk_level = result.get("risk_level")
        diagnostic.recommendations = result.get("recommendations")
        diagnostic.processed_scanpath_path = result.get("scanpath_path")
        diagnostic.status = models.DiagnosticStatus.completed
        diagnostic.updated_at = datetime.utcnow()
        self.session.add(diagnostic)
        self.session.commit()
        self.session.refresh(diagnostic)
        return diagnostic

    def mark_failed(self, diagnostic: models.DiagnosticSession, reason: str) -> None:
        diagnostic.status = models.DiagnosticStatus.failed
        diagnostic.recommendations = reason
        diagnostic.updated_at = datetime.utcnow()
        self.session.add(diagnostic)
        self.session.commit()


def process_session_video(session_id: int, video_path: str) -> None:
    """Background processing entry point."""
    video_service = VideoProcessingService()
    with session_scope() as session:
        diagnostic = session.get(models.DiagnosticSession, session_id)
        if diagnostic is None:
            return
        try:
            result = video_service.process_video(session_id, video_path)
        except Exception as exc:  # pragma: no cover - background worker
            diagnostic.status = models.DiagnosticStatus.failed
            diagnostic.recommendations = f"Processing error: {exc}"
            diagnostic.updated_at = datetime.utcnow()
            session.add(diagnostic)
            session.commit()
            return
        diagnostic.risk_score = float(result.get("risk_score", 0.0))
        diagnostic.risk_level = result.get("risk_level")
        diagnostic.recommendations = result.get("recommendations")
        diagnostic.processed_scanpath_path = result.get("scanpath_path")
        diagnostic.status = models.DiagnosticStatus.completed
        diagnostic.updated_at = datetime.utcnow()
        session.add(diagnostic)
        session.commit()
*** End Patch}