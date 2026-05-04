# Hướng Dẫn Sử Dụng LLM Wiki

Tài liệu này dành cho người dùng vận hành hệ thống hằng ngày: editor, reviewer, admin, và người đọc nội bộ.

## 1. Mục tiêu của hệ thống

LLM Wiki dùng để:

- thu thập tài liệu nguồn từ file, URL, hoặc pasted text
- trích xuất và tổ chức thành trang wiki có citation
- duy trì review trước khi publish
- hỗ trợ hỏi đáp có dẫn chứng
- theo dõi chất lượng tri thức qua graph, lint, audit, job, và admin metrics

## 2. Vai trò người dùng

### Reader

- xem dashboard, sources, pages, ask, graph, lint
- không được sửa dữ liệu nhạy cảm

### Editor

- ingest source
- chỉnh sửa page
- tạo draft từ chunks
- save câu trả lời Ask thành draft
- archive/restore source
- chạy bulk actions hợp lệ

### Reviewer

- review approve/reject/merge
- comment trên review item
- phối hợp với editor để chốt nội dung trước publish

### Admin

- toàn quyền editor + reviewer
- chỉnh Settings
- xem Operations dashboard
- export/import config
- bulk retry failed jobs

## 3. Đăng nhập

Màn hình login dùng token Bearer.

Tài khoản dev mặc định:

- Email: `admin@local.test`
- Password: `admin123`

Sau khi login:

- token được frontend lưu local
- menu người dùng hiển thị role hiện tại
- action không đủ quyền sẽ bị ẩn hoặc disable

## 4. Tổng quan menu

### Dashboard

Dùng để xem:

- số lượng source, page, review item, job
- trạng thái hệ thống tổng quan
- điểm bắt đầu nhanh để đi vào sources/pages/review

### Collections

Dùng để nhóm knowledge theo domain, ví dụ:

- compliance
- engineering
- operations

Collections ảnh hưởng tới:

- filter sources
- filter pages
- filter graph
- filter lint

### Sources

Nơi ingest và quản lý tài liệu nguồn.

Các thao tác chính:

- upload file
- ingest URL
- ingest pasted text/transcript
- xem chunks, claims, entities, affected pages
- xem suggestions sau ingest
- rebuild source
- refresh URL source
- archive/restore source

### Pages

Nơi duyệt và chỉnh sửa wiki pages.

Các thao tác chính:

- xem page detail
- xem citations/backlinks
- xem version history
- xem audit trail
- update draft
- restore version cũ thành draft mới
- publish/unpublish
- tạo page từ selected chunks

### Review Queue

Nơi reviewer xử lý thay đổi AI-generated hoặc tín hiệu conflict/stale.

Các thao tác chính:

- approve
- reject
- merge
- create issue page
- comment thread

### Lint Center

Dùng để phát hiện page quality issues.

Ví dụ:

- thiếu source
- thiếu citation
- duplicate page
- stale source
- issue page thiếu owner/status

Một số quick fix an toàn có thể chạy trực tiếp.

### Ask AI

Hỏi đáp grounded bằng chunk/source thật.

Các thao tác chính:

- hỏi câu hỏi mới
- mở lịch sử chat
- xem citations
- mở source chunk liên quan
- save answer thành draft page

### Knowledge Graph

Hiển thị network tri thức giữa pages, entities, relationships.

Dùng để:

- phát hiện orphan/hub/conflict/stale
- nhìn local graph hoặc global graph
- điều hướng nhanh sang page/source liên quan

### Settings

Chỉ admin dùng để cấu hình:

- answer model
- ingest model
- embedding model
- chunking
- retrieval limits
- graph/lint/search guardrails

### Operations

Chỉ admin.

Dùng để:

- xem backlog jobs
- xem failed jobs
- bulk retry failed jobs
- xem config runtime

## 5. Quy trình ingest source

### A. Upload file

1. Vào `Sources`
2. Chọn upload file
3. Chọn collection nếu muốn
4. Submit
5. Theo dõi job ở source detail

### B. Ingest URL

1. Vào `Sources`
2. Chọn URL
3. Nhập URL và optional title
4. Submit
5. Nếu là web page hợp lệ, hệ thống fetch text và tạo source

### C. Pasted text / transcript

1. Vào `Sources`
2. Chọn text hoặc transcript
3. Dán nội dung
4. Submit

Sau ingest, source thường đi qua các bước:

- parsing
- chunking
- claim extraction
- linking
- page generation
- review item generation nếu cần

## 6. Cách đọc Source Detail

Source Detail thường có các vùng sau:

- metadata
- chunks
- claims
- entities
- affected pages
- suggestions
- jobs

Nên dùng theo thứ tự:

1. xem source metadata và ingest status
2. kiểm tra chunks có đọc được không
3. kiểm tra claims/entities trích xuất
4. xem suggestions để quyết định link/merge
5. nếu có lỗi thì xem Jobs tab

## 7. Xử lý suggestions sau ingest

Suggestions có thể là:

- collection match
- page match
- entity match
- timeline match
- new page

Người dùng có thể:

