from fastapi import APIRouter, Depends, Request

from backend.app.api.schemas import (
    CreatePreparationPlanRequest,
)
from backend.app.core.errors import AdmissionError
from backend.app.providers.base import LLMProvider
from backend.app.services.preparation_service import PreparationService

router = APIRouter()


def get_provider(request: Request) -> LLMProvider:
    return request.app.state.provider


def get_preparation_service(request: Request) -> PreparationService:
    return request.app.state.services["preparation"]


@router.post("", status_code=200)
@router.post("/generate", status_code=200)
async def generate_plan(
    payload: CreatePreparationPlanRequest,
    provider: LLMProvider = Depends(get_provider),
    service: PreparationService = Depends(get_preparation_service),
):
    return await service.generate_plan(
        provider=provider,
        candidate_id=payload.candidate_id,
        target_date=payload.target_date,
        study_minutes_per_week=payload.study_minutes_per_week,
        goal=payload.goal,
        topics=payload.topics,
    )


@router.get("/candidate/{candidate_id}/active")
def active_plan(candidate_id: str, service: PreparationService = Depends(get_preparation_service)):
    plan = service.get_active_plan(candidate_id)
    if plan is None:
        return {"candidate_id": candidate_id, "plan": None}
    return plan


@router.get("/candidate/{candidate_id}")
def list_plans(candidate_id: str, service: PreparationService = Depends(get_preparation_service)):
    return {"candidate_id": candidate_id, "items": service.list_plans(candidate_id)}


@router.get("/{plan_id}")
def get_plan(plan_id: str, service: PreparationService = Depends(get_preparation_service)):
    return service.get_plan(plan_id)


@router.post("/activities/{activity_id}/complete")
def complete_activity(activity_id: str, service: PreparationService = Depends(get_preparation_service)):
    return service.update_activity(activity_id, "completed")


@router.post("/activities/{activity_id}/pending")
def pending_activity(activity_id: str, service: PreparationService = Depends(get_preparation_service)):
    return service.update_activity(activity_id, "pending")


@router.get("/candidate/{candidate_id}/interviews")
def compare_interviews(candidate_id: str, service: PreparationService = Depends(get_preparation_service)):
    return {"candidate_id": candidate_id, "items": service.compare_interviews(candidate_id)}