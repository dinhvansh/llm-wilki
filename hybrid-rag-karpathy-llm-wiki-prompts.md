# Hybrid RAG + Karpathy LLM Wiki + Obsidian-like UI Prompts

Dưới đây là bộ prompt để phát triển hệ thống theo hướng:

- Hybrid RAG + Wiki
- Upload tài liệu gốc
- AI tự phân tích và auto-link
- Sinh ra các page như summary / concept / SOP / entity / timeline / issue / glossary
- Có graph kiểu Obsidian
- Có cơ chế sửa hệ thống hiện tại thành kiểu đó

---

## 1) Prompt tổng: phát triển hệ thống theo hướng Hybrid RAG + Karpathy LLM Wiki + Obsidian-like UI

```text
Tôi muốn bạn đóng vai Senior Product Architect + Senior Full Stack Engineer để phân tích và nâng cấp hệ thống hiện tại của tôi theo mô hình hybrid:

1. Document ingestion / RAG
2. AI-generated Wiki
3. Human-editable knowledge base
4. Obsidian-like navigation and graph visualization

## Mục tiêu sản phẩm
Tôi không muốn hệ thống chỉ là một chat với tài liệu (RAG thuần), cũng không muốn chỉ là một app note-taking thủ công kiểu markdown editor đơn giản.

Tôi muốn một hệ thống kết hợp cả hai:
- Người dùng có thể upload tài liệu gốc: PDF, DOCX, TXT, web content, image OCR, transcript
- AI phân tích tài liệu gốc để tạo ra tri thức có cấu trúc
- Hệ thống sinh ra nhiều loại wiki page khác nhau
- Người dùng có thể chỉnh sửa thủ công như một knowledge base sống
- Hệ thống tự động link tài liệu mới với page / entity / issue / timeline phù hợp
- Có graph view kiểu Obsidian để nhìn mối quan hệ giữa các page

## Tư duy thiết kế cốt lõi
Tôi muốn hệ thống đi theo mô hình:

Raw Sources -> Parse / Chunk / Extract -> AI Analysis -> Structured Wiki Pages -> Human Review / Edit -> Publish -> Search / Query / Graph / Lint

Không được chỉ làm kiểu:
- upload file
- chunk
- hỏi đáp
- xong là hết

Tôi muốn “tri thức tích lũy được theo thời gian”.

## Kiến trúc cốt lõi mong muốn

### A. Tầng Source / Document Layer
Hệ thống phải hỗ trợ:
- Upload tài liệu
- Lưu metadata của tài liệu
- Parse nội dung
- OCR nếu cần
- Chunk nội dung
- Index semantic search / full-text search
- Lưu raw source để trace ngược

Mỗi source cần có:
- source_id
- title
- type
- original file
- extracted text
- created_at
- updated_at
- collection_id (nullable)
- tags
- entities extracted
- status

### B. Tầng Knowledge Extraction
AI cần phân tích từ bản gốc để phát hiện:
- summary
- concepts
- SOP-like instructions
- entities
- events / timeline entries
- issues / problems
- glossary terms

Không được bịa. Mọi nội dung sinh ra phải có khả năng trace ngược về source.

### C. Tầng Wiki Pages
Hệ thống cần hỗ trợ các page type sau:

1. Summary page
- Tóm tắt một tài liệu, một bộ tài liệu, hoặc một chủ đề

2. Concept page
- Giải thích một khái niệm / thuật ngữ / idea

3. SOP page
- Hướng dẫn thao tác từng bước

4. Entity page
- Hồ sơ của một thực thể cụ thể: người, công ty, hệ thống, dự án, văn bản, sản phẩm...

5. Timeline page
- Trình bày diễn biến theo thời gian

6. Issue page
- Hồ sơ theo dõi một vấn đề / lỗi / tranh chấp / rủi ro / điểm cần xử lý

7. Glossary page
- Danh sách thuật ngữ và định nghĩa ngắn

Mỗi page cần có:
- page_id
- title
- slug
- page_type
- content_md
- summary
- linked_sources
- linked_entities
- linked_pages
- citations
- status (draft / review / published)
- last_generated_at
- last_reviewed_at
- updated_by
- confidence_score (nếu phù hợp)

### D. Auto-linking
Khi người dùng upload thêm tài liệu mới, hệ thống KHÔNG bắt buộc họ phải vào đúng collection/page để upload.

Tôi muốn mặc định hệ thống:
- tự phân tích tài liệu mới
- tự phát hiện collection liên quan
- tự phát hiện page nào bị ảnh hưởng
- tự phát hiện entity / issue / timeline liên quan
- tự đề xuất update cho page cũ
- hoặc tạo page mới nếu đây là chủ đề mới

Tuy nhiên phải cho phép user:
- accept suggestion
- reject suggestion
- đổi sang collection khác
- để tài liệu standalone

Tôi muốn mô hình:
auto link + suggest update + human override

### E. Editing / Review workflow
Tôi muốn người dùng có thể:
- đọc page dạng preview đẹp
- chỉnh sửa page dưới dạng markdown
- xem source evidence
- xem diff AI đề xuất trước khi accept
- xem thay đổi lịch sử
- xem backlinks
- xem related pages

### F. Lint / Quality layer
Tôi muốn hệ thống có “wiki lint” để kiểm tra chất lượng tri thức:
- orphan pages
- broken links
- stale pages
- claims thiếu citation
- conflicting pages
- duplicate pages
- thin pages
- entity chưa có page
- timeline thiếu mốc
- issue chưa có owner / status

Cần có Lint Center để hiển thị các vấn đề này.

## Yêu cầu UI/UX
Tôi muốn UI theo tinh thần:
- sạch
- chuyên nghiệp
- thiên về knowledge work
- dễ đọc
- ít màu mè
- phù hợp với dữ liệu lớn
- cảm giác như kết hợp giữa Obsidian + NotebookLM + Wiki nội bộ

### Layout đề xuất
- Left sidebar:
  - Workspace / Collections
  - Page tree
  - Source library
  - Saved views

- Main content:
  - Page view / editor
  - Source view
  - Search results
  - Graph view
  - Lint view

- Right sidebar:
  - Metadata
  - Backlinks
  - Related pages
  - Citations
  - Change history
  - AI suggestions

### Core modules cần có
1. Dashboard
2. Source Library
3. Collection View
4. Wiki Page View
5. Markdown Editor + Preview
6. AI Suggest Update Panel
7. Graph View
8. Search / Ask View
9. Lint Center
10. Entity Explorer
11. Timeline Explorer
12. Review Queue

## Graph visualization (rất quan trọng)
Tôi thích graph kiểu Obsidian và muốn sửa graph hiện tại của tôi thành phong cách đó.

Graph cần:
- hiển thị các page như node
- hiển thị các liên kết giữa page như edge
- có thể zoom / pan / drag
- click node để mở page
- hover node để highlight neighbors
- có local graph mode và global graph mode
- node size phản ánh mức độ kết nối
- node color phản ánh page type hoặc status
- hỗ trợ filter theo:
  - page type
  - collection
  - status
  - orphan
  - stale
- hỗ trợ search node
- hỗ trợ toggle labels
- labels chỉ nên hiện hợp lý, tránh rối
- graph phải tối giản, không quá flashy
- graph dùng như công cụ quan sát tri thức, không chỉ để trang trí

## Phong cách graph mong muốn
Tôi muốn graph có cảm giác giống Obsidian:
- nền tối hoặc nền sáng nhẹ đều được, nhưng phải tinh gọn
- nodes nhỏ, gọn, mềm
- edges mảnh, nhẹ
- tổng thể tối giản
- khi hover/click thì vùng liên quan nổi bật lên
- cho cảm giác “knowledge constellation” / “brain map”
- không làm kiểu biểu đồ enterprise quá nặng nề
- không làm kiểu visual noise

Nhưng tôi muốn cải tiến hơn Obsidian ở chỗ:
- có semantic meaning
- color by page type
- node states rõ ràng
- support orphan/stale/conflict highlight
- click node thấy metadata + citations + related sources

## Yêu cầu kỹ thuật
Trước khi code, hãy:
1. phân tích hệ thống hiện tại
2. xác định những phần đang có thể giữ lại
3. đề xuất refactor plan thay vì viết lại vô tội vạ
4. chỉ ra gap giữa implementation hiện tại và target architecture

Sau đó hãy cung cấp:

### 1. Kiến trúc đề xuất
- system architecture
- data flow
- entity relationship
- indexing flow
- AI generation flow
- review/publish flow
- auto-link flow

### 2. Database schema đề xuất
Bao gồm các bảng chính như:
- sources
- source_chunks
- collections
- pages
- page_links
- entities
- page_entities
- citations
- issues
- timeline_events
- glossary_terms
- ai_jobs
- page_revisions
- lint_results

### 3. UI sitemap
- toàn bộ màn hình
- điều hướng
- page hierarchy

### 4. Component architecture
- component tree
- reusable component strategy
- graph module
- page editor module
- source viewer
- right panel

### 5. Implementation plan
- phase 1
- phase 2
- phase 3
- phase 4

### 6. Code
Viết code production-oriented, rõ ràng, dễ maintain.

## Tech stack ưu tiên
Nếu cần giả định stack, mặc định dùng:
- Frontend: React + TypeScript
- UI: Tailwind CSS + shadcn/ui
- Markdown editor: tiptap / code editor phù hợp
- Graph: React Flow hoặc force-graph / d3 phù hợp
- Backend: Node.js / Next.js / NestJS đều được, miễn thiết kế tốt
- Database: PostgreSQL
- Search: PostgreSQL full text + vector search
- AI orchestration: background jobs / queue
- File storage: local trước, dễ migrate sang S3 sau

## Điều quan trọng
- Không chỉ mô tả lý thuyết
- Không làm MVP quá sơ sài
- Phải đưa ra thiết kế đủ rõ để có thể code
- Phải ưu tiên khả năng mở rộng sau này
- Phải ưu tiên traceability từ wiki page về raw source
- Phải ưu tiên AI-assisted knowledge maintenance chứ không chỉ chat answer

## Cách trả lời mong muốn
Hãy trả lời theo cấu trúc:
1. Phân tích hệ thống hiện tại và gap
2. Kiến trúc đích
3. Data model
4. UX/UI proposal
5. Graph redesign proposal
6. Refactor plan
7. Implementation plan
8. Code mẫu cho các module quan trọng
9. Rủi ro / edge cases / đề xuất tiếp theo

Bắt đầu bằng việc phân tích hệ thống hiện tại và đề xuất hướng refactor, sau đó mới đi tới thiết kế chi tiết.
```

