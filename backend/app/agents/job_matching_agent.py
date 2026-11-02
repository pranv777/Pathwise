"""Job Matching Agent — compares a student profile against a job
description and produces a 0-100 match score with matched/missing skills.
Retrieves similar job-description context from RAG to calibrate what
"typical requirements" look like for that role family.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.llm_outputs import JobMatchOut
from app.models.schemas import JobListing, JobMatchResponse, StudentProfile
from app.rag.vector_store import search
from app.utils.structured import invoke_json

SYSTEM_PROMPT = """You are a Job Matching Agent for a college placement assistant.
Given a student's profile and a job description, produce ONLY valid JSON (no
markdown fences) matching this schema:

{
  "match_score": <integer 0-100>,
  "matched_skills": ["skills the student has that the job requires"],
  "missing_skills": ["skills the job requires that the student lacks"],
  "rationale": "2-3 sentence explanation of the score, referencing specifics"
}

Score generously for adjacent/transferable skills (e.g. Flask experience partially
covers a FastAPI requirement) but do not inflate the score past what the evidence supports.
"""


def run_job_matching_agent(
    profile: StudentProfile, job: JobListing
) -> JobMatchResponse:
    context_docs = search(job.description, k=3, doc_type="job_description")
    context_text = "\n---\n".join(d.page_content for d, _ in context_docs)

    user_content = f"""STUDENT SKILLS: {", ".join(profile.skills) or "none listed"}
STUDENT PROJECTS: {"; ".join(profile.projects) or "none listed"}
STUDENT EXPERIENCE: {"; ".join(profile.experience) or "none listed"}

JOB TITLE: {job.title}
JOB DESCRIPTION: {job.description}

REFERENCE CONTEXT (similar role requirements, for calibration only):
{context_text or "none available"}
"""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]
    data = invoke_json(JobMatchOut, messages, temperature=0.2)
    return JobMatchResponse(
        match_score=max(0, min(100, data.match_score)),
        matched_skills=data.matched_skills,
        missing_skills=data.missing_skills,
        rationale=data.rationale,
    )
