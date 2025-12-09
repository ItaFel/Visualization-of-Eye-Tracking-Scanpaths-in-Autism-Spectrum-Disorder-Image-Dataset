from fastapi import APIRouter

from backend.app.routes import auth, diagnostics

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(diagnostics.router)