---

## 2) Prompt riêng: sửa biểu đồ / graph hiện tại thành kiểu Obsidian-like

```text
Tôi đã có một graph visualization trong hệ thống hiện tại, nhưng tôi muốn bạn phân tích và redesign nó theo phong cách Obsidian Graph View, đồng thời nâng cấp để phù hợp với một AI-powered wiki / knowledge graph system.

## Mục tiêu
Tôi không muốn graph chỉ là một biểu đồ đẹp.
Tôi muốn nó trở thành một công cụ quan sát tri thức:
- xem mối quan hệ giữa các page
- phát hiện hub pages
- phát hiện orphan pages
- phát hiện cluster chủ đề
- hỗ trợ điều hướng trong knowledge base
- thể hiện trạng thái tri thức

## Yêu cầu phong cách
Tôi thích graph kiểu Obsidian:
- tối giản
- tinh gọn
- cảm giác “network of thoughts”
- node nhỏ, nhẹ
- edge mảnh
- không quá nhiều text gây rối
- hover/click thì vùng liên quan nổi bật
- zoom/pan mượt
- tổng thể clean và dễ nhìn

## Tôi muốn sửa graph hiện tại theo các tiêu chí sau

### 1. Visual style
- nền tối hoặc nền sáng nhẹ, nhưng phải tối giản
- nodes là các chấm hoặc shape nhỏ, tinh gọn
- edges mỏng, nhẹ, opacity thấp
- khi hover node:
  - highlight node đó
  - highlight first-degree neighbors
  - fade các node/edge không liên quan
- khi click node:
  - pin selection
  - hiện panel chi tiết ở bên phải

### 2. Semantic meaning
Graph không được chỉ hiển thị node giống nhau hết.
Tôi muốn:
- màu node theo page type:
  - summary
  - concept
  - SOP
  - entity
  - timeline
  - issue
  - glossary
- kích thước node theo mức độ kết nối hoặc importance
- trạng thái node có thể biểu thị bằng viền hoặc style:
  - stale
  - orphan
  - draft
  - published
  - conflict
  - needs review

### 3. Interaction
Graph phải hỗ trợ:
- zoom
- pan
- drag node
- search node
- click node để mở page
- hover node để xem tooltip
- local graph mode
- global graph mode
- expand neighbors
- filter by collection
- filter by page type
- filter by status
- filter orphan/stale/conflict

### 4. Label behavior
- không hiển thị label toàn bộ mọi lúc nếu gây rối
- label chỉ nên hiện khi:
  - hover
  - zoom đủ gần
  - selected
  - hoặc khi người dùng bật toggle labels
- cần thuật toán hiển thị label hợp lý để tránh đè lên nhau

### 5. Analytical features
Tôi muốn graph hỗ trợ:
- highlight orphan pages
- highlight high-degree nodes / hubs
- highlight disconnected clusters
- highlight pages recently updated
- show related sources count
- optionally show edge types:
  - links to
  - mentions
  - derived from
  - related to

### 6. Layout logic
Tôi muốn layout có cảm giác organic như Obsidian, nhưng không quá random.
Có thể dùng force-directed layout.
Cần tối ưu để:
- ít chồng chéo
- dễ nhìn cluster
- mượt khi số lượng node tăng

### 7. Right detail panel khi click node
Khi click node, panel phải hiện:
- title
- page type
- summary ngắn
- metadata
- linked pages
- backlinks
- linked sources
- citations count
- page status
- quick actions:
  - open page
  - open local graph
  - filter by this type
  - inspect related sources

### 8. Yêu cầu kỹ thuật
Trước tiên, hãy:
1. review graph implementation hiện tại
2. chỉ ra điểm nào đang chưa tốt
3. đưa ra proposal để sửa thành Obsidian-like graph

Sau đó hãy cung cấp:
- UI/UX explanation
- component structure
- graph data model
- rendering strategy
- performance strategy
- code / refactor plan

## Tech stack ưu tiên
- React + TypeScript
- Graph library phù hợp: React Flow / d3-force / force-graph / cytoscape tùy bạn đề xuất
- code phải dễ maintain
- hỗ trợ dữ liệu lớn hơn về sau

## Tôi muốn đầu ra
Hãy trả lời theo cấu trúc:
1. Đánh giá graph hiện tại
2. Obsidian-like design principles
3. Visual redesign proposal
4. Interaction redesign proposal
5. Data model mapping
6. Performance considerations
7. Refactor plan
8. Code mẫu hoặc implementation skeleton

Hãy ưu tiên hướng thực tế, có thể áp dụng để sửa graph hiện tại chứ không chỉ mô tả chung chung.
```

