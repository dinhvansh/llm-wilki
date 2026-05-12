# Quality Release Checklist

Dung checklist nay truoc khi merge mot thay doi lon lien quan `Ask AI`, retrieval, chunking, ingest semantics, hoac citation policy.

## 1. Chot baseline

Chay benchmark va eval truoc thay doi:

```powershell
python backend\scripts\benchmark_retrieval.py
python backend\scripts\evaluate_quality.py
```

Neu can chay subset theo nhom case:

```powershell
python backend\scripts\evaluate_quality.py --tag followup
python backend\scripts\evaluate_quality.py --tag conflict
```

## 2. Sau khi sua code

Chay lai:

```powershell
python backend\scripts\benchmark_retrieval.py
python backend\scripts\evaluate_quality.py
```

Neu thay doi tap trung vao mot nhom hanh vi:

```powershell
python backend\scripts\evaluate_quality.py --tag retrieval
python backend\scripts\evaluate_quality.py --tag authority
python backend\scripts\evaluate_quality.py --tag followup
```

## 3. So sanh truoc/sau

So sanh hai run `eval` gan nhat:

```powershell
python backend\scripts\compare_quality_runs.py --run-type eval
```

So sanh hai run `benchmark` gan nhat:

```powershell
python backend\scripts\compare_quality_runs.py --run-type benchmark
```

Artifacts:

- `backend/evals/last_quality_compare.json`
- `backend/evals/last_quality_compare.md`

## 4. Gate merge toi thieu

Khong merge neu mot trong cac dieu sau bi rot:

- `benchmark_retrieval.py` fail
- `evaluate_quality.py` fail
- `retrievalRecallAt5` giam co y nghia ma khong co ly do ro rang
- `rerankPrecisionAt5` giam co y nghia ma khong co tradeoff duoc chap nhan
- `answerFaithfulness` giam
- `clarificationAccuracy`, `followupResolutionSuccess`, `conflictHandlingAccuracy` giam
- benchmark/eval gate authority, archived source, section summary, hoac conflict bi fail

## 5. Truoc khi release local/full-stack

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1 -SkipDocker -SkipE2E
```

Neu can chot full local stack:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild
powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1
```

## 6. Doc ket qua

- Admin UI: `/admin`
- Recent persisted runs: trong `Quality > Recent Runs`
- Failed behavior cases: trong `Quality > Failed Behavior Cases`
- Latest raw artifacts:
  - `backend/evals/last_eval_report.json`
  - `backend/evals/last_benchmark_report.json`
  - `backend/evals/last_quality_compare.json`
