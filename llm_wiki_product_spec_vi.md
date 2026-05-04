# Tài liệu đặc tả phát triển hệ thống LLM Wiki / AI Knowledge Base

## 1. Mục tiêu tài liệu
Tài liệu này dùng làm đầu bài cho AI agent hoặc đội phát triển để xây dựng một hệ thống **LLM Wiki / AI Knowledge Base** có khả năng:
- ingest tài liệu từ nhiều nguồn
- parse, chunk, extract tri thức
- tự động soạn thảo wiki page
- kiểm tra citation, conflict, stale content
- hỗ trợ hỏi đáp trên knowledge base
- có thể vận hành với hoặc không có human review

Mục tiêu cuối cùng là tạo ra một hệ thống knowledge base có cấu trúc, có khả năng truy vết nguồn, có trải nghiệm UI tốt, và đủ linh hoạt để dùng cho tài liệu kỹ thuật, SOP, policy, compliance, hoặc knowledge base nội bộ doanh nghiệp.

---

## 2. Bối cảnh sản phẩm
Hệ thống cần kết hợp 4 lớp chính:
1. **Source Layer**: lưu và quản lý tài liệu gốc
2. **Knowledge Extraction Layer**: parse, chunk, embedding, entity, claim, relation
3. **Wiki Composition Layer**: xây và cập nhật page wiki từ knowledge đã extract
4. **Review + Query Layer**: review chất lượng nội dung, hiển thị page, hỏi đáp và truy xuất nguồn

Sản phẩm không chỉ là một chatbot. Sản phẩm phải là một **AI-powered knowledge workspace** gồm cả:
- trang wiki
- knowledge graph
- source explorer
- review queue
- hỏi đáp có citation

---

## 3. Mục tiêu sản phẩm

### 3.1 Mục tiêu chính
- Biến tài liệu rời rạc thành hệ thống wiki có cấu trúc
- Cho phép AI tự tạo và cập nhật page từ source
- Mọi claim quan trọng cần truy vết được về source/chunk
- Hỗ trợ navigation qua page, graph, source, tag
- Hỗ trợ hỏi đáp trên knowledge base với citation rõ ràng

### 3.2 Mục tiêu UX
- Người dùng nhìn vào là hiểu wiki đang có gì
- Người dùng biết nội dung này đến từ đâu
- Người dùng phân biệt được page nào đã publish, draft, unverified, needs review
- Người dùng có thể click từ page -> claim -> chunk -> source

### 3.3 Mục tiêu kỹ thuật
- Kiến trúc modular, dễ mở rộng
- Hỗ trợ background jobs
- Có thể thay model và vector store
- Có thể chạy local hoặc cloud
- Có API rõ ràng để front-end và AI agent cùng dùng

---

## 4. Phạm vi tính năng

### 4.1 In scope
- Upload và quản lý source
- Parse tài liệu và chunking
- Extract entity / claim / relation / tag
- Embedding và semantic retrieval
- Generate draft wiki page
- Review quality: citation, conflict, stale content
- Publish / unpublish / version page
- Search và Ask AI trên knowledge base
- Knowledge graph
- Dashboard quản trị

### 4.2 Out of scope cho phiên bản đầu
- OCR quá phức tạp cho file scan xấu
- Cộng tác thời gian thực kiểu Google Docs
- Permission quá chi tiết theo từng block nội dung
- Workflow approval nhiều cấp phức tạp
- Full multilingual localization

---

## 5. Đối tượng người dùng

### 5.1 Admin / Knowledge Manager
- upload source
- trigger ingest/rebuild
- review draft
- publish page
- theo dõi job và quality

### 5.2 Reader / End User
- đọc page wiki
- search
- hỏi đáp
- xem citation
- mở source liên quan

### 5.3 Reviewer / Subject Matter Expert
- kiểm tra claim conflict
- duyệt draft
- chỉnh sửa nội dung nhạy cảm
- xác nhận source nào là authoritative

---

## 6. Luồng nghiệp vụ tổng thể

### 6.1 Luồng ingest
1. User upload source
2. System lưu file + metadata
3. Ingest Agent parse nội dung
4. Hệ thống chunk theo heading/section/token window
5. Extract entity, claim, relation, tags
6. Tạo embedding và index
7. Gắn source vào các page liên quan hoặc tạo gợi ý page mới

### 6.2 Luồng compose page
1. Page Composer Agent chọn source/chunk/claim liên quan
2. Tạo hoặc cập nhật draft page
3. Chèn cấu trúc section
4. Tạo citation map
5. Tạo related pages / related entities
6. Lưu diff so với bản trước nếu page đã tồn tại

