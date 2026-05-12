# Ask AI / Document QA Test Cases

Tai lieu nay dung de test lai toan bo nhung gi da nang cap trong:

- Ask AI retrieval va answer quality
- ingest metadata va semantic chunking
- knowledge units / section summaries / authority ranking
- multimodal artifact retrieval / citation provenance
- OCR / Docling local va Docker runtime
- eval, benchmark, admin debug, quality gates

Khac voi checklist release, file nay tap trung vao:

- tinh huong can test
- dieu kien dau vao
- buoc test
- ket qua ky vong
- lenh verify san co trong repo

## 0. One-command automation

Neu muon chay toan bo suite tu dong:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_document_qa_suite.ps1
```

Artifacts:

- `backend/evals/last_document_qa_suite.json`
- `backend/evals/last_document_qa_suite.md`

## 1. Muc tieu test

Can dam bao 5 muc sau:

1. Bao mat:
   he thong khong uu tien nham source informal/draft/archived khi co source official/approved manh hon
2. Chinh xac:
   Ask AI retrieve dung evidence, dung source, dung answer type
3. Sach se:
   khong co workaround phu thuoc may ca nhan, local va Docker deu verify duoc
4. Khong tam bo:
   chunking, retrieval, rerank, OCR, eval, debug phai co duong test ro rang
5. Giai quyet triet de:
   fail case phai truy duoc ve query understanding, retrieval, authority, context assembly, hoac source ingest

## 2. Cach dung bo test nay

Chia thanh 3 lop:

- `Automated regression`: script co san, phai chay pass
- `Scenario validation`: tinh huong theo behavior, co the dung UI hoac API de xac nhan
- `Operator drilldown`: xem admin/eval/debug de truy vet khi co sai lech

Nen test theo thu tu:

1. environment va runtime
2. ingest / OCR
3. retrieval / Ask AI
4. authority / conflict / follow-up
5. eval / benchmark / admin
6. smoke local va full-stack

## 3. Environment Gate

### TC-ENV-01: Backend local venv dung

- Muc dich:
  xac nhan backend local khong phu thuoc Python global
- Lenh:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_local_backend.ps1
backend\.venv\Scripts\python.exe -m pip check
```

- Ky vong:
  - `setup_local_backend.ps1` PASS
  - `No broken requirements found.`

### TC-ENV-02: Backend compile pass

- Lenh:

```powershell
backend\.venv\Scripts\python.exe -m compileall backend\app backend\scripts
```

- Ky vong:
  - khong co syntax error

### TC-ENV-03: Frontend build pass

- Lenh:

```powershell
npm --prefix llm-wiki run build
```

- Ky vong:
  - Next.js build PASS

## 4. OCR / Parser Cases

### TC-OCR-01: Local OCR runtime du `eng` va `vie`

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase28.py
```

- Ky vong:
  - `doclingParser = true`
  - `ocrEngine = tesseract_cli`
  - `ocrLangs` co `eng` va `vie`
  - `tesseractCommand` resolve ve binary that
  - `tessdataPath` resolve ve local override hoac runtime path hop le

### TC-OCR-02: Docker OCR runtime pass

- Dieu kien:
  stack Docker da build
- Lenh:

```powershell
docker compose up -d --build postgres redis drawio backend worker frontend
powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild
```

- Ky vong:
  - backend/frontend/draw.io health PASS
  - OCR dependency nam trong image backend/worker

### TC-OCR-03: PDF scan / image OCR fallback behavior

- Cach test:
  upload mot anh hoac PDF scan qua UI `Sources`
- Ky vong:
  - neu Docker: ingest thanh cong va source duoc index
  - neu local native:
    - neu OCR runtime san sang: ingest thanh cong
    - neu OCR runtime thieu: loi phai ro rang, khong fail mo ho

## 5. Ingest / Metadata / Chunking Cases

### TC-INGEST-01: Structured chunking benchmark

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\benchmark_retrieval.py
```

