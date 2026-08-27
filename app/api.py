from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.models import (
    Form,
    FormCreate,
    Health,
    Submission,
    SubmissionCreate,
)
from app.store import FormNotFoundError, InMemoryStore

router = APIRouter()

# Single process-local store instance
_store = InMemoryStore()


# Dependency provider for store instance
def get_store() -> InMemoryStore:
    return _store


# Dependency type aliases for FastAPI injection
StoreDep = Annotated[InMemoryStore, Depends(get_store)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


# Health check endpoint returning app version and environment status
@router.get("/health", response_model=Health, tags=["ops"])
async def health(settings: SettingsDep) -> Health:
    return Health(
        status="ok",
        version=settings.app_version,
        environment=settings.environment,
    )


# Create and store a new form
@router.post(
    "/forms",
    response_model=Form,
    status_code=status.HTTP_201_CREATED,
    tags=["forms"],
)
async def create_form(payload: FormCreate, store: StoreDep) -> Form:
    return store.create_form(payload)


# Create a new submission for a specific form
@router.post(
    "/forms/{form_id}/submissions",
    response_model=Submission,
    status_code=status.HTTP_201_CREATED,
    tags=["submissions"],
)
async def create_submission(
    form_id: UUID, payload: SubmissionCreate, store: StoreDep
) -> Submission:
    try:
        return store.add_submission(form_id, payload)
    except FormNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Form not found"
        ) from None


# Retrieve all submissions for a specific form
@router.get(
    "/forms/{form_id}/submissions",
    response_model=list[Submission],
    tags=["submissions"],
)
async def list_submissions(form_id: UUID, store: StoreDep) -> list[Submission]:
    try:
        return store.list_submissions(form_id)
    except FormNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Form not found"
        ) from None