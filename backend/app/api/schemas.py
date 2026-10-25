from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(strict=True, min_length=1, max_length=4000)


class Source(BaseModel):
    document: str
    page: int | None = Field(default=None, ge=1)


class ChatResponse(BaseModel):
    answer: str
    provider: str
    model: str
    sources: list[Source] = Field(default_factory=list)
    documentation_sufficient: bool = False


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class StatusResponse(BaseModel):
    status: Literal["ready", "unavailable"]
    provider: str
    model: str
    mock: bool
    rag_enabled: bool = False
    local_only: bool = True

from typing import Literal


class InterviewQuestion(BaseModel):
    id: str
    category: str
    prompt: str
    difficulty: str


class CreateInterviewSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    candidate_id: str | None = Field(default=None, min_length=1, max_length=128)
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=254)
    mode: Literal["quick", "standard", "complete"] = "standard"


class InterviewSessionResponse(BaseModel):
    session_id: str
    candidate_id: str
    mode: str
    question_count: int
    status: str
    current_question_id: str | None = None
    current_position: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str
    updated_at: str


class StartInterviewResponse(BaseModel):
    session: InterviewSessionResponse
    current_question: InterviewQuestion | None = None
    total_questions: int


class CurrentQuestionResponse(BaseModel):
    session_id: str
    status: str
    position: int
    total_questions: int
    current_question: InterviewQuestion | None = None


class SubmitAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question_id: str = Field(min_length=1, max_length=128)
    answer: str = Field(min_length=1, max_length=4000)


class AnswerResponse(BaseModel):
    session_id: str
    question_id: str
    answer_id: str
    status: str
    next_question: InterviewQuestion | None = None
    completed_available: bool = True


class InterviewHistoryItem(BaseModel):
    question_id: str
    category: str
    prompt: str
    answer: str
    created_at: str


class InterviewHistoryResponse(BaseModel):
    session_id: str
    status: str
    items: list[InterviewHistoryItem] = Field(default_factory=list)


class CompleteInterviewResponse(BaseModel):
    session_id: str
    status: str
    completed_at: str | None = None


class FollowupResponse(BaseModel):
    session_id: str
    should_ask: bool
    followup_question: InterviewQuestion | None = None
    message: str | None = None


class LLMFollowupOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    should_ask: bool = False
    followup_question: str = ""
    rationale: str = ""


from typing import Literal


class CVEvidenceRequirement(BaseModel):
    model_config = ConfigDict(extra="ignore")
    requirement: str
    category: Literal["mandatory", "recommended"] = "recommended"
    status: Literal["evidence_found", "evidence_insufficient", "not_demonstrated"]
    evidence: str = ""
    notes: str = ""


class CVAnalysisLLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    professional_summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    missing_or_unclear_evidence: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    requirement_classification: list[CVEvidenceRequirement] = Field(default_factory=list)
    wording_improvements: list[str] = Field(default_factory=list)
    feedback: str = ""


class CVUploadResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    analysis_id: str | None = None
    candidate_id: str
    file_name: str
    status: str
    file_size: int | None = None
    created_at: str


class CVStatusResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    analysis_id: str | None = None
    candidate_id: str | None = None
    status: str
    analyzed_at: str | None = None
    analysis_date: str | None = None
    error: dict | None = None


class CVAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    analysis_id: str | None = None
    candidate_id: str | None = None
    file_name: str | None = None
    status: str
    created_at: str | None = None
    updated_at: str | None = None
    analyzed_at: str | None = None
    analysis_date: str | None = None
from typing import Literal


class EvaluationCriterion(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(min_length=1, max_length=120)
    score: int | None = Field(default=None, ge=0, le=100)
    status: Literal["applicable", "not_applicable", "insufficient_evidence"] = "applicable"
    explanation: str = ""


class StressManagementFeedback(BaseModel):
    model_config = ConfigDict(extra="ignore")
    addresses: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class TechnicalAccuracyFeedback(BaseModel):
    model_config = ConfigDict(extra="ignore")
    classification: Literal[
        "correct", "partially_correct", "unsupported", "incorrect",
        "insufficient_evidence", "not_applicable",
    ] = "not_applicable"
    claims: list[dict] = Field(default_factory=list)


class AnswerEvaluationLLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    overall_score: int = Field(ge=0, le=100)
    criteria: list[EvaluationCriterion] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    revised_answer: str = ""
    practice_tip: str = ""
    technical_accuracy: TechnicalAccuracyFeedback | None = None
    stress_management: StressManagementFeedback | None = None
    feedback: str = ""


class EvaluateAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    question_id: str | None = Field(default=None, min_length=1, max_length=128)
    answer_id: str | None = Field(default=None, min_length=1, max_length=128)
    question_prompt: str | None = Field(default=None, min_length=1, max_length=4000)
    answer: str | None = Field(default=None, min_length=1, max_length=4000)
    candidate_answer: str | None = Field(default=None, min_length=1, max_length=4000)
    force: bool = False


class ImprovedAnswerResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    evaluation_id: str | None = None
    answer_id: str | None = None
    revised_answer: str = ""
    improved_answer: str = ""
    practice_tip: str | None = None


class AnswerEvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    evaluation_id: str | None = None
    session_id: str | None = None
    answer_id: str | None = None
    question_id: str | None = None
    candidate_id: str | None = None
    question_prompt: str | None = None
    original_answer: str | None = None
    overall_score: int | None = None
    score: int | None = None
    criteria: list | None = None
    scores: dict | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    areas_for_improvement: list[str] | None = None
    recommendations: list[str] | None = None
    revised_answer: str | None = None
    improved_answer: str | None = None
    practice_tip: str | None = None
    technical_accuracy: dict | None = None
    stress_management: dict | None = None
    disclaimer: str | None = None
    status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    evaluation: dict | None = None
    result: dict | None = None
    analysis: dict | None = None


class AnswerEvaluationListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    session_id: str | None = None
    items: list[AnswerEvaluationResponse] = Field(default_factory=list)
    evaluations: list[AnswerEvaluationResponse] = Field(default_factory=list)


class CandidateProfileRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    full_name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=254)
    academic_background: str | None = Field(default=None, max_length=8000)
    professional_background: str | None = Field(default=None, max_length=8000)


class CandidateProfileResponse(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: str
    full_name: str
    email: str | None = None
    academic_profile: dict = Field(default_factory=dict)
    created_at: str

