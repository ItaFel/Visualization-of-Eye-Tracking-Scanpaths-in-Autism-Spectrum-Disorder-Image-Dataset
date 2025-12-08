"""Endpoints for managing diagnostic sessions."""
from __future__ import annotations

import time
from pathlib import Path
from typing import List

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi import HTTPException, status
from sqlmodel import select

from backend.app import models, schemas
from backend.app.auth import CurrentUser, SessionDep
from backend.app.config import get_settings
from backend.app.services.diagnostics import DiagnosticService, process_session_video

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])
settings = get_settings()


@router.get("/instructions")
def get_preparation_instructions() -> dict:
    return {
        "environment": [
            "Ensure even, indirect lighting without glare",
            "Seat the child ~40cm from the device",
            "Stabilize the phone on a tripod or stand",
        ],
        "recording": [
            "Keep the child centered in the frame",
            "Avoid background distractions",
            "Confirm battery is above 30% and device is plugged in",
        ],
    }


@router.post("/sessions", response_model=schemas.DiagnosticSessionRead)
def create_session(
    payload: schemas.DiagnosticSessionCreate,
    current_user: CurrentUser,
    session: SessionDep,
) -> models.DiagnosticSession:
    service = DiagnosticService(session)
    return service.create_session(current_user.id, payload.purchased)


@router.get("/sessions", response_model=List[schemas.DiagnosticSessionRead])
def list_sessions(current_user: CurrentUser, session: SessionDep):
    statement = (
        select(models.DiagnosticSession)
        .where(models.DiagnosticSession.user_id == current_user.id)
        .order_by(models.DiagnosticSession.created_at.desc())
    )
    return session.exec(statement).all()


@router.get("/sessions/{session_id}", response_model=schemas.DiagnosticSessionRead)
def get_session(session_id: int, current_user: CurrentUser, session: SessionDep):
    service = DiagnosticService(session)
    diagnostic = service.get_session(session_id, current_user.id)
    return diagnostic


@router.post("/sessions/{session_id}/consent", response_model=schemas.DiagnosticSessionRead)
def sign_consent(
    session_id: int,
    payload: schemas.ConsentPayload,
    current_user: CurrentUser,
    session: SessionDep,
):
    service = DiagnosticService(session)
    diagnostic = service.get_session(session_id, current_user.id)
    return service.record_consent(diagnostic, payload.accepted)


async def _persist_upload(upload: UploadFile, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(destination, "wb") as out_file:
        while chunk := await upload.read(1024 * 1024):
            await out_file.write(chunk)
    await upload.close()
    return destination


@router.post(
    "/sessions/{session_id}/video",
    response_model=schemas.UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_video(
    session_id: int,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(),
    session: SessionDep = Depends(),
):
    service = DiagnosticService(session)
    diagnostic = service.get_session(session_id, current_user.id)
    if diagnostic.consent_status != models.ConsentStatus.granted:
        raise HTTPException(status_code=400, detail="Consent must be granted before upload")

    timestamp = int(time.time())
    suffix = Path(file.filename or "recording.mp4").suffix or ".mp4"
    destination = Path(settings.uploads_dir) / f"session_{session_id}_{timestamp}{suffix}"
    saved_path = await _persist_upload(file, destination)
    service.attach_video(diagnostic, saved_path)

    background_tasks.add_task(process_session_video, diagnostic.id, str(saved_path))

    return schemas.UploadResponse(
        session_id=diagnostic.id,
        artifact_path=str(saved_path),
        message="Video received. Processing has started.",
    )
