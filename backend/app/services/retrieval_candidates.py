from __future__ import annotations

from collections.abc import Callable


def retrieve_candidates(
    *,
    db,
    runtime,
    interpreted: dict,
    query_embedding: list[float] | None,
    actor=None,
    single_query_retriever: Callable[..., list[dict]],
    planned_candidate_merger: Callable[[list[dict]], list[dict]],
    query_embedder: Callable[[object, str], list[float] | None],
) -> list[dict]:
    """Coordinate Ask retrieval candidate building across direct and planned queries.

    The DB-specific candidate builders still live near their scoring helpers, but
    this module owns the retrieval orchestration contract so it can be tested and
    evolved independently from answer formatting.
    """
    planner = interpreted.get("planner") or {}
    if planner.get("strategy") != "decompose":
        return single_query_retriever(db, runtime, interpreted, query_embedding, actor=actor)

    planned_candidates: list[dict] = []
    for step in planner.get("subQueries", [])[:4]:
        step_query = str(step.get("query") or "").strip()
        if not step_query:
            continue
        step_intent = str(step.get("intent") or interpreted["intent"])
        step_embedding = query_embedder(runtime, step_query)
        planned_candidates.extend(
            single_query_retriever(
                db,
                runtime,
                interpreted,
                step_embedding,
                question=step_query,
                intent_override=step_intent,
                planner_step=step,
                actor=actor,
            )
        )
    return planned_candidate_merger(planned_candidates)