- accept
- reject
- đổi target
- accept all
- reject all
- để source standalone

Nguyên tắc:

- chỉ accept khi thấy target hợp lý
- nếu chưa chắc, reject hoặc để standalone
- không merge tri thức chỉ vì confidence cao nếu evidence yếu

## 8. Chỉnh sửa page

### Chỉnh sửa draft

Khi update page:

- hệ thống dùng `expectedVersion`
- nếu page đã bị người khác lưu trước, API trả conflict `409`
- người dùng cần reload version mới trước khi lưu tiếp

### Restore version cũ

Nếu muốn quay lại version cũ:

1. mở version history
2. chọn version cần restore
3. restore

Kết quả:

- version cũ không bị ghi đè
- hệ thống tạo draft mới từ nội dung của version đó

### Insert helpers

Editor có helper để lấy:

- backlink markdown
- citation snippet markdown

Mục đích là chèn link/citation nhất quán hơn thay vì viết tay.

## 9. Publish flow

Trước khi publish nên kiểm tra:

- page có source links
- page có citation map
- lint severity cao đã xử lý
- review item liên quan đã đóng

Sau khi publish:

- page có `publishedAt`
- audit log ghi lại actor
- nếu chỉnh lại nội dung thì page quay về draft flow phù hợp

## 10. Review flow

Review item có thể tới từ:

- AI-generated update
- conflict heuristic
- stale heuristic

Reviewer nên làm:

1. đọc diff/change summary
2. kiểm tra issue list và evidence
3. comment nếu cần hỏi thêm
4. chọn một trong các hướng:
   - approve
   - reject
   - merge vào page khác
   - create issue page

## 11. Dùng Ask AI đúng cách

Ask AI tốt nhất khi:

- câu hỏi bám vào domain đã ingest
- người dùng mở citations để kiểm chứng
- câu trả lời quan trọng được save thành draft thay vì copy thủ công

Nên làm:

- hỏi cụ thể
- mở citation card
- kiểm tra source chunk
- save answer as draft nếu muốn đưa vào wiki

Không nên:

- publish trực tiếp chỉ dựa trên câu trả lời Ask
- bỏ qua citation khi câu trả lời ảnh hưởng policy/quyết định

## 12. Dùng Lint Center

Lint là lớp quality, không chỉ là markdown hygiene.

Luồng làm việc khuyến nghị:

1. filter theo severity `high`/`critical`
2. xử lý issue có quick fix an toàn trước
3. xử lý các issue cần editorial judgment sau
4. rerun hoặc reload lint

Quick fix hiện phù hợp cho:

- điền owner/status cho issue page
- tạo entity page còn thiếu

## 13. Dùng Knowledge Graph

Graph hữu ích khi cần:

- phát hiện page cô lập
- tìm cluster tri thức
- xem page nào là hub
- xác định page có conflict/stale signal

Cách dùng:

1. filter theo collection hoặc loại node
2. bật local graph khi muốn debug một page
3. dùng panel chi tiết để mở page/source nhanh

## 14. Saved views

Saved views dùng để lưu filter cá nhân, ví dụ:

- lint high severity
- pages in review
- stale source-linked pages

Saved views là per-user và lưu backend, không còn chỉ ở local UI.

## 15. Bulk actions

Bulk actions hiện hữu ích cho:

- publish/unpublish nhiều page
- archive/restore nhiều source
- bulk retry jobs ở khu vực admin

Chỉ nên dùng khi:

- tiêu chí chọn item đã rõ
- đã filter đúng collection/status
- chấp nhận tác động hàng loạt

## 16. Operations cho admin

Admin nên kiểm tra định kỳ:

- failed jobs
- duration p50/p95
- source throughput
- audit logs toàn cục
- runtime config export

Khi có failure hàng loạt:

1. vào `/admin`
2. xem failed job drilldown
3. nếu lỗi transient, bulk retry
4. nếu lỗi do input/provider, sửa root cause trước

## 17. Các lỗi thường gặp

### Không login được

Kiểm tra:

- backend đang chạy
- token cũ đã hết hạn hoặc logout
- đang dùng đúng tài khoản/role

### Source ingest không xong

Kiểm tra:

- Jobs tab
- source parse/ingest status
- worker có đang chạy không
- provider/model có cấu hình đúng không

### Lưu page bị conflict

Nguyên nhân:

- page đã có version mới hơn

Cách xử lý:

- reload page
- so sánh nội dung
- lưu lại trên version mới

### Ask AI trả lời yếu hoặc ít citation

Kiểm tra:

- source đã index chưa
- retrieval limit có quá thấp không
- câu hỏi có quá chung không

## 18. Checklist dùng hằng ngày

### Editor

- kiểm tra jobs/source mới
- xử lý suggestions
- chỉnh draft pages
- chạy lint cho khu vực mình phụ trách

### Reviewer

- mở review queue
- ưu tiên severity cao
- comment nếu cần clarifying context
- approve/reject/merge rõ ràng

### Admin

- kiểm tra operations dashboard
- bulk retry failed jobs nếu phù hợp
- export config trước thay đổi lớn
- theo dõi audit và smoke/regression trước release
