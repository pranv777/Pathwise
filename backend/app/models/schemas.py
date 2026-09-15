"""Shared Pydantic models for requests, responses, and agent state."""
from __future__ import annotations
from typing import Optional
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
    raw_text: str = ""


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
    query: str
    location: Optional[str] = None
    limit: int = 5


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
    missing_skills: list[str]
    context: str = ""


class LearningResource(BaseModel):
    skill: str
    resources: list[str]
    estimated_weeks: int


class LearningRoadmapResponse(BaseModel):
    roadmap: list[LearningResource]
    total_estimated_weeks: int


# ---------- Interview ----------

class InterviewGenerateRequest(BaseModel):
    role: str
    profile: Optional[StudentProfile] = None
    num_questions: int = 5


class InterviewQuestion(BaseModel):
    question: str
    category: str  # "technical" | "behavioral" | "system_design"
    answer: str = ""


class InterviewGenerateResponse(BaseModel):
    questions: list[InterviewQuestion]


class InterviewEvaluateRequest(BaseModel):
    question: str
    answer: str
    role: str = ""


class InterviewEvaluateResponse(BaseModel):
    score: int  # 0-10
    feedback: str
    improved_answer_tips: list[str]


# ---------- GitHub (MCP) ----------

class GitHubAnalysisRequest(BaseModel):
    username: str


class GitHubAnalysisResponse(BaseModel):
    username: str
    public_repos: int
    top_languages: list[str]
    notable_repos: list[str]
    summary: str


# ---------- RAG ----------

class RagIngestRequest(BaseModel):
    text: str
    source: str
    doc_type: str = "career_guide"  # resume | job_description | interview_prep | learning_resource | career_guide


class RagSearchRequest(BaseModel):
    query: str
    k: int = 4
    doc_type: Optional[str] = None


class RagSearchResult(BaseModel):
    content: str
    source: str
    doc_type: str
    score: float


class RagSearchResponse(BaseModel):
    results: list[RagSearchResult]


# ---------- Orchestrator / chat ----------

class ChatRequest(BaseModel):
    message: str
    profile: Optional[StudentProfile] = None
    session_id: str = "default"


class AgentStep(BaseModel):
    agent: str
    action: str
    detail: str = ""


class ChatResponse(BaseModel):
    reply: str
    steps: list[AgentStep]


class WorkflowRequest(BaseModel):
    profile: StudentProfile
    job_query: str
    location: Optional[str] = None


class WorkflowResponse(BaseModel):
    steps: list[AgentStep]
    job: Optional[JobListing] = None
    match: Optional[JobMatchResponse] = None
    skill_gap: Optional[SkillGapResponse] = None
    roadmap: Optional[LearningRoadmapResponse] = None
    interview_questions: list[InterviewQuestion] = Field(default_factory=list)
