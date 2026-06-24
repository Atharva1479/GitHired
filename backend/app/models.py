from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

Source = Literal["LinkedIn", "Naukri", "Referral", "CompanySite", "Other"]
# Kept as a Literal for backward-compat (used in query-param annotations).
Status = Literal["Applied", "Screening", "Interview", "Offer", "Rejected", "Ghosted"]


class ApplicationStatus(str, Enum):
    applied = "Applied"
    screening = "Screening"
    interview = "Interview"
    offer = "Offer"
    rejected = "Rejected"
    ghosted = "Ghosted"


ConnectionStatus = Literal[
    "Request Sent", "Accepted", "Msg Sent", "Replied", "Referred", "Dropped"
]
Outcome = Literal["Referred", "NoResponse", "Declined"]

NudgeType = Literal[
    "application_followup",
    "application_stale",
    "application_interview_stale",
    "apply_more",
    "referral_check",
    "referral_unaccepted",
    "referral_ask",
    "referral_followup",
]
NudgeReferenceType = Literal["application", "referral", "user"]
NudgeSeverity = Literal["info", "due", "overdue"]

DraftEntityType = Literal["application", "referral"]
DraftType = Literal[
    "followup_email", "cover_letter", "referral_ask", "referral_followup", "weekly_summary"
]


class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=200)
    source: Source
    applied_date: date
    jd_url: HttpUrl | None = None
    jd_text: str | None = None
    contact_name: str | None = None
    contact_linkedin: HttpUrl | None = None
    fit_score: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = None
    salary_discussed: str | None = None


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str | None = Field(default=None, min_length=1, max_length=200)
    role: str | None = Field(default=None, min_length=1, max_length=200)
    source: Source | None = None
    applied_date: date | None = None
    status: ApplicationStatus | None = None
    notes: str | None = None
    fit_score: int | None = Field(default=None, ge=0, le=100)
    salary_discussed: str | None = None
    contact_name: str | None = None
    contact_linkedin: HttpUrl | None = None
    jd_url: HttpUrl | None = None
    jd_text: str | None = None


class ApplicationOut(BaseModel):
    id: int
    company: str
    role: str
    source: Source
    status: ApplicationStatus
    applied_date: date
    last_updated: datetime
    jd_url: str | None
    salary_discussed: str | None
    contact_name: str | None
    contact_linkedin: str | None
    fit_score: int | None
    notes: str | None
    follow_up_count: int
    last_followed_up_at: datetime | None
    created_at: datetime
    jd_text: str | None = None
    jd_file_name: str | None = None
    resume_file_name: str | None = None
    cover_letter_file_name: str | None = None


class ReferralCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    target_role: str = Field(min_length=1, max_length=200)
    connection_sent_date: date
    role_at_company: str | None = None
    linkedin_url: HttpUrl | None = None
    mutual_context: str | None = None
    notes: str | None = None


class ReferralUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    company: str | None = None
    target_role: str | None = None
    role_at_company: str | None = None
    linkedin_url: HttpUrl | None = None
    mutual_context: str | None = None
    connection_status: ConnectionStatus | None = None
    referral_msg_sent_date: date | None = None
    reply_date: date | None = None
    outcome: Outcome | None = None
    notes: str | None = None


class NudgeOut(BaseModel):
    id: int
    type: NudgeType
    reference_type: NudgeReferenceType
    reference_id: int | None
    severity: NudgeSeverity
    message: str
    fired_on_date: date
    read_at: datetime | None
    acted_at: datetime | None
    snoozed_until: date | None
    created_at: datetime


class SnoozeBody(BaseModel):
    days: int = Field(ge=1, le=30)


class DraftOut(BaseModel):
    id: int
    entity_type: DraftEntityType
    entity_id: int
    draft_type: DraftType
    content: str
    model: str
    cached: bool = False
    fallback: bool = False
    created_at: datetime


class DraftRequest(BaseModel):
    regenerate: bool = False


class CoverLetterRequest(BaseModel):
    regenerate: bool = False
    tone: str = "professional"  # "professional" | "concise" | "enthusiastic"


class ReferralOut(BaseModel):
    id: int
    name: str
    company: str
    target_role: str
    role_at_company: str | None
    linkedin_url: str | None
    mutual_context: str | None
    connection_sent_date: date
    connection_status: ConnectionStatus
    referral_msg_sent_date: date | None
    reply_date: date | None
    outcome: Outcome | None
    notes: str | None
    last_updated: datetime
    created_at: datetime


