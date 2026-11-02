"""Interview Agent — generates role-specific interview questions (grounded
in retrieved interview-prep material) and evaluates candidate answers.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.llm_outputs import EvaluationOut, InterviewSetOut
from app.models.schemas import (
    InterviewEvaluateResponse,
    InterviewGenerateResponse,
    InterviewQuestion,
    StudentProfile,
)
from app.rag.vector_store import search
from app.utils.structured import invoke_json

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
- Each "answer" should be genuinely useful and formatted in markdown: use **bold**
  for key terms, bullet points for multi-part explanations, and short paragraphs.
  For behavioral questions, format the STAR structure with **Situation**, **Task**,
  **Action**, **Result** as bold labels. Long enough to demonstrate a strong answer
  (3-6 sentences or bullets for technical/system_design) — not a one-line summary.

IMPORTANT: Output must be strictly valid JSON. Within any string value, encode
line breaks as the two characters \\n (backslash-n), never as a literal newline.
Escape any double-quote characters that appear inside a string value as \\".
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


def run_interview_generate(
    role: str, profile: StudentProfile | None, num_questions: int = 5
) -> InterviewGenerateResponse:
    docs = search(f"{role} interview questions", k=4, doc_type="interview_prep")
    retrieved_text = "\n---\n".join(d.page_content for d, _ in docs)

    profile_line = (
        f"CANDIDATE SKILLS: {', '.join(profile.skills)}\nCANDIDATE PROJECTS: {'; '.join(profile.projects)}"
        if profile
        else "CANDIDATE PROFILE: not provided"
    )
    user_content = f"""ROLE: {role}
NUMBER OF QUESTIONS: {num_questions}
{profile_line}

RETRIEVED INTERVIEW PREP MATERIAL:
{retrieved_text or "none available"}
"""
    messages = [
        SystemMessage(content=GENERATE_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]
    data = invoke_json(InterviewSetOut, messages, temperature=0.5)
    questions = [
        InterviewQuestion(
            question=q.question,
            category=q.category
            if q.category in {"technical", "behavioral", "system_design"}
            else "technical",
            answer=q.answer,
        )
        for q in data.questions
    ]
    return InterviewGenerateResponse(
        questions=questions[:num_questions] if num_questions else questions
    )


def run_interview_evaluate(
    question: str, answer: str, role: str = ""
) -> InterviewEvaluateResponse:
    user_content = f"""ROLE: {role or "not specified"}
QUESTION: {question}
CANDIDATE ANSWER: {answer}
"""
    messages = [
        SystemMessage(content=EVALUATE_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]
    data = invoke_json(EvaluationOut, messages, temperature=0.2)
    return InterviewEvaluateResponse(
        score=max(0, min(10, data.score)),
        feedback=data.feedback,
        improved_answer_tips=data.improved_answer_tips,
    )
