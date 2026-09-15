"""Interview Agent — generates role-specific interview questions (grounded
in retrieved interview-prep material) and evaluates candidate answers.
"""
from __future__ import annotations
from langchain_core.messages import HumanMessage, SystemMessage
from app.models.schemas import (
    StudentProfile,
    InterviewQuestion,
    InterviewGenerateResponse,
    InterviewEvaluateResponse,
)
from app.utils.llm import get_llm, extract_json
from app.rag.vector_store import search

GENERATE_SYSTEM_PROMPT = """You are an Interview Agent for a college placement assistant.
Generate role-specific interview questions WITH strong model answers. Respond with ONLY
valid JSON (no markdown fences):

{
  "questions": [
    {
      "question": "string",
      "category": "technical|behavioral|system_design",
      "answer": "a strong, concrete model answer a well-prepared candidate would give"
    }
  ]
}

Rules:
- Mix categories realistically for the role (mostly technical for engineering roles, with
  2-3 behavioral questions).
- Ground technical questions in the retrieved reference material and, if provided, the
  candidate's own listed skills/projects where relevant.
- Each "answer" should be genuinely useful: specific, structured, and long enough to
  actually demonstrate a good answer (3-6 sentences for technical/system_design, or a
  STAR-format answer for behavioral) — not a one-line summary.
"""

EVALUATE_SYSTEM_PROMPT = """You are an Interview Agent evaluating a candidate's spoken/written
answer to an interview question. Respond with ONLY valid JSON (no markdown fences):

{
  "score": <integer 0-10>,
  "feedback": "2-4 sentences: what was strong, what was missing",
  "improved_answer_tips": ["concrete tip 1", "concrete tip 2"]
}

Be constructive but honest — do not inflate scores for vague or incomplete answers.
"""


def run_interview_generate(role: str, profile: StudentProfile | None, num_questions: int = 5) -> InterviewGenerateResponse:
    docs = search(f"{role} interview questions", k=4, doc_type="interview_prep")
    retrieved_text = "\n---\n".join(d.page_content for d, _ in docs)

    llm = get_llm(temperature=0.5)
    profile_line = (
        f"CANDIDATE SKILLS: {', '.join(profile.skills)}\nCANDIDATE PROJECTS: {'; '.join(profile.projects)}"
        if profile
        else "CANDIDATE PROFILE: not provided"
    )
    user_content = f"""ROLE: {role}
NUMBER OF QUESTIONS: {num_questions}
{profile_line}

RETRIEVED INTERVIEW PREP MATERIAL:
{retrieved_text or 'none available'}
"""
    messages = [SystemMessage(content=GENERATE_SYSTEM_PROMPT), HumanMessage(content=user_content)]
    response = llm.invoke(messages)
    data = extract_json(response.content)

    questions = [
        InterviewQuestion(question=q.get("question", ""), category=q.get("category", "technical"), answer=q.get("answer", ""),)
        for q in data.get("questions", []) or []
    ]
    return InterviewGenerateResponse(questions=questions[:num_questions] if num_questions else questions)


def run_interview_evaluate(question: str, answer: str, role: str = "") -> InterviewEvaluateResponse:
    llm = get_llm(temperature=0.2)
    user_content = f"""ROLE: {role or 'not specified'}
QUESTION: {question}
CANDIDATE ANSWER: {answer}
"""
    messages = [SystemMessage(content=EVALUATE_SYSTEM_PROMPT), HumanMessage(content=user_content)]
    response = llm.invoke(messages)
    data = extract_json(response.content)

    return InterviewEvaluateResponse(
        score=int(data.get("score", 0)),
        feedback=data.get("feedback", ""),
        improved_answer_tips=data.get("improved_answer_tips", []) or [],
    )