# ─────────────────────────  M10 — Study tracker  ─────────────────────────

StudyKind = Literal["learn", "revise"]
StudyStatus = Literal["todo", "in_progress", "done", "mastered"]


class StudySectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    icon: str | None = Field(default=None, max_length=40)
    position: int | None = Field(default=None, ge=0)


class StudySectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    icon: str | None = Field(default=None, max_length=40)
    position: int | None = Field(default=None, ge=0)


class StudySectionOut(BaseModel):
    id: int
    name: str
    icon: str | None
    position: int
    created_at: datetime
    last_updated: datetime


class StudySubsectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    position: int | None = Field(default=None, ge=0)


class StudySubsectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    position: int | None = Field(default=None, ge=0)
    section_id: int | None = None


class StudySubsectionOut(BaseModel):
    id: int
    section_id: int
    name: str
    position: int
    created_at: datetime
    last_updated: datetime


class StudyTopicCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    notes: str | None = None
    kind: StudyKind = "learn"
    tags: list[str] = Field(default_factory=list)
    position: int | None = Field(default=None, ge=0)


class StudyTopicUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=300)
    notes: str | None = None
    kind: StudyKind | None = None
    status: StudyStatus | None = None
    tags: list[str] | None = None
    position: int | None = Field(default=None, ge=0)
    subsection_id: int | None = None


class StudyTopicOut(BaseModel):
    id: int
    subsection_id: int
    title: str
    notes: str | None
    kind: StudyKind
    status: StudyStatus
    tags: list[str]
    revision_count: int
    last_revised_at: datetime | None
    position: int
    created_at: datetime
    last_updated: datetime


class StudyPlanSubsection(StudySubsectionOut):
    topics: list[StudyTopicOut] = Field(default_factory=list)


class StudyPlanSection(StudySectionOut):
    subsections: list[StudyPlanSubsection] = Field(default_factory=list)


class StudyPlan(BaseModel):
    """Full nested tree returned by GET /api/study/plan."""

    sections: list[StudyPlanSection] = Field(default_factory=list)


class StudyReviseResponse(BaseModel):
    topic: StudyTopicOut
    revision_count: int
    new_status: StudyStatus


class StudyProgress(BaseModel):
    total_topics: int
    todo: int
    in_progress: int
    done: int
    mastered: int
    revisions_this_week: int
    due_for_review: int


# ── M10 Phase 4 — AI generation previews ────────────────────────────


class StudyAITopicPreview(BaseModel):
    title: str
    notes: str | None = None


class StudyAISubsectionPreview(BaseModel):
    name: str
    topics: list[StudyAITopicPreview] = Field(default_factory=list)


class StudyAISectionPreview(BaseModel):
    name: str
    subsections: list[StudyAISubsectionPreview] = Field(default_factory=list)


class StudyGenerateRequest(BaseModel):
    role: str = Field(max_length=200)
    target_companies: list[str] | None = None
    existing_sections: list[str] | None = None


class StudyGenerateResponse(BaseModel):
    sections: list[StudyAISectionPreview]


class StudyGenerateTopicsRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=30)
    hint: str | None = Field(default=None, max_length=500)


class StudyGenerateTopicsResponse(BaseModel):
    topics: list[StudyAITopicPreview]


# ── DSA Progress Tracker ──────────────────────────────────────────────────────

class DsaDifficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class DsaAnalysisOut(BaseModel):
    id: int
    problem_id: int
    user_id: int
    time_complexity: str
    space_complexity: str
    approach_summary: str
    feedback: str
    optimized_solution: str
    optimized_explanation: str
    dry_run_explanation: str
    model: str
    created_at: datetime


class DsaProblemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = Field(min_length=1, max_length=100)
    difficulty: DsaDifficulty = DsaDifficulty.medium
    title: str = Field(min_length=1, max_length=300)
    source_url: str | None = None
    description: str | None = None
    user_solution: str | None = Field(default=None, max_length=10000)


class DsaProblemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str | None = None
    difficulty: DsaDifficulty | None = None
    title: str | None = None
    source_url: str | None = None
    description: str | None = None
    user_solution: str | None = Field(default=None, max_length=10000)


