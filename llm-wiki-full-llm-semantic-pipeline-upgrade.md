# LLM Wiki Upgrade Plan — Full LLM Semantic Knowledge Pipeline

## 1. Mục tiêu

Cập nhật dự án **LLM Wiki** từ hệ thống xử lý tài liệu dựa nhiều vào heuristic thành một hệ thống tri thức có LLM hỗ trợ đầy đủ.

Nguyên tắc thiết kế:

```text
Code keeps structure and citations.
LLM creates semantic knowledge.
Human review creates trust.
```

Diễn giải:

- **Code / parser / OCR** giữ cấu trúc tài liệu, page number, block, citation.
- **LLM** hiểu nghĩa, extract tri thức, tạo wiki page, phát hiện conflict.
- **Human review** duyệt lại để tri thức đáng tin cậy trước khi publish.

---

## 2. Hiện trạng dự án

Pipeline hiện tại:

```text
OCR engine              = Tesseract
Docling parsing         = parser/OCR pipeline, không phải chat AI
chunking                = structure-aware, không phải LLM
claim extraction        = heuristic
entity extraction       = heuristic
timeline extraction     = heuristic
glossary extraction     = heuristic
page type classification= heuristic
BPM suitability scoring = heuristic
```

Nhận xét:

- Nền tảng hiện tại tốt vì ổn định, rẻ, dễ debug.
- Nhưng tầng “hiểu tri thức” vẫn chưa đủ mạnh.
- Nếu muốn thành **LLM Wiki đúng nghĩa**, các bước semantic nên chuyển sang LLM hoặc hybrid LLM + heuristic.

---

## 3. Target Architecture

Pipeline mục tiêu:

```text
Upload Source
→ OCR / Docling Parse
→ Parsed Blocks
→ Structure-aware Chunks
→ Heuristic Hints
→ LLM Knowledge Extraction
→ LLM Entity Extraction
→ LLM Relation Extraction
→ LLM Timeline Extraction
→ LLM Glossary Extraction
→ LLM Page Type Classification
→ LLM BPM Suitability Scoring
→ LLM Page Composer
→ Conflict Detection
→ Review Queue
→ Published Wiki
→ Ask AI over published knowledge + source evidence
```

---

## 4. Phần nào giữ deterministic/code-based?

Các phần sau **không nên giao cho LLM làm chính**:

```text
OCR
Docling parsing
parsed block storage
structure-aware chunking
page number / bbox / block citation mapping
embedding/indexing
job status/log/retry
review/publish workflow
```

Lý do:

- Cần ổn định.
- Cần trace/citation chính xác.
- Cần debug được.
- Không nên để LLM tự quyết page/chunk/citation.

---

## 5. Phần nào chuyển sang LLM-powered?

Các phần sau nên có LLM:

```text
knowledge unit extraction
entity extraction
relation extraction
timeline extraction
glossary extraction
page type classification
BPM suitability scoring
page composition
conflict detection
```

Heuristic hiện tại không xóa, mà dùng làm:

```text
- hints cho LLM
- fallback nếu LLM lỗi hoặc bị tắt
- validation để tăng confidence nếu heuristic và LLM cùng đồng ý
- diagnostics/debug để so sánh heuristic vs LLM
```

---

## 6. Đổi khái niệm Claim thành Knowledge Unit

Không nên chỉ dùng `claim` vì hệ thống tri thức cần cover mọi loại tài liệu.

Dùng khái niệm rộng hơn:

```text
Knowledge Unit
```

Một Knowledge Unit là một mẩu tri thức atomic, có nguồn chứng minh.

Công thức:

```text
Knowledge Unit = Statement + Type + Context + Evidence + Entities + Relations + Status
```

Ví dụ:

```text
Employees must submit travel expense claims within 7 days.
Finance is responsible for verifying supporting documents.
The backend uses FastAPI and Alembic.
The Docker stack can be started by running docker compose up.
API authentication requires an API key in the request header.
```

---

## 7. Knowledge Types

Hỗ trợ các `knowledge_type` universal sau:

```text
definition
fact
rule
requirement
process
instruction
responsibility
condition
exception
decision
metric
risk
open_issue
timeline_event
glossary_term
configuration
command
api_endpoint
troubleshooting
```

Bộ này cover được:

```text
policy
SOP
contract
meeting note
technical guide
support guide
FAQ
API document
architecture document
report
business process document
general document
```

