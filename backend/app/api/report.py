from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from backend.app.core.errors import AdmissionError
from backend.app.services.report_service import ReportService


def get_report_service(request: Request) -> ReportService:
    return request.app.state.services["reports"]


router = APIRouter()


@router.get("/{session_id}")
@router.get("/{session_id}/pdf")
@router.get("/{session_id}/report")
async def get_session_report(session_id: str, service: ReportService = Depends(get_report_service)):
    pdf_bytes, filename = service.generate(session_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="%s"' % filename},
    )
