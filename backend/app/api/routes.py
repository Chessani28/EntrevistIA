from fastapi import APIRouter, Depends, Request

from backend.app.api.schemas import ChatRequest, ChatResponse, HealthResponse, StatusResponse
from backend.app.providers.base import LLMProvider

router = APIRouter()


def get_provider(request: Request) -> LLMProvider:
    return request.app.state.provider


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@router.get("/api/v1/status", response_model=StatusResponse)
async def status(provider: LLMProvider = Depends(get_provider)):
    available = await provider.is_available()
    return StatusResponse(
        status="ready" if available else "unavailable",
        provider=provider.name, model=provider.model, mock=provider.name == "mock",
    )


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, provider: LLMProvider = Depends(get_provider)):
    await provider.ensure_available()
    answer = await provider.generate(payload.message)
    return ChatResponse(answer=answer, provider=provider.name, model=provider.model)

from backend.app.api.schemas import CandidateProfileRequest, CandidateProfileResponse


def get_candidate_service(request: Request):
    return request.app.state.services['candidates']


def get_question_service(request: Request):
    return request.app.state.services['questions']


def get_session_service(request: Request):
    return request.app.state.services['sessions']


@router.get('/api/v1/candidates')
async def list_candidates(service=Depends(get_candidate_service)):
    return [CandidateProfileResponse(**item) for item in service.list()]


@router.post('/api/v1/candidates', response_model=CandidateProfileResponse)
async def create_candidate(payload: CandidateProfileRequest, service=Depends(get_candidate_service)):
    profile = {}
    if payload.academic_background is not None:
        profile['academic_background'] = payload.academic_background
    if payload.professional_background is not None:
        profile['professional_background'] = payload.professional_background
    return CandidateProfileResponse(**service.create(payload.full_name, payload.email, profile))


@router.get('/api/v1/candidates/{candidate_id}', response_model=CandidateProfileResponse)
async def get_candidate(candidate_id: str, service=Depends(get_candidate_service)):
    item = service.get(candidate_id)
    if item is None:
        raise AdmissionError('candidate_not_found', 'No existe el candidato indicado.', 404)
    return CandidateProfileResponse(**item)


@router.patch('/api/v1/candidates/{candidate_id}', response_model=CandidateProfileResponse)
async def update_candidate(candidate_id: str, payload: CandidateProfileRequest, service=Depends(get_candidate_service)):
    profile = {}
    if payload.academic_background is not None:
        profile['academic_background'] = payload.academic_background
    if payload.professional_background is not None:
        profile['professional_background'] = payload.professional_background
    item = service.update(candidate_id, full_name=payload.full_name, email=payload.email, academic_profile=profile)
    return CandidateProfileResponse(**item)


@router.get('/api/v1/questions')
async def list_questions(category: str | None = None, service=Depends(get_question_service)):
    return service.list_questions(category)


@router.get('/api/v1/questions/{question_id}')
async def get_question(question_id: str, service=Depends(get_question_service)):
    item = service.get(question_id)
    if item is None:
        raise AdmissionError('question_not_found', 'No existe la pregunta indicada.', 404)
    return item


@router.get('/api/v1/sessions')
async def list_sessions(limit: int = 50, service=Depends(get_session_service)):
    return service.list(limit)


from backend.app.core.errors import AdmissionError

