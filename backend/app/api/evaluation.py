from fastapi import APIRouter, Depends, Request

from backend.app.api.schemas import (
    AnswerEvaluationListResponse,
    AnswerEvaluationResponse,
    EvaluateAnswerRequest,
    ImprovedAnswerResponse,
)
from backend.app.core.errors import AdmissionError
from backend.app.providers.base import LLMProvider
from backend.app.services.answer_evaluation_service import AnswerEvaluationService

router = APIRouter()


def get_provider(request: Request) -> LLMProvider:
    return request.app.state.provider


def get_evaluation_service(request: Request) -> AnswerEvaluationService:
    return request.app.state.services["answer_evaluation"]


def _resp(data):
    return AnswerEvaluationResponse(**data)


async def _evaluate_with_body(payload, provider, service):
    data = await service.evaluate_answer(
        provider=provider,
        session_id=payload.session_id,
        question_id=payload.question_id,
        answer_id=payload.answer_id,
        question_prompt=payload.question_prompt,
        candidate_answer=payload.candidate_answer or payload.answer,
        answer=payload.answer,
        force=payload.force,
    )
    return _resp(data)

@router.post("", response_model=AnswerEvaluationResponse)
@router.post("/evaluate", response_model=AnswerEvaluationResponse)
@router.post("/evaluation", response_model=AnswerEvaluationResponse)
async def evaluate_answer_root(
    payload: EvaluateAnswerRequest,
    provider: LLMProvider = Depends(get_provider),
    service: AnswerEvaluationService = Depends(get_evaluation_service),
):
    return await _evaluate_with_body(payload, provider, service)


@router.post("/answers/{answer_id}/evaluate", response_model=AnswerEvaluationResponse)
@router.post("/answers/{answer_id}/evaluation", response_model=AnswerEvaluationResponse)
@router.post("/answer/{answer_id}/evaluate", response_model=AnswerEvaluationResponse)
@router.post("/answer/{answer_id}/evaluation", response_model=AnswerEvaluationResponse)
@router.post("/by-answer/{answer_id}/evaluate", response_model=AnswerEvaluationResponse)
async def evaluate_by_answer(
    answer_id: str,
    payload: EvaluateAnswerRequest | None = None,
    provider: LLMProvider = Depends(get_provider),
    service: AnswerEvaluationService = Depends(get_evaluation_service),
):
    force = getattr(payload, "force", False) if payload else False
    data = await service.evaluate_answer(provider=provider, answer_id=answer_id, force=force)
    return _resp(data)

@router.post("/{session_id}/answers/{question_id}/evaluate", response_model=AnswerEvaluationResponse)
@router.post("/{session_id}/answers/{question_id}/evaluation", response_model=AnswerEvaluationResponse)
@router.post("/{session_id}/questions/{question_id}/evaluate", response_model=AnswerEvaluationResponse)
@router.post("/{session_id}/questions/{question_id}/evaluation", response_model=AnswerEvaluationResponse)
async def evaluate_by_session_question(
    session_id: str,
    question_id: str,
    payload: EvaluateAnswerRequest | None = None,
    provider: LLMProvider = Depends(get_provider),
    service: AnswerEvaluationService = Depends(get_evaluation_service),
):
    candidate_answer = None
    question_prompt = None
    force = False
    if payload:
        candidate_answer = payload.candidate_answer or payload.answer
        question_prompt = payload.question_prompt
        force = payload.force
    data = await service.evaluate_answer(
        provider=provider,
        session_id=session_id,
        question_id=question_id,
        question_prompt=question_prompt,
        candidate_answer=candidate_answer,
        force=force,
    )
    return _resp(data)

@router.post("/{session_id}/evaluate", response_model=AnswerEvaluationResponse)
async def evaluate_session_root(
    session_id: str,
    payload: EvaluateAnswerRequest,
    provider: LLMProvider = Depends(get_provider),
    service: AnswerEvaluationService = Depends(get_evaluation_service),
):
    payload.session_id = session_id
    return await _evaluate_with_body(payload, provider, service)


@router.get("/answers/{answer_id}", response_model=AnswerEvaluationResponse)
@router.get("/answers/{answer_id}/evaluation", response_model=AnswerEvaluationResponse)
@router.get("/answer/{answer_id}", response_model=AnswerEvaluationResponse)
@router.get("/answer/{answer_id}/evaluation", response_model=AnswerEvaluationResponse)
@router.get("/by-answer/{answer_id}", response_model=AnswerEvaluationResponse)
async def get_evaluation_by_answer(
    answer_id: str,
    service: AnswerEvaluationService = Depends(get_evaluation_service),
):
    data = service.get_evaluation(answer_id=answer_id)
    return _resp(data)


@router.get("/evaluation/{evaluation_id}", response_model=AnswerEvaluationResponse)
@router.get("/evaluations/{evaluation_id}", response_model=AnswerEvaluationResponse)
@router.get("/id/{evaluation_id}", response_model=AnswerEvaluationResponse)
@router.get("/{evaluation_id}", response_model=AnswerEvaluationResponse)
async def get_evaluation_by_id(
    evaluation_id: str,
    service: AnswerEvaluationService = Depends(get_evaluation_service),
):
    data = service.get_evaluation(evaluation_id=evaluation_id)
    return _resp(data)


@router.get("/{session_id}/evaluations", response_model=AnswerEvaluationListResponse)
@router.get("/sessions/{session_id}/evaluations", response_model=AnswerEvaluationListResponse)
@router.get("/session/{session_id}/evaluations", response_model=AnswerEvaluationListResponse)
@router.get("/by-session/{session_id}", response_model=AnswerEvaluationListResponse)
@router.get("/sessions/{session_id}", response_model=AnswerEvaluationListResponse)
@router.get("/session/{session_id}", response_model=AnswerEvaluationListResponse)
async def list_evaluations(
    session_id: str,
    service: AnswerEvaluationService = Depends(get_evaluation_service),
):
    items = service.list_evaluations(session_id)
    converted = [AnswerEvaluationResponse(**item) for item in items]
    return AnswerEvaluationListResponse(session_id=session_id, items=converted, evaluations=converted)


@router.get("/{evaluation_id}/improved-answer", response_model=ImprovedAnswerResponse)
@router.get("/{evaluation_id}/improvement", response_model=ImprovedAnswerResponse)
@router.get("/{evaluation_id}/improved", response_model=ImprovedAnswerResponse)
async def get_improved_answer_get(
    evaluation_id: str,
    service: AnswerEvaluationService = Depends(get_evaluation_service),
):
    data = service.get_improved_answer(evaluation_id=evaluation_id)
    return ImprovedAnswerResponse(**data)


@router.post("/{evaluation_id}/improved-answer", response_model=ImprovedAnswerResponse)
@router.post("/{evaluation_id}/improve", response_model=ImprovedAnswerResponse)
@router.post("/{evaluation_id}/improved", response_model=ImprovedAnswerResponse)
async def get_improved_answer_post(
    evaluation_id: str,
    service: AnswerEvaluationService = Depends(get_evaluation_service),
):
    data = service.get_improved_answer(evaluation_id=evaluation_id)
    return ImprovedAnswerResponse(**data)


@router.post("/improved-answer", response_model=ImprovedAnswerResponse)
async def improved_answer_root(
    payload: EvaluateAnswerRequest,
    service: AnswerEvaluationService = Depends(get_evaluation_service),
):
    data = service.get_improved_answer(evaluation_id=payload.answer_id, answer_id=payload.answer_id)
    return ImprovedAnswerResponse(**data)
