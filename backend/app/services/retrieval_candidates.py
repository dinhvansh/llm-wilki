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
    query_variants: list[dict] | None = None,
) -> list[dict]:
    """Coordinate Ask retrieval candidate building across direct and planned queries.

    The DB-specific candidate builders still live near their scoring helpers, but
    this module owns the retrieval orchestration contract so it can be tested and
    evolved independently from answer formatting.
    """
    planner = interpreted.get("planner") or {}
    variants = [item for item in (query_variants or []) if isinstance(item, dict) and str(item.get("query") or "").strip()]
    if not variants:
        variants = [{"id": "v1", "query": interpreted.get("standaloneQuery", ""), "language": "unknown", "type": "original"}]
    if planner.get("strategy") != "decompose":
        merged: list[dict] = []
        for variant in variants[:3]:
            variant_query = str(variant.get("query") or "").strip()
            variant_embedding = query_embedder(runtime, variant_query) if variant_query != interpreted.get("standaloneQuery") else query_embedding
            rows = single_query_retriever(db, runtime, interpreted, variant_embedding, question=variant_query, actor=actor)
            for row in rows:
                row["queryVariantId"] = variant.get("id")
                row["queryVariantType"] = variant.get("type")
                row["queryVariantLanguage"] = variant.get("language")
                diagnostics = row.get("diagnostics") or {}
                diagnostics["queryVariantId"] = row["queryVariantId"]
                diagnostics["queryVariantType"] = row["queryVariantType"]
                diagnostics["queryVariantLanguage"] = row["queryVariantLanguage"]
                row["diagnostics"] = diagnostics
            merged.extend(rows)
        return planned_candidate_merger(merged)

    planned_candidates: list[dict] = []
    for step in planner.get("subQueries", [])[:4]:
        step_query = str(step.get("query") or "").strip()
        if not step_query:
            continue
        step_intent = str(step.get("intent") or interpreted["intent"])
        step_variants: list[tuple[str, str]] = [(step_query, "unknown")]
        for variant in variants[:3]:
            variant_query = str(variant.get("query") or "").strip()
            if variant_query and variant_query.lower() != step_query.lower():
                step_variants.append((f"{variant_query}: {step_query}", str(variant.get("language") or "unknown")))
        seen: set[str] = set()
        for variant_query, variant_language in step_variants:
            normalized = variant_query.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            step_embedding = query_embedder(runtime, variant_query)
            rows = single_query_retriever(
                db,
                runtime,
                interpreted,
                step_embedding,
                question=variant_query,
                intent_override=step_intent,
                planner_step=step,
                actor=actor,
            )
            for row in rows:
                row["queryVariantId"] = variant_query
                row["queryVariantType"] = "planned_variant"
                row["queryVariantLanguage"] = variant_language
                diagnostics = row.get("diagnostics") or {}
                diagnostics["queryVariantId"] = row["queryVariantId"]
                diagnostics["queryVariantType"] = row["queryVariantType"]
                diagnostics["queryVariantLanguage"] = row["queryVariantLanguage"]
                row["diagnostics"] = diagnostics
            planned_candidates.extend(rows)
    return planned_candidate_merger(planned_candidates)