---

## 8. Document Types

Hỗ trợ các `document_type` sau:

```text
policy
sop
contract
meeting_note
technical_guide
support_guide
faq
api_doc
architecture_doc
report
business_process
general
```

LLM prompt nên thay đổi theo `document_type`.

Ví dụ:

- `contract`: chú ý obligation, liability, payment term, termination.
- `technical_guide`: chú ý command, configuration, dependency, API, error.
- `support_guide`: chú ý problem, symptom, cause, solution, escalation.
- `sop`: chú ý process, role, step, approval, exception.
- `meeting_note`: chú ý decision, action item, owner, timeline, open issue.

---

## 9. Core Tables

Tối thiểu cần có hoặc cập nhật các bảng:

```text
sources
source_blocks
source_chunks
knowledge_units
entities
knowledge_relations
wiki_pages
page_versions
extraction_runs
review_items
job_logs
```

Nếu bảng đã tồn tại thì migrate/extend, không duplicate.

---

## 10. knowledge_units Table

Schema đề xuất:

```sql
CREATE TABLE knowledge_units (
  id UUID PRIMARY KEY,
  source_id UUID NOT NULL,
  chunk_id UUID,
  extraction_run_id UUID,

  statement TEXT NOT NULL,
  knowledge_type TEXT NOT NULL,
  document_type TEXT,
  domain TEXT,
  tags JSONB DEFAULT '[]',
  entities JSONB DEFAULT '[]',
  attributes JSONB DEFAULT '{}',
  source_refs JSONB DEFAULT '[]',

  confidence NUMERIC,
  extraction_method TEXT,
  status TEXT DEFAULT 'draft',

  page_start INT,
  page_end INT,
  block_ids JSONB DEFAULT '[]',

  valid_from DATE,
  valid_to DATE,

  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

Allowed `extraction_method`:

```text
heuristic
llm
hybrid
manual
```

Allowed `status`:

```text
draft
accepted
rejected
merged
superseded
conflict
published
```

---

## 11. entities Table

Schema đề xuất:

```sql
CREATE TABLE entities (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  entity_type TEXT,
  aliases JSONB DEFAULT '[]',
  description TEXT,
  domain TEXT,
  source_refs JSONB DEFAULT '[]',
  confidence NUMERIC,
  status TEXT DEFAULT 'draft',
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

Entity types gợi ý:

```text
person
department
role
system
process
document
policy
product
api
table
metric
risk
vendor
customer
location
concept
tool
service
component
```

---

## 12. knowledge_relations Table

Schema đề xuất:

```sql
CREATE TABLE knowledge_relations (
  id UUID PRIMARY KEY,
  source_id UUID,
  from_entity_id UUID,
  to_entity_id UUID,
  from_knowledge_unit_id UUID,
  to_knowledge_unit_id UUID,

  relation_type TEXT NOT NULL,
  description TEXT,
  source_refs JSONB DEFAULT '[]',
  confidence NUMERIC,
  status TEXT DEFAULT 'draft',

  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

Relation types gợi ý:

```text
responsible_for
requires
depends_on
part_of
approved_by
owned_by
used_by
supersedes
conflicts_with
related_to
causes
solves
mentions
defines
```

---

## 13. extraction_runs Table

Bảng này rất quan trọng để trace LLM.

Schema đề xuất:

```sql
CREATE TABLE extraction_runs (
  id UUID PRIMARY KEY,
  source_id UUID,
  run_type TEXT NOT NULL,
  method TEXT NOT NULL,
  model TEXT,
  provider TEXT,
  prompt_version TEXT,
  status TEXT DEFAULT 'running',

  input_chunk_count INT,
  output_item_count INT,
  token_input INT,
  token_output INT,
  cost_estimate NUMERIC,

  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  error_message TEXT,
  metadata JSONB DEFAULT '{}'
);
```

Run types:

```text
knowledge_extraction
entity_extraction
relation_extraction
timeline_extraction
glossary_extraction
page_classification
bpm_scoring
page_composition
conflict_detection
```

Methods:

```text
heuristic
llm
hybrid
manual
```

---

## 14. LLM Configuration

Thêm config qua `.env` hoặc admin settings:

```env
ENABLE_LLM_KNOWLEDGE_EXTRACTION=true
ENABLE_LLM_ENTITY_EXTRACTION=true
ENABLE_LLM_RELATION_EXTRACTION=true
ENABLE_LLM_TIMELINE_EXTRACTION=true
ENABLE_LLM_GLOSSARY_EXTRACTION=true
ENABLE_LLM_PAGE_CLASSIFICATION=true
ENABLE_LLM_BPM_SCORING=true
ENABLE_LLM_PAGE_COMPOSER=true
ENABLE_LLM_CONFLICT_DETECTION=true

LLM_PROVIDER=openai
LLM_EXTRACTION_MODEL=gpt-4.1-mini
LLM_PAGE_MODEL=gpt-4.1
LLM_REASONING_MODEL=gpt-4.1
LLM_MAX_CHUNKS_PER_RUN=20
LLM_TEMPERATURE=0.1
```

Nếu dự án đã có provider config thì tích hợp vào config hiện tại.

---

## 15. LLM Service Layer

Tạo service layer rõ ràng cho LLM calls.

Cấu trúc gợi ý:

```text
app/services/llm/
  client.py
  schemas.py
  prompts/
    knowledge_extractor.py
    entity_extractor.py
    relation_extractor.py
    timeline_extractor.py
    glossary_extractor.py
    page_classifier.py
    bpm_scorer.py
    page_composer.py
    conflict_detector.py
```

LLM client cần hỗ trợ:

```text
provider
model
temperature
JSON schema output
retry
timeout
logging
token usage capture
error capture
```

---

## 16. Prompt Requirements

Mọi extractor prompt phải trả về strict JSON.

Không trả prose tự do.

Quy tắc chung:

```text
- Chỉ extract tri thức được support trực tiếp bởi chunk.
- Không suy diễn quá nguồn.
- Mỗi knowledge unit chỉ chứa một ý atomic.
- Giữ nguyên số liệu, ngày tháng, deadline, condition, role, command, API path, config key.
- Mỗi item phải có source_refs trỏ về source_id, chunk_id, page_start, page_end, block_ids.
- Nếu không có tri thức hữu ích, trả array rỗng.
```

---

## 17. Knowledge Extractor Prompt

```text
You are a knowledge extraction engine for an internal company wiki.

Your task is to extract atomic, source-grounded knowledge units from the provided document chunk.

Rules:
- Extract only knowledge explicitly supported by the chunk.
- Do not infer beyond the text.
- Each knowledge unit must contain one atomic idea only.
- Preserve important numbers, dates, deadlines, conditions, responsibilities, commands, API paths, configuration keys, and exceptions.
- Use the provided document_type to classify the knowledge correctly.
- Return strict JSON only.
- Every item must include source_refs using the provided source_id, chunk_id, page_start, page_end, and block_ids.
- If there is no useful knowledge, return an empty array.

Allowed knowledge_type values:
definition, fact, rule, requirement, process, instruction, responsibility, condition, exception, decision, metric, risk, open_issue, timeline_event, glossary_term, configuration, command, api_endpoint, troubleshooting.

Input:
- source_id
- chunk_id
- document_type
- heading_path
- page_start
- page_end
- block_ids
- chunk_text
- heuristic_hints

Return JSON:
{
  "knowledge_units": [
    {
      "statement": "string",
      "knowledge_type": "string",
      "confidence": 0.0,
      "entities": [
        {"name": "string", "type": "string"}
      ],
      "tags": ["string"],
      "attributes": {},
      "source_refs": [
        {
          "source_id": "string",
          "chunk_id": "string",
          "page_start": 1,
          "page_end": 1,
          "block_ids": ["string"]
        }
      ]
    }
  ]
}
```

---

## 18. Entity Extractor Prompt

```text
Extract canonical entities from the provided chunk and/or knowledge units.

Entity types:
person, department, role, system, process, document, policy, product, api, table, metric, risk, vendor, customer, location, concept, tool, service, component.

Rules:
- Extract only meaningful entities.
- Merge obvious aliases if supported by context.
- Do not invent descriptions.
- Return strict JSON only.
```

Return JSON:

```json
{
  "entities": [
    {
      "name": "string",
      "entity_type": "string",
      "aliases": ["string"],
      "description": "string",
      "confidence": 0.0,
      "source_refs": []
    }
  ]
}
```

---

## 19. Relation Extractor Prompt

```text
Extract relations between entities and/or knowledge units.

Allowed relation_type:
responsible_for, requires, depends_on, part_of, approved_by, owned_by, used_by, supersedes, conflicts_with, related_to, causes, solves, mentions, defines.

Rules:
- Extract only relations grounded in the provided source.
- Do not infer unsupported relations.
- Return strict JSON only.
```

Return JSON:

```json
{
  "relations": [
    {
      "from": "string",
      "to": "string",
      "relation_type": "responsible_for|requires|depends_on|part_of|approved_by|owned_by|used_by|supersedes|conflicts_with|related_to|causes|solves|mentions|defines",
      "description": "string",
      "confidence": 0.0,
      "source_refs": []
    }
  ]
}
```

---

## 20. Timeline Extractor Prompt

```text
Extract date-based events from the provided chunk.

Rules:
- Only extract events with clear or implied dates.
- If exact date is not available, event_date can be null and date_text should be preserved in attributes.
- Return strict JSON only.
```

Return JSON:

```json
{
  "timeline_events": [
    {
      "event_date": "YYYY-MM-DD or null",
      "event_title": "string",
      "event_description": "string",
      "related_entities": ["string"],
      "confidence": 0.0,
      "source_refs": []
    }
  ]
}
```

---

## 21. Glossary Extractor Prompt

```text
Extract important glossary terms from the provided chunk.

Rules:
- Extract terms that are defined, explained, or essential to understanding the document.
- Do not create generic glossary entries unless supported by source text.
- Return strict JSON only.
```

Return JSON:

```json
{
  "glossary_terms": [
    {
      "term": "string",
      "definition": "string",
      "aliases": ["string"],
      "domain": "string",
      "confidence": 0.0,
      "source_refs": []
    }
  ]
}
```

---

## 22. Page Classifier Prompt

Allowed page types:

```text
summary_page
concept_page
sop_page
entity_page
timeline_page
issue_page
glossary_page
technical_guide_page
support_article
api_reference_page
architecture_page
business_process_page
```

Return JSON:

```json
{
  "suggested_pages": [
    {
      "page_type": "string",
      "title": "string",
      "reason": "string",
      "confidence": 0.0,
      "source_refs": []
    }
  ]
}
```

---

## 23. BPM Suitability Scoring Prompt

```text
Analyze whether the document describes a process suitable for BPM/workflow automation.

Look for:
- requester
- approver
- status
- deadline
- condition
- notification
- handoff
- SLA
- exception
- system action
- manual approval
```

Return JSON:

```json
{
  "score": 0,
  "level": "low|medium|high",
  "reason": "string",
  "detected_workflow_elements": [
    "requester",
    "approver",
    "status",
    "deadline",
    "condition",
    "notification",
    "handoff",
    "SLA",
    "exception"
  ],
  "missing_information": ["string"],
  "recommended_next_steps": ["string"],
  "source_refs": []
}
```

---

## 24. Page Composer Prompt

```text
Create draft wiki pages from chunks, knowledge units, entities, relations, glossary terms, timeline events, and source refs.

Rules:
- Do not publish automatically.
- Output Markdown.
- Include citations/source references.
- Do not invent facts.
- Prefer accepted knowledge units if available.
- Otherwise use draft knowledge units and mark the page as draft.
- If source evidence is weak, include a warning note.
```

Return JSON:

```json
{
  "title": "string",
  "page_type": "string",
  "content_markdown": "string",
  "source_refs": [],
  "related_entities": [],
  "related_knowledge_unit_ids": [],
  "confidence": 0.0
}
```

---

## 25. Conflict Detector Prompt

Detect:

```text
conflicts
supersedes
duplicates
updates
related items
```

Return JSON:

```json
{
  "conflicts": [
    {
      "new_knowledge_unit_id": "string",
      "existing_knowledge_unit_id": "string",
      "conflict_type": "conflict|supersedes|duplicate|update|related",
      "explanation": "string",
      "severity": "low|medium|high",
      "confidence": 0.0
    }
  ]
}
```

---

## 26. Hybrid Strategy

Không xóa heuristic extractors hiện tại.

Dùng theo một hoặc nhiều cách:

```text
1. Heuristic as hints
   Run heuristic first and pass results to LLM as heuristic_hints.

2. Heuristic as fallback
   If LLM is disabled or fails, use heuristic output.

3. Heuristic as validation
   Compare heuristic and LLM output and increase confidence if they agree.

4. Heuristic as diagnostics
   Show differences between heuristic and LLM extraction in admin/debug view.
```

Preferred approach:

```text
Heuristic → candidate hints
LLM → semantic extraction and normalization
Reviewer → approve/reject
```

---

## 27. Review Workflow

Tất cả LLM-generated outputs phải lưu là `draft` mặc định.

Không auto-publish.

Review actions:

```text
accept
reject
edit
merge
mark_conflict
publish
```

Review áp dụng cho:

```text
knowledge units
entities
relations
draft wiki pages
conflicts
BPM analysis
```

---

## 28. UI Requirements

Source detail page nên có tabs:

```text
Overview
Blocks
Chunks
Knowledge Units
Entities
Relations
Timeline
Glossary
Suggested Pages
BPM Analysis
Draft Pages
Extraction Runs
Logs
```

Knowledge Units tab hiển thị:

```text
statement
knowledge_type
confidence
extraction_method
status
source page/chunk
actions: accept, reject, edit, merge
```

Extraction Runs tab hiển thị:

```text
run_type
method
model
prompt_version
status
input chunks
output items
token usage
cost estimate
duration
error message
```

---

## 29. Worker / Job Requirements

Pipeline nên chạy async trong worker.

Mỗi step có status và logs.

Suggested source statuses:

```text
uploaded
parsing
parsed
chunking
chunked
extracting_knowledge
extracting_entities
extracting_relations
extracting_timeline
extracting_glossary
classifying_pages
scoring_bpm
composing_pages
detecting_conflicts
review_pending
published
failed
```

Nếu failed thì lưu:

```text
failed_step
error_message
retry_count
can_retry
```

---

## 30. Ask AI Behavior

Ask AI nên ưu tiên:

```text
1. Published wiki pages
2. Accepted knowledge units
3. Source chunks
4. Draft knowledge only if user explicitly includes drafts
```

Rules:

```text
- Answers must include citations/source references.
- Ask AI must not use rejected knowledge units.
- Draft knowledge should not be used by default.
```

---

## 31. Acceptance Criteria

Update thành công khi:

```text
1. Existing ingestion still works.
2. Docling parsing and structure-aware chunking still work.
3. Heuristic extractors still work as fallback/hints.
4. LLM knowledge extraction can be enabled by config.
5. LLM entity extraction can be enabled by config.
6. LLM relation extraction can be enabled by config.
7. LLM timeline/glossary/page classification/BPM scoring can be enabled by config.
8. LLM page composer creates draft wiki pages with citations.
9. All LLM outputs are saved as draft by default.
10. Extraction runs are logged with model, prompt version, token usage, output count, and errors.
11. Source detail UI shows knowledge units, entities, relations, timeline, glossary, BPM analysis, draft pages, and extraction runs.
12. Review actions allow accepting/rejecting/editing LLM-generated knowledge.
13. Ask AI prioritizes published/accepted knowledge over draft/raw chunks.
14. No LLM output is auto-published without review.
15. Tests or smoke scripts cover at least one end-to-end upload → parse → chunk → LLM extract → draft page → review flow.
```

---

## 32. Implementation Order

Làm tuần tự:

```text
1. Add/extend database models and migrations.
2. Add LLM config and LLM client abstraction.
3. Add extraction_runs logging.
4. Convert existing heuristic output into knowledge_units format.
5. Add LLM KnowledgeExtractor.
6. Add LLM EntityExtractor.
7. Add LLM PageComposer.
8. Add UI tabs for Knowledge Units and Extraction Runs.
9. Add Relation/Timeline/Glossary extractors.
10. Add PageClassifier and BPMScorer.
11. Add ConflictDetector.
12. Update Ask AI retrieval priority.
13. Add tests/smoke scripts.
14. Update README and docs.
```

---

## 33. Important Constraints

```text
Do not break existing Docker workflow.
Do not remove current regression/smoke scripts.
Do not introduce hard-coded provider keys.
Do not auto-publish LLM-generated content.
Do not delete current heuristic extractors.
Do not let LLM create facts without source evidence.
```

---

## 34. Short Prompt to Run Before Coding

Use this as the short instruction before giving the full plan to Codex / Claude Code:

```text
Read the current codebase first. Then implement this upgrade plan carefully and incrementally. Preserve existing behavior, migrations, Docker setup, and tests. When uncertain, add config flags and keep old heuristic behavior as fallback rather than deleting it.
```