### 6.3 Luồng review
1. Reviewer Agent quét draft
2. Kiểm tra citation thiếu
3. Kiểm tra claim conflict
4. Kiểm tra stale content
5. Nếu pass thì auto publish hoặc mark ready
6. Nếu fail hoặc risk cao thì chuyển review queue

### 6.4 Luồng publish
- Draft -> Reviewed -> Published
- Published page cần có version, updated_at, reviewer, source coverage

### 6.5 Luồng hỏi đáp
1. User nhập câu hỏi
2. System retrieve relevant pages/chunks/claims
3. AI trả lời grounded answer
4. Hiển thị citations, related pages, related sources
5. Có thể lưu câu trả lời thành note hoặc draft page

---

## 7. Kiến trúc agent

## 7.1 Ingest Agent
### Nhiệm vụ
- parse file
- normalize text
- detect heading/section
- chunking
- entity extraction
- claim extraction
- relation extraction
- tagging

### Input
- file gốc
- metadata nguồn

### Output
- parsed_source
- chunks
- entities
- claims
- relations
- embeddings

### Quy tắc
- ưu tiên giữ context section
- chunk không được cắt mất nghĩa
- lưu reference tới page number / section / source span nếu có
- mọi claim phải link về ít nhất 1 chunk

## 7.2 Page Composer Agent
### Nhiệm vụ
- chọn claims/chunks liên quan
- nhóm nội dung theo topic
- viết draft page dạng markdown
- thêm summary, key facts, related pages
- thêm citation theo section hoặc claim

### Input
- topic hoặc page id
- chunks liên quan
- claims liên quan
- existing page nếu có

### Output
- draft page markdown
- citation map
- diff/change summary
- related pages

### Quy tắc
- không được bịa thông tin ngoài source nếu không được đánh dấu inference
- ngôn ngữ rõ ràng, có cấu trúc, dễ đọc
- mỗi section chính phải có grounding từ source

## 7.3 Reviewer Agent
### Nhiệm vụ
- kiểm tra missing citation
- kiểm tra unsupported claim
- phát hiện conflict giữa claim/source
- phát hiện stale content
- tính confidence score
- gắn cờ để human review nếu cần

### Input
- draft page
- citation map
- related sources/chunks/claims
- version hiện tại của page

### Output
- quality report
- list issue
- decision suggestion: pass / review / reject

### Quy tắc
- không tự override authoritative source nếu có conflict nghiêm trọng
- phải giải thích lý do gắn cờ
- stale content cần nêu rõ source nào mới hơn

---

## 8. Human-in-the-loop

### 8.1 Nguyên tắc
Hệ thống phải hỗ trợ cả 2 mode:
- **Auto mode**: tự publish khi confidence cao và không có cờ đỏ
- **Review mode**: cần reviewer duyệt khi có issue hoặc topic nhạy cảm

### 8.2 Khi nào bắt buộc human review
- claim conflict
- missing citation ở section quan trọng
- source mới mâu thuẫn source cũ
- policy / legal / compliance page
- confidence thấp
- external authoritative source thay đổi version

### 8.3 Khi nào có thể auto publish
- topic low-risk
- citation coverage đạt ngưỡng
- không có conflict
- source trusted
- draft thay đổi nhỏ

### 8.4 Review actions
- approve
- reject
- edit manually
- mark source authoritative
- request rebuild

---

## 9. Cấu trúc thông tin và điều hướng

### 9.1 Loại page
- Summary
- Overview
- Deep Dive
- Entity
- Source-derived page
- FAQ / Glossary

### 9.2 Quan hệ page
- parent / child
- related_to
- derived_from
- mentions
- supersedes
- depends_on

### 9.3 Điều hướng chính
- Dashboard
- Sources
- Pages
- Graph
- Review Queue
- Ask AI
- Settings

---

## 10. Yêu cầu giao diện

## 10.1 Dashboard
Hiển thị:
- Total Sources
- Total Pages
- Draft Pages
- Published Pages
- Unverified Claims
- Review Queue Count
- Last Sync Time
- Recent Activity
- Failed Jobs

## 10.2 Sources
Tính năng:
- drag/drop upload
- danh sách source
- filter theo loại, tag, status
- preview source
- xem extracted chunks
- xem entities/claims
- xem affected pages
- rebuild source

## 10.3 Source Detail
Tabs:
- Overview
- Chunks
- Extracted Claims
- Extracted Entities
- Related Pages
- Job Logs

## 10.4 Pages
- cây điều hướng page
- search page
- filter theo type/status/tag
- list page card hoặc table

## 10.5 Page Detail
Layout đề xuất 3 cột:
- trái: page tree / page list / search
- giữa: nội dung page markdown render
- phải: citations / related pages / related entities / source snippets / status / confidence

