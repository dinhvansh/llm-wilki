# Flow Nghiep Vu LLM Wiki

Tai lieu nay mo ta cac flow su dung theo cong viec thuc te, khong di sau vao code.

## 1. Flow ingest tai lieu moi

### Muc tieu

Dua tai lieu moi vao he thong va bien no thanh tri thuc co the review.

### Luong

1. Editor tao source tu file, URL, hoac text
2. He thong tao job ingest
3. Worker xu ly source
4. He thong sinh chunks, claims, entities, pages lien quan
5. He thong tao suggestions va co the tao review items
6. Editor mo source detail de xac nhan
7. Editor xu ly suggestions

### Ket qua mong doi

- source o trang thai indexed/usable
- page draft hoac page lien quan duoc cap nhat
- citations va links truy duoc ve source

## 2. Flow xay mot page moi tu source

### Cach 1: tu ingest tu dong

1. Source duoc ingest
2. He thong tao page draft
3. Editor mo page
4. Editor chinh noi dung, kiem citations
5. Reviewer review neu can
6. Publish

### Cach 2: tu selected chunks

1. Editor xac dinh chunk quan trong
2. Dung flow tao draft tu chunks
3. He thong tao page draft moi hoac update page hien co
4. Editor chinh summary va cau truc
5. Review/publish

## 3. Flow cap nhat page dang ton tai

1. Editor mo page
2. Kiem tra version hien tai
3. Chinh noi dung
4. Submit update kem `expectedVersion`
5. Neu conflict:
   - reload
   - so sanh voi version moi
   - cap nhat lai
6. Neu khong conflict:
   - page luu thanh draft/version moi
   - audit log ghi nhan thay doi

## 4. Flow restore version cu

1. Editor hoac reviewer mo version history
2. Chon version can quay lai
3. Restore
4. He thong tao draft version moi tu noi dung cu
5. Editor tiep tuc chinh neu can

Diem quan trong:

- khong pha version history
- restore khong phai rollback destructive

## 5. Flow review AI-generated update

1. Review item xuat hien trong queue
2. Reviewer doc:
   - diff
   - issue list
   - evidence
   - comments neu co
3. Reviewer chon:
   - approve
   - reject
   - merge
   - create issue page

### Approve

- page duoc chap nhan
- review item dong
- audit log ghi lai

### Reject

- page quay ve draft path
- review item giu lich su reject

### Merge

- ghi nhan merge source page vao target page
- source page co the chuyen archived

## 6. Flow xu ly stale/conflict

1. He thong phat hien stale/conflict qua heuristic hoac lint/review
2. Reviewer kiem source moi hon hoac evidence mau thuan
3. Neu issue dung:
   - cap nhat page
   - tao issue page neu can theo doi
   - merge hoac chinh source links
4. Re-run review/lint

## 7. Flow Ask AI -> draft page

1. User hoi o Ask AI
2. He thong tra loi voi citations
3. User kiem source evidence
4. Neu cau tra loi dang giu:
   - save answer as draft
5. He thong tao page draft co section citations
6. Editor lam sach noi dung roi dua vao review/publish flow

## 8. Flow lint remediation

1. Editor/reviewer vao Lint Center
2. Filter high/critical
3. Neu co quick fix an toan:
   - chay truc tiep
4. Neu can judgment:
   - mo page/source lien quan
   - chinh tay
5. Reload lint de xac nhan issue giam

## 9. Flow source refresh cho URL

1. Editor mo URL source
2. Chon refresh
3. He thong fetch lai noi dung URL
4. File nguon duoc thay moi
5. Job rebuild duoc enqueue
6. Source va pages lien quan duoc cap nhat theo ingest flow

## 10. Flow bulk operations

### Pages

- publish/unpublish hang loat

### Sources

- archive/restore hang loat

### Jobs

- admin bulk retry failed jobs

Nguyen tac:

- chi chay sau khi filter dung
- tranh bulk action tren tap du lieu chua kiem tra

## 11. Flow admin operations

1. Admin mo `/admin`
2. Xem backlog/failure/duration
3. Mo failed jobs
4. Neu loi transient thi bulk retry
5. Kiem tra audit neu co thay doi nhay cam
6. Export config truoc thay doi lon
7. Import config khi can dong bo moi truong

## 12. Flow phat hanh noi bo

1. Chay regression script
2. Build frontend
3. Chay Docker smoke
4. Chay E2E smoke
5. Kiem tra release notes/known limitations
6. Chi khi pass het moi coi la build san sang noi bo

## 13. Chuan BPM cho flow diagram

Tu nay, cac flow nghiep vu duoc sinh tu tai lieu phai theo chuan business process.

Y nghia:

- flow phai chi ro `ai lam`
- `buoc nao` duoc thuc hien
- `dieu kien nao` re nhanh
- `ban giao cho ai/he thong nao`
- `ket thuc o dau`

Flow diagram khong duoc chi la hinh minh hoa.

No phai la artifact nghiep vu co the review va truy vet.

Tai lieu chuan nam o:

- [BPM Flow Standard](</mnt/d/AI-native wiki platform/docs/BPM_FLOW_STANDARD.md>)

Nguyen tac ap dung:

1. Moi flow nho phai co scope ro rang
2. Moi step phai co owner
3. Moi decision phai co branch label
4. Moi handoff phai chi ro diem chuyen trach nhiem
5. Moi flow phai co happy path va exception path
6. Neu tai lieu mo ho thi AI phai dat open question, khong duoc tu doan
7. Neu dung editor diagram thi editor do phai la `draw.io` open-source duoc self-host trong he thong, khong dung ban embed online
