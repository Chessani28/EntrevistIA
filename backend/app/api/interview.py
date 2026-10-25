from fastapi import APIRouter, Depends, Request

from backend.app.api.schemas import (
    AnswerResponse,
    CompleteInterviewResponse,
    CreateInterviewSessionRequest,
    CurrentQuestionResponse,
    FollowupResponse,
    InterviewHistoryResponse,
    InterviewSessionResponse,
    StartInterviewResponse,
    SubmitAnswerRequest,
)
from backend.app.core.errors import AdmissionError
from backend.app.providers.base import LLMProvider

router = APIRouter()


def get_provider(request: Request) -> LLMProvider:
    return request.app.state.provider


def get_interview_service(request: Request):
    return request.app.state.services["interview"]


def _session_response(session: dict) -> InterviewSessionResponse:
    return InterviewSessionResponse(
        session_id=session["id"],
        candidate_id=session["candidate_id"],
        mode=session["mode"],
        question_count=session["question_count"],
        status=session["status"],
        current_question_id=session.get("current_question_id"),
        current_position=session.get("current_position") or 0,
        started_at=session.get("started_at"),
        completed_at=session.get("completed_at"),
        created_at=session["created_at"],
        updated_at=session["updated_at"],
    )


@router.post("", response_model=InterviewSessionResponse)
async def create_interview_session(
    payload: CreateInterviewSessionRequest,
    service=Depends(get_interview_service),
):
    result = service.create_session(
        candidate_id=payload.candidate_id,
        full_name=payload.full_name,
        email=payload.email,
        mode=payload.mode,
    )
    return _session_response(result["session"])


@router.get("/{session_id}", response_model=InterviewSessionResponse)
async def get_interview_session(session_id: str, service=Depends(get_interview_service)):
    session = service._get_session_or_404(session_id)
    return _session_response(session)


@router.post("/{session_id}/start", response_model=StartInterviewResponse)
async def start_interview(session_id: str, service=Depends(get_interview_service)):
    result = service.start(session_id)
    from backend.app.api.schemas import InterviewQuestion

    question = None
    if result.get("current_question"):
        question = InterviewQuestion(**result["current_question"])
    return StartInterviewResponse(
        session=_session_response(result["session"]),
        current_question=question,
        total_questions=result["total_questions"],
    )


@router.get("/{session_id}/current-question", response_model=CurrentQuestionResponse)
async def current_question(session_id: str, service=Depends(get_interview_service)):
    result = service.get_current_question(session_id)
    from backend.app.api.schemas import InterviewQuestion

    question = None
    if result.get("current_question"):
        question = InterviewQuestion(**result["current_question"])
    return CurrentQuestionResponse(
        session_id=result["session_id"],
        status=result["status"],
        position=result["position"],
        total_questions=result["total_questions"],
        current_question=question,
    )


@router.post("/{session_id}/answers", response_model=AnswerResponse)
async def submit_answer(
    session_id: str,
    payload: SubmitAnswerRequest,
    service=Depends(get_interview_service),
):
    result = service.submit_answer(session_id, payload.question_id, payload.answer)
    from backend.app.api.schemas import InterviewQuestion

    next_question = None
    if result.get("next_question"):
        next_question = InterviewQuestion(**result["next_question"])
    return AnswerResponse(
        session_id=result["session_id"],
        question_id=result["question_id"],
        answer_id=result["answer_id"],
        status=result["status"],
        next_question=next_question,
        completed_available=result.get("completed_available", True),
    )


@router.get("/{session_id}/history", response_model=InterviewHistoryResponse)
async def interview_history(session_id: str, service=Depends(get_interview_service)):
    result = service.get_history(session_id)
    from backend.app.api.schemas import InterviewHistoryItem

    items = [InterviewHistoryItem(**item) for item in result["items"]]
    return InterviewHistoryResponse(
        session_id=result["session_id"],
        status=result["status"],
        items=items,
    )


@router.post("/{session_id}/complete", response_model=CompleteInterviewResponse)
async def complete_interview(session_id: str, service=Depends(get_interview_service)):
    result = service.complete(session_id)
    return CompleteInterviewResponse(
        session_id=result["session_id"],
        status=result["status"],
        completed_at=result.get("completed_at"),
    )


@router.post("/{session_id}/follow-up", response_model=FollowupResponse)
async def generate_followup(
    session_id: str,
    provider: LLMProvider = Depends(get_provider),
    service=Depends(get_interview_service),
):
    result = await service.generate_followup(session_id, provider)
    from backend.app.api.schemas import InterviewQuestion

    question = None
    if result.get("followup_question"):
        question = InterviewQuestion(**result["followup_question"])
    return FollowupResponse(
        session_id=result["session_id"],
        should_ask=result["should_ask"],
        followup_question=question,
        message=result.get("message"),
    )
