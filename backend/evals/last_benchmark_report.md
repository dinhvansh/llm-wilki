# Retrieval Benchmark Report

- Success: True
- Query count: 4

## Quality Gates
- authoritySignal: True
- sectionSummarySignal: True
- notebookContextSignal: True
- structuredChunkCountBetterOrEqual: True
- structuredCitationStable: True
- allPassed: True

## Search

- `citation accuracy` hits=5 top=Citation accuracy must exceed 90 percent for grounded answers. latencyMs=40.48
- `hybrid retrieval` hits=6 top=RAG Architecture latencyMs=8.53
- `safety evaluation framework` hits=5 top=Safety Evaluation Framework latencyMs=14.46
- `API authentication` hits=2 top=API Reference & Integration Guide (Authentication and Authorization) latencyMs=7.7

## Ask

- `citation accuracy` citations=1 candidates=6 latencyMs=43.89
- `hybrid retrieval` citations=1 candidates=6 latencyMs=32.25
- `safety evaluation framework` citations=1 candidates=5 latencyMs=91.56
- `API authentication` citations=0 candidates=1 latencyMs=21.87