- Ky vong:
  - `structured` co signal tot hon hoac bang `window`
  - `structuredCitationStable = true`
  - `authoritySignal = true`
  - `sectionSummarySignal = true`

### TC-INGEST-02: Source metadata va document type

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase34.py
```

- Ky vong:
  - `documentType = policy`
  - chunk roles co `scope/rule/exception`
  - default `sourceStatus/authorityLevel` duoc preserve
  - metadata override duoc persist

### TC-INGEST-03: Semantic chunking va section summary

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase35.py
```

- Ky vong:
  - `chunkCount >= 3`
  - `sectionSummaryCount >= 3`
  - co `parentSectionSummary`
  - section role phan biet duoc `step/exception/prerequisite` khi phu hop

### TC-INGEST-04: Source sections normalized

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase40.py
```

- Ky vong:
  - `sourceSectionCount >= 3`
  - co `chunkIndexes`
  - co roles khac `general`

## 6. Ask AI Retrieval / Answer Cases

### TC-ASK-01: Follow-up clarification

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase33.py
backend\.venv\Scripts\python.exe backend\scripts\evaluate_quality.py --tag followup
```

- Ky vong:
  - follow-up mo ho nhu `tra loi sai roi` tra ve `clarification`
  - khong retrieve bua
  - `clarificationAccuracy = 1.0`

### TC-ASK-02: Follow-up resolution

- Tinh huong:
  - hoi cau tong quat
  - follow-up bang `y toi la hybrid retrieval`
- Ky vong:
  - `interpretedQuery.standaloneQuery` phai rewrite duoc
  - answer dung source va dung term mong doi
  - `followupResolutionSuccess = 1.0`

### TC-ASK-03: Multi-object retrieval

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase36.py
backend\.venv\Scripts\python.exe backend\scripts\test_phase37.py
backend\.venv\Scripts\python.exe backend\scripts\test_phase38.py
```

- Ky vong:
  - candidate set co `section_summary`
  - candidate set co `knowledge_unit`
  - citation provenance phan biet `chunk/claim/section_summary/knowledge_unit`

### TC-ASK-04: Intent-aware retrieval

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase41.py
```

- Ky vong:
  - query comparison sinh roles `comparison_a/comparison_b`
  - query conflict sinh roles `conflict_side_a/conflict_side_b`
  - source uu tien dung authority hon

### TC-ASK-05: Authority-aware conflict handling

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\evaluate_quality.py --tag conflict
```

### TC-ASK-06: Artifact-aware multimodal citation flow

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase53.py
```

- Ky vong:
  - `artifact_summary` xuat hien trong selected context
  - citation tra ve `candidateType = artifact_summary`
  - citation tra ve `artifactType = notebook` hoac artifact type phu hop

- Ky vong:
  - answerType = `conflict`
  - preferred source la source official/approved/manh hon
  - `conflictHandlingAccuracy = 1.0`

## 7. Quality / Lint / Governance Cases

### TC-QUALITY-01: Eval full set

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\evaluate_quality.py
```

- Ky vong:
  - `qualityGates.allPassed = true`
  - metrics chinh:
    - `retrievalRecallAt5`
    - `retrievalRecallAt10`
    - `rerankPrecisionAt5`
    - `answerFaithfulness`
  - failed behavior cases = 0

### TC-QUALITY-02: Persisted eval runs

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase44.py
```

- Ky vong:
  - sau khi chay eval/benchmark phai co run history trong DB

### TC-QUALITY-03: Tag-based subset

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase45.py
```

- Ky vong:
  - subset theo tag chay dung
  - report chi phan anh subset duoc chon

### TC-QUALITY-04: Import / export eval dataset

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase46.py
```

- Ky vong:
  - import/export dataset khong mat case quan trong

### TC-QUALITY-05: Compare quality runs

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase47.py
```

- Ky vong:
  - compare baseline/candidate chay duoc
  - artifacts compare duoc tao

### TC-LINT-01: Authority mismatch / archived source

- Lenh:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\test_phase42.py
```

