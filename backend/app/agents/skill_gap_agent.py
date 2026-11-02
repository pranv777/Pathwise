"""Skill Gap Agent — takes a student profile and target job, identifies
missing skills, and orders them by priority (what to learn first to
maximize interview readiness). Separate from Job Matching Agent so it can
be called standalone once a job is already selected.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.llm_outputs import SkillGapOut
from app.models.schemas import JobListing, SkillGapResponse, StudentProfile
from app.utils.structured import invoke_json

SYSTEM_PROMPT = """You are a Skill Gap Agent for a college placement assistant.
Given a student's current skills and a target job description, respond with
ONLY valid JSON (no markdown fences) matching:

{
  "missing_skills": ["skill", ...],
  "priority_order": ["skill", ...],
  "explanation": "1-3 sentences on why these are prioritized this way"
}

"priority_order" must be a re-ordering of "missing_skills" (same set), ranked from
highest-impact/most-frequently-required first to nice-to-have last.
"""


def run_skill_gap_agent(profile: StudentProfile, job: JobListing) -> SkillGapResponse:
    user_content = f"""STUDENT SKILLS: {", ".join(profile.skills) or "none listed"}
JOB TITLE: {job.title}
JOB DESCRIPTION: {job.description}
"""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]
    data = invoke_json(SkillGapOut, messages, temperature=0.2)
    return SkillGapResponse(
        missing_skills=data.missing_skills,
        priority_order=data.priority_order or data.missing_skills,
        explanation=data.explanation,
    )
