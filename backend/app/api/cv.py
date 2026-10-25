from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from backend.app.api.schemas import CVAnalysisResponse, CVStatusResponse, CVUploadResponse
from backend.app.core.errors import AdmissionError
from backend.app.providers.base import LLMProvider
from backend.app.services.cv_analysis_service import CVAnalysisService

router = APIRouter()


def get_provider(request: Request) -> LLMProvider:
    return request.app.state.provider


def get_cv_service(request: Request) -> CVAnalysisService:
    return request.app.state.services["cv_analysis"]


async def _upload(file, candidate_id, full_name, email, service):
    data = await file.read()
    if len(data) > service.max_bytes:
        raise AdmissionError("file_size", "El archivo excede el tamaño máximo permitido.", 413)
    result = service.upload_cv(
        candidate_id=candidate_id,
        full_name=full_name,
        email=email,
        file_name=file.filename or "cv.pdf",
        data=data,
        content_type=file.content_type,
    )
    return result


@router.post("", response_model=CVUploadResponse, status_code=200)
@router.post("/upload", response_model=CVUploadResponse, status_code=200)
async def upload_cv(
    file: UploadFile = File(...),
    candidate_id: str | None = Form(default=None),
    full_name: str | None = Form(default=None),
    email: str | None = Form(default=None),
    service: CVAnalysisService = Depends(get_cv_service),
):
    return await _upload(file, candidate_id, full_name, email, service)


@router.post("/{analysis_id}/analyze", response_model=CVAnalysisResponse, status_code=200)
@router.post("/{analysis_id}/analysis", response_model=CVAnalysisResponse, status_code=200)
@router.post("/{analysis_id}/start", response_model=CVAnalysisResponse, status_code=200)
@router.post("/{analysis_id}/start-analysis", response_model=CVAnalysisResponse, status_code=200)
async def start_analysis(
    analysis_id: str,
    provider: LLMProvider = Depends(get_provider),
    service: CVAnalysisService = Depends(get_cv_service),
):
    return await service.start_analysis(analysis_id, provider)


@router.get("/{analysis_id}", response_model=CVAnalysisResponse, status_code=200)
@router.get("/{analysis_id}/analysis", response_model=CVAnalysisResponse, status_code=200)
@router.get("/{analysis_id}/result", response_model=CVAnalysisResponse, status_code=200)
@router.get("/{analysis_id}/results", response_model=CVAnalysisResponse, status_code=200)
async def get_analysis(analysis_id: str, service: CVAnalysisService = Depends(get_cv_service)):
    return service.get_analysis(analysis_id)


@router.get("/{analysis_id}/status", response_model=CVStatusResponse, status_code=200)
async def get_status(analysis_id: str, service: CVAnalysisService = Depends(get_cv_service)):
    return service.get_status(analysis_id)


@router.delete("/{analysis_id}", status_code=200)
@router.delete("/{analysis_id}/delete", status_code=200)
async def delete_cv(analysis_id: str, service: CVAnalysisService = Depends(get_cv_service)):
    return service.delete_cv(analysis_id)