Page detail cần có:
- title
- page type
- status badge
- summary
- content sections
- key facts
- related pages
- related sources
- last updated
- version
- reviewer info nếu có

## 10.6 Review Queue
Phải có:
- danh sách draft cần review
- severity badge
- issue type: missing citation / conflict / stale / unsupported claim
- diff view old vs new
- evidence panel hiển thị source snippets
- approve / reject / edit / send back

## 10.7 Ask AI
Phải có:
- input câu hỏi
- grounded answer
- citations rõ ràng
- related pages
- related sources
- khả năng mở page liên quan
- optional: save as note / save as page draft

## 10.8 Knowledge Graph
- mỗi node là page hoặc entity tùy mode
- edge thể hiện quan hệ
- click node để mở page
- zoom/pan
- filter theo page type/tag/cluster
- highlight central node / selected node

---

## 11. Mô hình dữ liệu đề xuất

## 11.1 sources
Các trường tối thiểu:
- id
- title
- source_type
- mime_type
- file_path hoặc url
- uploaded_at
- updated_at
- created_by
- parse_status
- ingest_status
- metadata_json
- checksum
- trust_level

## 11.2 source_chunks
- id
- source_id
- chunk_index
- section_title
- page_number nếu có
- content
- token_count
- embedding_vector hoặc embedding_id
- span_start
- span_end
- created_at

## 11.3 entities
- id
- name
- entity_type
- description
- aliases
- normalized_name
- created_at

## 11.4 claims
- id
- text
- claim_type
- confidence_score
- source_chunk_ids
- canonical_status
- review_status
- extracted_at

## 11.5 claim_relations
- id
- from_claim_id hoặc from_entity_id
- to_claim_id hoặc to_entity_id
- relation_type
- confidence_score

## 11.6 pages
- id
- slug
- title
- page_type
- status
- summary
- content_md
- content_html cache optional
- current_version
- last_composed_at
- last_reviewed_at
- published_at
- owner

## 11.7 page_versions
- id
- page_id
- version_no
- content_md
- change_summary
- created_at
- created_by_agent_or_user
- review_status

## 11.8 page_claim_links
- id
- page_id
- claim_id
- section_key
- citation_style

## 11.9 page_links
- id
- from_page_id
- to_page_id
- relation_type
- auto_generated boolean

## 11.10 jobs
- id
- job_type
- status
- started_at
- finished_at
- input_ref
- output_ref
- error_message
- logs_json

---

## 12. API/Service contract gợi ý

### 12.1 Source APIs
- `POST /api/sources/upload`
- `GET /api/sources`
- `GET /api/sources/{id}`
- `POST /api/sources/{id}/rebuild`
- `GET /api/sources/{id}/chunks`
- `GET /api/sources/{id}/claims`
- `GET /api/sources/{id}/affected-pages`

### 12.2 Page APIs
- `GET /api/pages`
- `GET /api/pages/{slug}`
- `POST /api/pages/compose`
- `POST /api/pages/{id}/publish`
- `POST /api/pages/{id}/unpublish`
- `GET /api/pages/{id}/versions`
- `GET /api/pages/{id}/diff/{version}`

### 12.3 Review APIs
- `GET /api/review-queue`
- `GET /api/review-items/{id}`
- `POST /api/review-items/{id}/approve`
- `POST /api/review-items/{id}/reject`
- `POST /api/review-items/{id}/request-rebuild`

### 12.4 Query APIs
- `POST /api/ask`
- `GET /api/search?q=`
- `GET /api/graph`

---

## 13. Trạng thái hệ thống

### 13.1 Source status
- uploaded
- parsing
- parsed
- chunked
- extracted
- indexed
- failed

### 13.2 Page status
- draft
- in_review
- reviewed
- published
- stale
- archived

### 13.3 Review issue types
- missing_citation
- unsupported_claim
- conflict_detected
- stale_content
- low_confidence
- broken_source_reference

---

## 14. Luật nghiệp vụ quan trọng

1. Mọi page published phải có ít nhất 1 source liên kết
2. Mọi claim quan trọng phải truy ra được chunk/source
3. Nếu source authoritative mới hơn source hiện tại thì page liên quan phải bị đánh dấu stale hoặc queued for review
4. Nếu có conflict nghiêm trọng thì không auto publish
5. Draft mới phải lưu diff so với version hiện tại nếu page đã tồn tại
6. Source bị xóa không được làm mất hẳn lịch sử page version
7. Ask AI chỉ được trả lời dựa trên knowledge đã index, hoặc nếu có inference thì phải đánh dấu rõ

---

## 15. Gợi ý công nghệ

### 15.1 Frontend
- React + TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Table
- React Query
- Recharts cho dashboard
- React Flow hoặc thư viện graph/network cho knowledge graph
- Markdown renderer có support heading, link, code, table