- Ky vong:
  - detect duoc `authority_mismatch_sources`
  - detect duoc `archived_source_link`

## 8. Admin / Debug Cases

### TC-ADMIN-01: Admin quality dashboard

- Dieu kien:
  chay app, co it nhat 1 eval run va 1 benchmark run
- Man hinh:
  `/admin`
- Ky vong:
  - xem duoc latest eval
  - xem duoc latest benchmark
  - xem duoc recent runs persisted
  - xem duoc failed behavior cases neu co
  - xem duoc related sources/pages/citations trong failed case

### TC-ADMIN-02: Retrieval drilldown

- Cach test:
  hoi 1 cau conflict hoac follow-up trong UI `Ask`
- Ky vong:
  - `interpretedQuery` hien dung
  - diagnostics hien top candidates
  - selected context co roles dung
  - conflict summary neu co

## 9. Full Regression / Smoke Cases

### TC-REG-01: Local regression

- Lenh:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_regression.ps1 -SkipDocker -SkipE2E
```

- Ky vong:
  - PASS

### TC-REG-02: Docker smoke

- Lenh:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild
```

- Ky vong:
  - backend health/readiness PASS
  - frontend PASS
  - draw.io PASS

### TC-REG-03: E2E smoke

- Lenh:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e_smoke.ps1
```

- Ky vong:
  - source ingest PASS
  - page generation PASS
  - ask PASS
  - route smoke PASS

## 10. Tinh huong danh gia lai can uu tien

Day la nhom case can test lai moi khi sua retrieval/ingest/authority:

### Scenario A: File cu vs file moi

- Dau vao:
  2 source cung chu de, mot source cu, mot source moi
- Muc tieu:
  xac nhan Ask AI uu tien source moi hon khi noi dung xung dot

### Scenario B: Draft vs approved

- Dau vao:
  1 draft note va 1 approved policy
- Muc tieu:
  Ask AI va lint phai uu tien approved policy

### Scenario C: Official policy vs meeting note

- Dau vao:
  1 policy chinh thuc, 1 meeting note informal
- Muc tieu:
  answer phai noi ro source nao manh hon va vi sao

### Scenario D: SOP local vs global policy

- Dau vao:
  local SOP de xuat mot buoc, global policy co rule khac
- Muc tieu:
  conflict handling phai chi ra layer uu tien

### Scenario E: Follow-up mo ho

- Dau vao:
  `tra loi sai roi`, `y toi la cai tren`, `so sanh 2 cai`
- Muc tieu:
  he thong phai clarify hoac rewrite, khong retrieve bua

### Scenario F: Scan PDF / image OCR

- Dau vao:
  PDF scan tieng Viet va image OCR
- Muc tieu:
  parser/OCR phai tao text dung de chunk/retrieve duoc

### Scenario G: Citation grounding

- Dau vao:
  cau hoi factual va procedural
- Muc tieu:
  answer phai co citation dung object type va dung source

## 11. Recommended Test Order

Neu can test nhanh sau mot thay doi lon:

1. `setup_local_backend.ps1`
2. `test_phase28.py`
3. `test_phase33.py`
4. `test_phase34.py`
5. `test_phase35.py`
6. `test_phase40.py`
7. `test_phase41.py`
8. `test_phase42.py`
9. `benchmark_retrieval.py`
10. `evaluate_quality.py`
11. `run_regression.ps1 -SkipDocker -SkipE2E`
12. `docker_smoke.ps1 -SkipBuild`
13. `e2e_smoke.ps1`

## 12. Pass / Fail Rule

Chi xem la `Ready` khi:

- local venv sach
- OCR runtime san sang neu can OCR
- benchmark PASS
- eval PASS
- local regression PASS
- Docker smoke PASS
- E2E smoke PASS

Neu mot case fail, phai classify nguyen nhan vao 1 trong 5 nhom:

1. parser / OCR
2. chunking / metadata
3. retrieval / rerank
4. authority / conflict / citation
5. environment / runtime