class DsaProblemOut(BaseModel):
    id: int
    user_id: int
    topic: str
    difficulty: DsaDifficulty
    title: str
    source_url: str | None
    description: str | None
    user_solution: str | None
    solved_at: datetime
    created_at: datetime
    last_updated: datetime
    deleted_at: datetime | None = None
    analysis: DsaAnalysisOut | None = None


class DsaTopicStats(BaseModel):
    topic: str
    count: int
    analyzed: int


class DsaStatsOut(BaseModel):
    total_solved: int
    by_difficulty: dict[str, int]
    topics: list[DsaTopicStats]
    analyzed_count: int
    streak_days: int


# ── AI Interview ──────────────────────────────────────────────────────────────

class InterviewSession(BaseModel):
    id: int
    user_id: int
    topic: str
    role: str
    years_exp: str
    duration_min: int
    total_questions: int
    status: str
    created_at: datetime
    ended_at: datetime | None = None
    agent_mode: bool = False
    agent_thread_id: str | None = None


class InterviewTurn(BaseModel):
    id: int
    session_id: int
    question_index: int
    question: str
    user_answer: str
    created_at: datetime
    turn_type: str = "primary"
    parent_turn_id: int | None = None
    followup_depth: int = 0
    agent_decision: str | None = None


# ── LangGraph agent mode request/response models ──────────────────────────────

class StartAgentSessionRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=100)
    years_exp: str = Field(min_length=1, max_length=20)
    difficulty: str = "medium"
    target_turns: int = Field(default=7, ge=3, le=20)
    jd_text: str | None = Field(default=None, max_length=10000)


class StartAgentSessionResponse(BaseModel):
    session_id: int
    thread_id: str
    first_question: str
    topic_clusters: list[str]
    target_turns: int
    agent_mode: bool = True


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(max_length=5000)


class SubmitAnswerResponse(BaseModel):
    next_question: str | None
    question_number: int
    followup_depth: int
    interview_complete: bool
    agent_status: str  # "asking" | "wrapping_up" | "done"


class InterviewQuestionReport(BaseModel):
    id: int
    session_id: int
    question_index: int
    question: str
    user_answer: str
    ideal_answer: str
    score: int
    feedback: str


class InterviewReport(BaseModel):
    id: int
    session_id: int
    overall_score: int
    skill_breakdown: dict[str, Any]
    summary: str
    created_at: datetime


class ResumeOut(BaseModel):
    id: int
    user_id: int
    name: str
    role_tag: str
    file_name: str
    created_at: datetime


class SkillGap(BaseModel):
    skill: str
    frequency: int
    total_jobs: int


class SkillGapResult(BaseModel):
    resume_id: int
    resume_name: str
    role_tag: str
    matched_jobs: int
    gaps: list[SkillGap]


# ──────────────────────────────────────────────────────────────────────────────
# Job Discovery
# ──────────────────────────────────────────────────────────────────────────────

class JobSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    query: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=120)
    remote_only: bool = False
    experience: str | None = None     # 'entry' | 'mid' | 'senior'
    freshness_hours: int = Field(default=24, ge=1, le=168)


class JobSearchOut(BaseModel):
    id: int
    name: str
    query: str
    location: str | None
    remote_only: bool
    experience: str | None
    freshness_hours: int
    is_active: bool
    last_alerted_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobResult(BaseModel):
    """A single discovered job, enriched with freshness/competition data."""
    id: int
    source: str
    external_id: str
    title: str
    company: str
    location: str | None
    description: str | None
    apply_url: str
    posted_at: datetime | None
    employment_type: str | None
    skills: list[str]
    hours_old: float | None
    freshness_score: int
    freshness_label: str
    freshness_color: str
    est_applicants: str
    velocity_label: str | None = None
    bookmark_status: str | None
    # Phase 2 — enriched fields
    is_remote: bool = False
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    tags: list[str] = []
    # Phase 3 — semantic ranking
    semantic_score: float | None = None

    model_config = ConfigDict(from_attributes=True)


class JobSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    location: str | None = None
    remote_only: bool = False
    experience: str | None = None
    freshness_hours: int = Field(default=24, ge=1, le=168)
    page: int = Field(default=1, ge=1, le=10)


class ApplyAndTrackRequest(BaseModel):
    job_cache_id: int
    title: str
    company: str
    apply_url: str
    posted_at: datetime | None = None
    source: str
    external_id: str
    description: str | None = None


class ApplyAndTrackOut(BaseModel):
    bookmark_id: int
    application_id: int