---

## 3) Mô tả ngắn để AI hiểu “biểu đồ kiểu đó” là kiểu gì

```text
Tôi muốn graph có phong cách giống Obsidian Graph View:
- tối giản, sạch, nhẹ
- node nhỏ như các điểm tri thức
- edge mảnh, opacity thấp
- tổng thể giống một mạng lưới ý tưởng / bản đồ tri thức
- khi hover/click thì vùng liên quan nổi bật rõ, phần còn lại mờ đi
- không hiển thị quá nhiều label gây rối
- cảm giác organic, tự nhiên, không cứng
- graph phục vụ điều hướng và quan sát tri thức, không phải chỉ để trang trí

Tôi muốn nâng cấp hơn Obsidian ở chỗ:
- node có semantic meaning rõ ràng
- color theo loại page
- style theo trạng thái page
- có local graph / global graph
- có search / filter / right-side detail panel
- hỗ trợ phát hiện orphan, stale, conflict, hub pages
```

---

## 4) Gợi ý thêm cho AI code

Nếu đang quăng cho AI code, nên thêm đoạn này để nó không đi lệch:

```text
Đừng chỉ build một graph đẹp.
Hãy build một graph có giá trị thật cho knowledge workflow:
- hỗ trợ điều hướng
- hỗ trợ phân tích
- hỗ trợ review tri thức
- hỗ trợ phát hiện vấn đề trong wiki
```

---

## 5) Gợi ý bước tiếp theo

Nếu muốn mở rộng tiếp, có thể làm thêm các prompt riêng cho:

1. Database schema
2. UI/UX screen-by-screen
3. Module graph + page + source + auto-link
4. Review queue + lint center
5. AI ingest pipeline

