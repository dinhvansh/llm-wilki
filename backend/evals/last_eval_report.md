# Quality Eval Report (phase17-eval-v1)

- Success: True
- Requested tags: all
- Cases: 3
- Citation coverage: 1.0
- Citation precision: 1.0
- Retrieval hit rate: 1.0
- Retrieval recall@5: 1.0
- Retrieval recall@10: 1.0
- Rerank precision@5: 1.0
- Answer faithfulness: 0.9
- Unsupported claim count: 0
- Clarification accuracy: 1.0
- Follow-up resolution: 1.0
- Source lookup accuracy: 1.0
- Conflict handling accuracy: 1.0
- Analysis planning accuracy: 1.0
- Scope adherence: 1.0
- Notebook summary accuracy: 1.0
- Authority synthesis accuracy: 1.0
- Suggestion usefulness proxy: 1.0

## Cases
- `citation-accuracy` recall@5=1.0 precision@5=1.0 faithfulness=0.9 sourceHit=True confidence=0.63
- `hybrid-retrieval` recall@5=1.0 precision@5=1.0 faithfulness=0.9 sourceHit=True confidence=0.6467
- `safety-evaluation` recall@5=1.0 precision@5=1.0 faithfulness=0.9 sourceHit=True confidence=0.8

## Behavior Cases
- `clarification-followup` type=clarification success=True answerType=clarification
- `followup-resolution` type=followup_resolution success=True answerType=clarified_answer
- `source-lookup` type=source_lookup success=True answerType=source_lookup
- `conflict-priority` type=conflict success=True answerType=conflict
- `analysis-planner` type=analysis_planning success=True answerType=analysis
- `scoped-source-ask` type=scoped_ask success=True answerType=step_by_step
- `notebook-summary` type=notebook_summary success=True answerType=summary
- `authority-synthesis` type=authority_synthesis success=True answerType=conflict
- `suggestion-usefulness` type=suggestion_usefulness success=True answerType=direct_answer
- `artifact-multimodal-summary` type=notebook_summary success=True answerType=direct_answer
