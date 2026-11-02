"""Shared Pydantic models for requests, responses, and agent state."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------- Resume / Profile ----------


class Education(BaseModel):
    institution: str = ""
    degree: str = ""
    year: str = ""


class StudentProfile(BaseModel):
    name: str = ""
    email: str = ""
    skills: list[str] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class ResumeAnalysisResponse(BaseModel):
    profile: StudentProfile
    summary: str


# ---------- Job search / matching ----------


class JobListing(BaseModel):
    id: str
    title: str
    company: str
    location: str = ""
    description: str
    url: str = ""
    source: str = "local"  # "local" | "web" (via MCP)


class JobSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=5, ge=1, le=20)
    job_type: Literal["any", "internship", "full-time"] = "any"


class JobSearchResponse(BaseModel):
    jobs: list[JobListing]
    tool_used: str


class JobMatchRequest(BaseModel):
    profile: StudentProfile
    job: JobListing


class JobMatchResponse(BaseModel):
    match_score: int  # 0-100
    matched_skills: list[str]
    missing_skills: list[str]
    rationale: str


# ---------- Skill gap / learning ----------


class SkillGapRequest(BaseModel):
    profile: StudentProfile
    job: JobListing


class SkillGapResponse(BaseModel):
    missing_skills: list[str]
    priority_order: list[str]
    explanation: str


class LearningRequest(BaseModel):
    missing_skills: list[str] = Field(max_length=30)
    context: str = Field(default="", max_length=2000)


class LearningResource(BaseModel):
    skill: str
    resources: list[str]
    estimated_weeks: int


class LearningRoadmapResponse(BaseModel):
    roadmap: list[LearningResource]
    total_estimated_weeks: int


# ---------- Interview ----------


class InterviewGenerateRequest(BaseModel):
    role: str = Field(min_length=1, max_length=200)
    profile: StudentProfile | None = None
    num_questions: int = Field(default=5, ge=1, le=10)


class InterviewQuestion(BaseModel):
    question: str
    category: str  # "technical" | "behavioral" | "system_design"
    answer: str = ""


class InterviewGenerateResponse(BaseModel):
    questions: list[InterviewQuestion]


class InterviewEvaluateRequest(BaseModel):
    question: str = Field(max_length=2000)
    answer: str = Field(max_length=10_000)
    role: str = Field(default="", max_length=200)


class InterviewEvaluateResponse(BaseModel):
    score: int  # 0-10
    feedback: str
    improved_answer_tips: list[str]


# ---------- GitHub (MCP) ----------


class GitHubAnalysisRequest(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9-]{1,39}$")


class GitHubAnalysisResponse(BaseModel):
    username: str
    public_repos: int
    top_languages: list[str]
    notable_repos: list[str]
    summary: str


# ---------- RAG ----------


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    k: int = Field(default=4, ge=1, le=10)
    doc_type: str | None = None


class RagSearchResult(BaseModel):
    content: str
    source: str
    doc_type: str
    score: float


class RagSearchResponse(BaseModel):
    results: list[RagSearchResult]


# ---------- Orchestrator / chat ----------


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    profile: StudentProfile | None = None
    session_id: str = Field(default="default", max_length=100)


class AgentStep(BaseModel):
    agent: str
    action: str
    detail: str = ""


class ChatResponse(BaseModel):
    reply: str
    steps: list[AgentStep]


class WorkflowRequest(BaseModel):
    profile: StudentProfile
    job_query: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=100)


class WorkflowResponse(BaseModel):
    steps: list[AgentStep]
    job: JobListing | None = None
    match: JobMatchResponse | None = None
    skill_gap: SkillGapResponse | None = None
    roadmap: LearningRoadmapResponse | None = None
    interview_questions: list[InterviewQuestion] = Field(default_factory=list)


class HistorySnapshot(BaseModel):
    job: JobListing
    match: JobMatchResponse | None = None
    skill_gap: SkillGapResponse | None = None
    roadmap: LearningRoadmapResponse | None = None
    interview_questions: list[InterviewQuestion] = Field(default_factory=list)
