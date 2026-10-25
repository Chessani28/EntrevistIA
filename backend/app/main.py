from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from backend.app.api.routes import router
from backend.app.api.interview import router as interview_router
from backend.app.api.cv import router as cv_router
from backend.app.api.evaluation import router as evaluation_router
from backend.app.api.report import router as report_router
from backend.app.core.config import settings
from backend.app.core.errors import AdmissionError
from backend.app.db import init_db
from backend.app.frontend import mount_frontend
from backend.app.providers.base import (
    LLMProvider, ProviderTimeoutError, ProviderUnavailableError,
    ModelUnavailableError, ProviderResponseError, ProviderOutputLimitError,
)
from backend.app.providers.mock import MockLLM
from backend.app.providers.ollama import OllamaProvider
from backend.app.services.answer_evaluation_service import AnswerEvaluationService
from backend.app.services.interview_service import InterviewService
from backend.app.services.candidate_service import CandidateService
from backend.app.services.cv_analysis_service import CVAnalysisService
from backend.app.services.question_bank_service import QuestionBankService
from backend.app.services.report_service import ReportService
from backend.app.services.session_service import InterviewSessionService


def error_response(status: int, code: str, message: str):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(provider: LLMProvider | None = None, voice=None) -> FastAPI:
    init_db()
    question_bank = QuestionBankService()
    question_bank.seed_if_empty()

    app = FastAPI(title=settings.app_name, version=settings.version)
    app.state.provider = provider if provider is not None else (
        OllamaProvider(settings) if settings.provider == "ollama" else MockLLM()
    )
    app.include_router(router)
    app.include_router(interview_router, prefix="/api/v1/interviews")
    app.include_router(interview_router, prefix="/api/v1/sessions")
    for prefix in ("/api/v1/cv", "/api/v1/cvs", "/api/v1/cv-analysis", "/api/v1/cv-analyses"):
        app.include_router(cv_router, prefix=prefix)
    for prefix in ("/api/v1/evaluations", "/api/v1/evaluation", "/api/v1/answer-evaluations", "/api/v1/answer-evaluation", "/api/v1/answers-evaluation"):
        app.include_router(evaluation_router, prefix=prefix)
    for prefix in ("/api/v1/reports", "/api/v1/report"):
        app.include_router(report_router, prefix=prefix)
    for prefix in ("/api/v1/interviews", "/api/v1/sessions"):
        app.include_router(evaluation_router, prefix=prefix)
        app.include_router(report_router, prefix=prefix)

    app.state.voice_enabled = settings.voice_enabled
    app.state.voice = voice
    if settings.voice_enabled:
        from backend.app.voice.routes import router as voice_router
        app.include_router(voice_router)
    app.state.services = {
        "candidates": CandidateService(),
        "interview": InterviewService(),
        "sessions": InterviewSessionService(),
        "questions": question_bank,
        "cv_analysis": CVAnalysisService(),
        "answer_evaluation": AnswerEvaluationService(),
        "reports": ReportService(),
    }

    @app.middleware("http")
    async def upload_limit(request: Request, call_next):
        if request.url.path.startswith(("/api/v1/documents", "/api/v1/cv", "/api/v1/cvs", "/api/v1/cv-analysis", "/api/v1/cv-analyses")) and request.method in {"POST", "PUT"} and "multipart" in request.headers.get("content-type", ""):
            length = request.headers.get("content-length", "")
            if not length.isdecimal():
                return error_response(411, "length_required", "Document uploads require Content-Length.")
            if int(length) > 10 * 1024 * 1024 + 65536:
                return error_response(413, "file_size", "Document upload exceeds 10 MiB plus metadata allowance.")
        return await call_next(request)

    @app.exception_handler(AdmissionError)
    async def admission_error(request: Request, exc: AdmissionError):
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        if request.url.path.startswith("/api/v1/voice"):
            return error_response(422, "voice_validation", "Invalid voice request. Check documented field and size limits.")
        return error_response(422, "validation_error", "Send a JSON object with only 'message': a non-empty string of at most 4000 characters.")

    @app.exception_handler(ModelUnavailableError)
    async def model_unavailable(request: Request, exc: ModelUnavailableError):
        return error_response(503, "model_unavailable", "The configured local model is not installed or is not supported locally.")

    @app.exception_handler(ProviderOutputLimitError)
    async def output_limit(request: Request, exc: ProviderOutputLimitError):
        return error_response(502, "provider_output_limit", "The local model reached its output limit before completing a response.")

    @app.exception_handler(ProviderResponseError)
    async def invalid_response(request: Request, exc: ProviderResponseError):
        return error_response(502, "provider_response_error", "The local LLM provider returned an invalid response.")

    @app.exception_handler(ProviderUnavailableError)
    async def unavailable(request: Request, exc: ProviderUnavailableError):
        return error_response(503, "provider_unavailable", "The local LLM provider is unavailable.")

    @app.exception_handler(ProviderTimeoutError)
    async def timeout(request: Request, exc: ProviderTimeoutError):
        return error_response(504, "provider_timeout", "The local LLM provider timed out.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response(exc.status_code, "http_error", "The requested resource or method is unavailable.")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        return error_response(500, "internal_error", "An internal error occurred.")

    mount_frontend(app)
    return app


app = create_app()
