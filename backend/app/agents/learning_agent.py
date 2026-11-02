"""Learning Recommendation Agent — turns a list of missing skills into a
personalized learning roadmap. Retrieves curated learning-resource
documents from RAG first, and only asks the LLM to synthesize/organize
them into a roadmap (grounded generation instead of hallucinated links).
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.llm_outputs import RoadmapOut
from app.models.schemas import LearningResource, LearningRoadmapResponse
from app.rag.vector_store import search
from app.utils.structured import invoke_json

SYSTEM_PROMPT = """You are a Learning Recommendation Agent for a college placement assistant.
You are given a list of missing skills and retrieved reference material describing
real learning resources. Respond with ONLY valid JSON (no markdown fences):

{
  "roadmap": [
    {"skill": "string", "resources": ["resource 1", "resource 2"], "estimated_weeks": <int>}
  ],
  "total_estimated_weeks": <int>
}

Rules:
- Prefer resources that appear in the retrieved reference material verbatim (by name).
- If no reference material covers a skill, recommend a well-known, real, official resource
  (official docs, a widely-known course/book) rather than inventing one.
- Order the roadmap by learning sequence (foundational skills first).
- total_estimated_weeks should account for some parallel learning, not a naive sum.
"""


def run_learning_agent(
    missing_skills: list[str], context: str = ""
) -> LearningRoadmapResponse:
    if not missing_skills:
        return LearningRoadmapResponse(roadmap=[], total_estimated_weeks=0)

    retrieved_chunks: list[str] = []
    for skill in missing_skills:
        docs = search(skill, k=2, doc_type="learning_resource")
        retrieved_chunks.extend(d.page_content for d, _ in docs)
    retrieved_text = "\n---\n".join(
        dict.fromkeys(retrieved_chunks)
    )  # dedupe, keep order

    user_content = f"""MISSING SKILLS: {", ".join(missing_skills)}
ADDITIONAL CONTEXT: {context or "none"}

RETRIEVED LEARNING RESOURCES:
{retrieved_text or "none available"}
"""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]
    data = invoke_json(RoadmapOut, messages, temperature=0.3)
    roadmap = [
        LearningResource(
            skill=item.skill,
            resources=item.resources,
            estimated_weeks=max(1, item.estimated_weeks),
        )
        for item in data.roadmap
    ]
    total = data.total_estimated_weeks or sum(r.estimated_weeks for r in roadmap)
    return LearningRoadmapResponse(roadmap=roadmap, total_estimated_weeks=total)
