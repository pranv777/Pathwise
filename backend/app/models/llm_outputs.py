"""Plain schemas handed to the LLM via with_structured_output()."""

from pydantic import BaseModel, Field


class EducationOut(BaseModel):
    institution: str
    degree: str
    year: str


class ResumeOut(BaseModel):
    name: str
    email: str
    skills: list[str] = Field(description="Normalized, deduplicated skill names")
    education: list[EducationOut]
    projects: list[str] = Field(description="One line per project")
    experience: list[str] = Field(description="One line per role or internship")
    certifications: list[str]


class JobMatchOut(BaseModel):
    match_score: int = Field(description="Integer from 0 to 100")
    matched_skills: list[str]
    missing_skills: list[str]
    rationale: str = Field(description="2-3 sentences referencing specifics")


class SkillGapOut(BaseModel):
    missing_skills: list[str]
    priority_order: list[str] = Field(description="Same skills, most important first")
    explanation: str


class RoadmapItemOut(BaseModel):
    skill: str
    resources: list[str]
    estimated_weeks: int


class RoadmapOut(BaseModel):
    roadmap: list[RoadmapItemOut]
    total_estimated_weeks: int


class InterviewQuestionOut(BaseModel):
    question: str
    category: str = Field(description="One of: technical, behavioral, system_design")
    answer: str = Field(description="Strong model answer in markdown")


class InterviewSetOut(BaseModel):
    questions: list[InterviewQuestionOut]


class EvaluationOut(BaseModel):
    score: int = Field(description="Integer from 0 to 10")
    feedback: str
    improved_answer_tips: list[str]


class RouteOut(BaseModel):
    route: str = Field(
        description="One of: job_search, github_analysis, skill_gap, learning, "
        "interview, rag_answer"
    )
    reasoning: str
    job_query: str = Field(description="Empty string if not job_search")
    github_username: str = Field(description="Empty string if not github_analysis")
    role: str = Field(description="Empty string unless skill_gap or interview")
    skills: list[str] = Field(description="Empty list unless learning")
