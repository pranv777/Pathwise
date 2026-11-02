"""Evaluation harness.

python -m evaluation.run_eval                       # everything, both modes
python -m evaluation.run_eval --only retrieval      # embeddings only
python -m evaluation.run_eval --repeats 5 --sleep 4 # gentler on free-tier rate limits
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma

from app.agents.job_matching_agent import run_job_matching_agent
from app.agents.resume_agent import run_resume_agent
from app.config import settings
from app.models.schemas import JobListing, StudentProfile
from app.rag import vector_store
from app.rag.ingest import ingest_seed_kb
from app.utils import structured

HERE = Path(__file__).parent
DATA = HERE / "data"
RESULTS = HERE / "results"
logger = logging.getLogger("eval")


def _load(name: str) -> Any:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def band(score: int) -> str:
    return "high" if score >= 70 else "medium" if score >= 40 else "low"


def _norm(s: str) -> str:
    return s.strip().lower()


def _prf(pred: list[str], gold: list[str]) -> tuple[float, float]:
    p, g = {_norm(x) for x in pred}, {_norm(x) for x in gold}
    tp = len(p & g)
    return (tp / len(p) if p else 0.0, tp / len(g) if g else 0.0)


def _use_temp_store() -> None:
    """Point the RAG layer at a throwaway store seeded from the shipped KB."""
    vector_store._store = Chroma(
        collection_name="eval_kb",
        embedding_function=vector_store.get_embeddings(),
        persist_directory=tempfile.mkdtemp(prefix="wayfind_eval_"),
    )
    ingest_seed_kb()


def eval_retrieval(k: int, sleep: float) -> dict[str, Any]:
    cases = _load("retrieval_queries.json")
    hits, empty, rr, misses = 0, 0, [], []
    for c in cases:
        results = vector_store.search(c["query"], k=k, doc_type=c.get("doc_type"))
        time.sleep(sleep)
        if not results:  # search() swallows errors; don't count outages as misses
            empty += 1
            continue
        sources = [d.metadata.get("source") for d, _ in results]
        rank = next(
            (i for i, s in enumerate(sources, 1) if s in c["expected_sources"]), None
        )
        hits += rank is not None
        rr.append(1 / rank if rank else 0.0)
        if rank is None:
            misses.append({"query": c["query"], "got": sources})
    answered = len(cases) - empty
    return {
        "k": k,
        "queries": len(cases),
        "empty_results": empty,
        f"hit_rate@{k}": round(hits / answered, 3) if answered else None,
        "mrr": round(statistics.mean(rr), 3) if rr else None,
        "misses": misses,
    }


def eval_llm(mode: str, repeats: int, sleep: float) -> dict[str, Any]:
    settings.llm_output_mode = mode  # type: ignore[assignment]
    structured.stats.clear()

    resumes = _load("resumes.json")
    labels: dict[str, str] = _load("labels.json")
    jobs = {
        j["id"]: JobListing(**j)
        for j in json.loads(
            (Path(settings.knowledge_base_dir) / "sample_jobs.json").read_text()
        )
    }
    # Matching uses the gold profile so match metrics don't depend on parse noise.
    gold = {
        r["id"]: StudentProfile(
            skills=r["expected_skills"],
            projects=r["projects"],
            experience=r["experience"],
        )
        for r in resumes
    }

    precisions: list[float] = []
    recalls: list[float] = []
    for r in resumes:
        for _ in range(repeats):
            try:
                p = run_resume_agent(r["text"])
                pr, rc = _prf(p.skills, r["expected_skills"])
                precisions.append(pr)
                recalls.append(rc)
            except Exception as exc:  # noqa: BLE001 - parse failures are counted in structured.stats
                logger.warning("resume %s failed: %s", r["id"], exc)
            time.sleep(sleep)

    scores: dict[str, list[int]] = {}
    for pair in labels:
        rid, jid = pair.split(":")
        for _ in range(repeats):
            try:
                scores.setdefault(pair, []).append(
                    run_job_matching_agent(gold[rid], jobs[jid]).match_score
                )
            except Exception as exc:  # noqa: BLE001 - parse failures are counted in structured.stats
                logger.warning("match %s failed: %s", pair, exc)
            time.sleep(sleep)

    multi = [v for v in scores.values() if len(v) > 1]
    flat = [(pair, s) for pair, v in scores.items() for s in v]
    calls = structured.stats["calls"] or 1
    return {
        "mode": mode,
        "llm_calls": structured.stats["calls"],
        "parse_failure_rate_first_attempt": round(
            structured.stats["first_attempt_failures"] / calls, 3
        ),
        "parse_failure_rate_final": round(
            structured.stats["final_failures"] / calls, 3
        ),
        "retries": structured.stats["retries"],
        "skill_precision": round(statistics.mean(precisions), 3)
        if precisions
        else None,
        "skill_recall": round(statistics.mean(recalls), 3) if recalls else None,
        "score_stdev_mean": round(
            statistics.mean(statistics.pstdev(v) for v in multi), 2
        )
        if multi
        else None,
        "pairs_spread_le_10": round(
            sum(max(v) - min(v) <= 10 for v in multi) / len(multi), 3
        )
        if multi
        else None,
        "band_accuracy": round(
            sum(band(s) == labels[pair] for pair, s in flat) / len(flat), 3
        )
        if flat
        else None,
    }


def _table(rows: list[dict[str, Any]]) -> str:
    keys = [k for k in rows[0] if k != "mode"]
    lines = [
        "| metric | " + " | ".join(r["mode"] for r in rows) + " |",
        "|---|" + "---|" * len(rows),
    ]
    lines += [f"| {k} | " + " | ".join(str(r[k]) for r in rows) + " |" for k in keys]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["all", "retrieval", "llm"], default="all")
    ap.add_argument("--modes", nargs="+", default=["legacy", "structured"])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--sleep", type=float, default=2.0, help="seconds between calls")
    ap.add_argument("--k", type=int, default=3)
    args = ap.parse_args()

    if not settings.google_api_key:
        print("GOOGLE_API_KEY is required for the eval harness.")
        return 1

    _use_temp_store()
    report: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "model": settings.gemini_model,
        "repeats": args.repeats,
    }
    md = [
        f"# Eval run {report['timestamp']}\n",
        f"Model: `{settings.gemini_model}`, repeats: {args.repeats}\n",
    ]

    if args.only in ("all", "retrieval"):
        report["retrieval"] = eval_retrieval(args.k, args.sleep)
        md.append(
            "## Retrieval\n```json\n"
            + json.dumps(report["retrieval"], indent=2)
            + "\n```"
        )

    if args.only in ("all", "llm"):
        rows = [eval_llm(m, args.repeats, args.sleep) for m in args.modes]
        report["llm"] = rows
        md.append("## LLM output\n" + _table(rows))

    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    (RESULTS / f"{stamp}.json").write_text(json.dumps(report, indent=2))
    (RESULTS / "latest.md").write_text("\n\n".join(md))
    print("\n\n".join(md))
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s"
    )
    sys.exit(main())
