"""API v1 router package."""
from fastapi import APIRouter
from app.api.v1.repos import router as repos_router
from app.api.v1.issues import router as issues_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.review import router as review_router

api_v1_router = APIRouter()
api_v1_router.include_router(repos_router, prefix="/repos", tags=["Repositories"])
api_v1_router.include_router(issues_router, prefix="/issues", tags=["Issues & Planning"])
api_v1_router.include_router(tasks_router, prefix="/tasks", tags=["Execution & Tasks"])
api_v1_router.include_router(review_router, prefix="/review", tags=["Code Review & PR"])

__all__ = ["api_v1_router"]



