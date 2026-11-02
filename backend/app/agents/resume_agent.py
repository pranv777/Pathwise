"""Resume Agent — extracts a structured StudentProfile (skills, education,
projects, experience, certifications) from raw resume text using Gemini,
grounded with a JSON-only prompt so the output is reliably parseable.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.llm_outputs import ResumeOut
from app.models.schemas import Education, StudentProfile
from app.utils.structured import invoke_json

SYSTEM_PROMPT = """You are a resume-parsing specialist for a college placement assistant.
Extract a structured profile from the resume text. Respond with ONLY valid JSON
matching this exact schema, no markdown fences, no commentary:

{
  "name": "string",
  "email": "string",
  "skills": ["string", ...],
  "education": [{"institution": "string", "degree": "string", "year": "string"}],
  "projects": ["one-line description per project", ...],
  "experience": ["one-line description per role/internship", ...],
  "certifications": ["string", ...]
}

Rules:
- "skills" should be normalized technical skill names (e.g. "React", "PostgreSQL", "Docker"), deduplicated.
- Infer skills mentioned inside project/experience bullets even if not in a dedicated skills section.
- If a field is unknown, use an empty string or empty list. Never fabricate details not implied by the text.
"""


def run_resume_agent(resume_text: str) -> StudentProfile:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"RESUME TEXT:\n\n{resume_text[:12000]}"),
    ]
    data = invoke_json(ResumeOut, messages, temperature=0.1)
    return StudentProfile(
        name=data.name,
        email=data.email,
        skills=data.skills,
        education=[Education(**e.model_dump()) for e in data.education],
        projects=data.projects,
        experience=data.experience,
        certifications=data.certifications,
    )