### 15.2 Backend
- FastAPI hoặc Next.js backend
- PostgreSQL
- pgvector hoặc Qdrant cho vector search
- Redis cho queue/cache nếu cần
- Background job runner: Celery / RQ / BullMQ / Temporal tùy stack

### 15.3 Parser / processing
- PyMuPDF hoặc unstructured cho PDF
- text splitter tùy chỉnh theo heading + token window
- embedding service có thể thay thế linh hoạt
- model orchestration cho agent workflow

---

## 16. Nguyên tắc UX/UI

1. Không làm sản phẩm chỉ như một chatbot
2. Page phải là đối tượng trung tâm
3. Citation phải nhìn thấy rõ và click được
4. Từ page phải truy ngược được về source
5. Review queue phải dễ hiểu, ít thao tác
6. Graph là phần hỗ trợ khám phá, không thay thế navigation chính
7. Màu badge cần phân biệt rõ draft / published / stale / needs review
8. UI cần sạch, hiện đại, dễ scan, thiên về knowledge work

---

## 17. Phiên bản MVP đề xuất

### Phase 1: Core pipeline
- upload source
- parse + chunk
- extract basic claims/entities
- create page draft
- page list + page detail
- ask AI có citation

### Phase 2: Review & publish
- review queue
- diff view
- publish workflow
- stale detection
- conflict detection cơ bản

### Phase 3: Advanced knowledge UX
- knowledge graph
- source-to-page lineage
- auto related pages
- page versioning nâng cao
- source trust scoring

---

## 18. Tiêu chí nghiệm thu

### 18.1 Source
- upload thành công file PDF/MD/TXT cơ bản
- parse được nội dung và tạo chunk
- source detail hiển thị chunks và claims

### 18.2 Page
- system tạo được page draft từ source
- page render markdown tốt
- page có section rõ ràng
- page hiển thị citations và related pages

### 18.3 Review
- review queue hiển thị các issue
- diff giữa old/new nhìn rõ
- approve/reject hoạt động đúng
- page conflict không được auto publish

### 18.4 Query
- Ask AI trả lời có grounding
- citations mở ra được page/source liên quan
- câu trả lời không được hoàn toàn bịa ngoài source

### 18.5 Performance
- source nhỏ xử lý trong thời gian hợp lý
- page load mượt với danh sách vài trăm page
- search phản hồi nhanh trong giới hạn MVP

---

## 19. Prompt điều phối cho AI phát triển
Dùng đoạn dưới đây làm đầu bài trực tiếp cho AI coding agent:

> Hãy phát triển một ứng dụng web LLM Wiki / AI Knowledge Base theo các yêu cầu trong tài liệu này. Ưu tiên kiến trúc sạch, type rõ ràng, component tái sử dụng được, và trải nghiệm người dùng giống một knowledge workspace hơn là chatbot đơn thuần. Bắt đầu bằng việc tạo kiến trúc thư mục, schema dữ liệu, API contract, seed data giả lập, rồi xây từng màn chính theo thứ tự: Dashboard, Sources, Page List, Page Detail, Review Queue, Ask AI, Knowledge Graph. Với mỗi màn, cần có loading state, empty state, error state. Phần Page Detail và Review Queue là quan trọng nhất. Hãy dùng mock data trước, sau đó tách service layer để dễ nối backend thật.

---

## 20. Yêu cầu coding standards
- Tách business logic khỏi UI
- Component nhỏ, tái sử dụng được
- Đặt tên rõ ràng, tránh viết tắt khó hiểu
- Type đầy đủ cho model chính
- Có mock data và mock API để UI chạy độc lập
- Có trạng thái loading / empty / error ở mọi page quan trọng
- Không hardcode dữ liệu vào component nếu có thể tách ra file riêng
- Dễ mở rộng sang backend thật

---

## 21. Deliverables mong muốn từ AI developer
1. Cấu trúc thư mục dự án
2. Schema dữ liệu chính
3. Bộ mock data đủ dùng
4. UI các màn chính hoàn chỉnh
5. Service layer / API abstraction
6. Workflow ingest -> compose -> review -> publish ở mức mô phỏng
7. README hướng dẫn chạy local
8. Ghi chú phần nào đang mock, phần nào đã thực thi thật

---

## 22. Kết luận
Sản phẩm cần được xây như một **AI-native wiki platform** có:
- source grounding
- traceability
- structured pages
- reviewability
- queryability

Không xây như chatbot đơn giản. Không chỉ tập trung vào trả lời câu hỏi. Trọng tâm là **tri thức có cấu trúc, có nguồn, có version, có thể review, và dễ khai thác bằng giao diện tốt**.
