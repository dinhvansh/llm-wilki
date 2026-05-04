# Flow Xử Lý Hệ Thống

Tài liệu này mô tả luồng xử lý từ góc nhìn hệ thống: API, worker, storage, retrieval, review, và vận hành.

## 1. Luồng ingest tổng quát

### Bước 1: API tạo source record

Khi user upload file, nhập URL, hoặc paste text:

- API tạo `source`
- metadata ghi connector info
- file bytes được lưu qua storage abstraction
- checksum SHA-256 được tính
- dedupe metadata được gắn nếu có source trùng checksum

### Bước 2: enqueue job

API không ingest trực tiếp trong request.

Thay vào đó:

- tạo durable job row
- notify worker qua Redis hoặc polling backend database

### Bước 3: worker claim job

Worker:

- claim job pending đầu tiên phù hợp
- chuyển job sang running
- cập nhật heartbeat/progress/logs

### Bước 4: run ingest pipeline

Pipeline thực hiện:

- parse document
- chunk text
- extract claims/entities/events/terms
- build embeddings nếu có provider
- link source với pages/entities
- tạo/sửa draft pages
- tạo suggestions
- tạo review items nếu cần

### Bước 5: persist kết quả

Sau pipeline:

- source status cập nhật
- chunks/claims/entities/pages được lưu
- job hoàn tất hoặc failed

## 2. Luồng connector

Hệ thống có connector registry để mô tả capability:

- `file`
- `url`
- `txt`
- `transcript`
- `image_ocr`

Mỗi connector có metadata:

- supportsRebuild
- supportsRefresh
- maxSize
- authRequired
- error taxonomy

Hiện trạng:

- local-first hoạt động đầy đủ
- OCR và S3 mới ở mức portability placeholder

## 3. Luồng storage

Storage abstraction hiện active ở mode `local`.

Vai trò:

- lưu bytes gốc
- thay bytes khi refresh URL
- giữ đường mở rộng sang S3-compatible storage

## 4. Luồng review

Review items có hai nguồn:

- persisted review item từ pipeline/update flow
- virtual heuristic item từ stale/conflict detection

Review payload chứa:

- diff/change set
- issues
- suggestions
- page context
- comments

Reviewer action dẫn tới:

- approve
- reject
- merge
- create issue page

Mọi action đều ghi audit.

## 5. Luồng page editing

Update page dùng optimistic locking:

- client gửi `expectedVersion`
- backend so với `currentVersion`
- mismatch trả `409`

Mục tiêu:

- tránh overwrite âm thầm trong môi trường multi-user không realtime

Restore version:

- lấy nội dung từ `page_versions`
- tạo update mới
- không xóa history cũ

## 6. Luồng Ask AI

### Retrieval

Ask flow:

1. tokenize query
2. lexical candidate filtering
3. semantic/vector scoring nếu có embedding
4. hybrid rank
5. chọn top chunks

### Answering

- nếu có provider answer model thì gọi completion có context
- nếu không có provider thì dùng fallback grounded answer

### Persistence

- chat session/message được lưu
- answer response giữ citations/diagnostics
- có thể save assistant message thành page draft

## 7. Luồng lint

Lint không sửa dữ liệu trực tiếp trừ khi user gọi quick fix.

Flow:

1. quét pages trong giới hạn runtime
2. chạy rule set
3. trả issue + summary + quick-fix metadata

Safe quick fixes hiện có:

- điền owner/status cho issue page
- tạo entity page thiếu

## 8. Luồng graph

Graph build từ:

- pages
- links
- source relations
- review/conflict/stale signals

API graph áp dụng:

- collection filter
- local/global modes
- node limit guard

## 9. Luồng auth và governance

Auth dùng:

- local users
- session token Bearer
- role guard ở backend

Governance:

- settings chỉ admin
- review actions cho reviewer/admin
- editorial mutations cho editor trở lên
- audit log ghi actor metadata

## 10. Luồng observability

Mỗi request:

- có `X-Request-ID`
- được log theo JSON structured log

Admin operations API tổng hợp:

- job counts
- duration percentiles
- stage counts
- source throughput
- failed drilldown
- config export/import

## 11. Luồng release nội bộ

Flow khuyến nghị:

1. chạy test scripts theo phase/regression
2. compile/build
3. docker rebuild
4. docker smoke
5. e2e smoke
6. review release notes

Shortcut hiện có:

- `scripts/run_regression.ps1`
- `scripts/reset_local.ps1`
