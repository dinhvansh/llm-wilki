# BPM Flow Standard

Tai lieu nay quy dinh cach he thong phai mo ta va sinh so do quy trinh nghiep vu.

Muc tieu:

- flow phai theo chuan business process, khong ve cho dep
- phai tra loi ro ai lam, lam gi, khi nao chuyen buoc, va di dau tiep
- AI neu sinh flow thi phai sinh theo chuan nay

## 1. Nguyen tac cot loi

Moi flow nghiep vu phai tra loi duoc 5 cau hoi:

1. Ai tham gia?
2. Buoc cong viec nao duoc thuc hien?
3. Dieu kien nao quyet dinh nhanh tiep theo?
4. Dau vao/dau ra cua moi buoc la gi?
5. Buoc nay ban giao cho ai hoac he thong nao tiep theo?

Neu flow khong tra loi duoc 5 cau hoi tren thi flow do chua dat chuan.

## 2. Don vi flow dung

He thong dung flow nho lam don vi goc.

Moi flow nen:

- phuc vu mot muc tieu nghiep vu ro rang
- co owner ro
- co diem bat dau va diem ket thuc ro
- co the link sang flow khac qua subprocess/handoff

Khong sinh mega-flow gom tat ca tai lieu lien quan vao mot so do duy nhat.

## 3. Thanh phan bat buoc trong flow

Moi BPM flow phai co cac thanh phan sau:

- `title`
- `scope`
- `start_event`
- `end_event`
- `actors`
- `systems`
- `steps`
- `decisions`
- `handoffs`
- `exceptions`
- `citations`

## 4. Quy tac ve actor

Flow phai ve theo actor ro rang. Moi buoc phai thuoc ve mot actor hoac mot system actor.

Actor hop le:

- `Requester`
- `Editor`
- `Reviewer`
- `Admin`
- `Finance`
- `HR`
- `System`
- ten bo phan/nghiep vu cu the

Khong duoc dung actor mo ho:

- `Nguoi dung`
- `Nhan vien`
- `Bo phan lien quan`
- `He thong khac`

Neu tai lieu mo ho, AI phai danh dau actor la `Unclear` va dua vao danh sach can review, khong tu y doan.

## 5. Quy tac ve step

Moi step phai viet theo dang hanh dong cu the:

- Dong tu + doi tuong + ket qua

Vi du tot:

- `Editor tao draft page`
- `Reviewer kiem tra citation`
- `System tao ingest job`
- `Admin retry failed job`

Vi du khong tot:

- `Xu ly tai lieu`
- `Kiem tra thong tin`
- `Cap nhat he thong`

Moi step nen co:

- `owner`
- `input`
- `output`
- `precondition` neu can
- `next`

## 6. Quy tac ve decision

Decision phai la cau hoi co nhanh ro rang.

Vi du:

- `Reviewer dong y?`
- `Source co hop le?`
- `Can tao issue page?`

Moi decision phai co:

- it nhat 2 outgoing edges
- label cho moi nhanh: `Yes/No`, `Approve/Reject`, `Valid/Invalid`

Khong duoc ve diamond ma khong ghi dieu kien.

## 7. Quy tac ve handoff

Handoff la diem chuyen trach nhiem giua actor hoac giua nguoi va he thong.

Moi handoff phai chi ro:

- ai ban giao
- ban giao cai gi
- ai nhan
- sau handoff flow di sang dau

## 8. Quy tac ve exception flow

Flow nghiep vu khong chi co happy path.

Moi flow can co:

- happy path
- reject/fail path
- retry/rework path neu co

Neu tai lieu co noi ve:

- tu choi
- loi
- khong hop le
- thieu thong tin
- can bo sung

thi AI phai sinh nhanh exception tuong ung.

## 9. Kich thuoc flow

Khuyen nghi:

- 5-20 nodes la dep
- tren 25-30 nodes can xem xet tach subprocess
- tren 3 actor lane can xem xet tach flow con

## 10. Cau truc metadata de luu trong he thong

Moi diagram/process flow nen co metadata toi thieu:

```json
{
  "id": "diag-001",
  "title": "Quy trinh phe duyet tai lieu",
  "objective": "Dua draft vao review va publish noi bo",
  "owner": "Knowledge Ops",
  "sourcePageIds": ["page-001"],
  "sourceIds": ["src-003"],
  "actors": ["Editor", "Reviewer", "System"],
  "entryPoints": ["Draft duoc tao"],
  "exitPoints": ["Published", "Rejected", "Needs rework"],
  "relatedDiagramIds": ["diag-002"],
  "status": "draft"
}
```

## 11. Diagram spec toi thieu

AI khong nen lay draw.io XML lam artifact logic goc.

Nen co diagram spec trung gian:

```json
{
  "title": "Quy trinh review va publish",
  "actors": [
    { "id": "editor", "label": "Editor" },
    { "id": "reviewer", "label": "Reviewer" },
    { "id": "system", "label": "System" }
  ],
  "nodes": [
    { "id": "start", "type": "start", "label": "Draft san sang review", "owner": "editor" },
    { "id": "submit", "type": "task", "label": "Editor gui draft", "owner": "editor" },
    { "id": "check", "type": "decision", "label": "Reviewer dong y?", "owner": "reviewer" },
    { "id": "publish", "type": "task", "label": "System publish page", "owner": "system" },
    { "id": "rework", "type": "task", "label": "Editor sua lai draft", "owner": "editor" },
    { "id": "end_ok", "type": "end", "label": "Published", "owner": "system" },
    { "id": "end_rework", "type": "end", "label": "Tra ve de sua", "owner": "editor" }
  ],
  "edges": [
    { "from": "start", "to": "submit" },
    { "from": "submit", "to": "check" },
    { "from": "check", "to": "publish", "label": "Approve" },
    { "from": "check", "to": "rework", "label": "Reject" },
    { "from": "publish", "to": "end_ok" },
    { "from": "rework", "to": "end_rework" }
  ]
}
```

## 12. Mapping node type

Node type duoc quy uoc nhu sau:

- `start`
- `task`
- `decision`
- `subprocess`
- `handoff`
- `document`
- `system_event`
- `end`

## 13. Chuan output khi AI sinh flow

Khi AI sinh flow tu tai lieu nghiep vu, output phai gom:

1. `scope summary`
2. `actors`
3. `main flow`
4. `decision points`
5. `exception flow`
6. `open questions`
7. `citations`
8. `diagram spec`

Neu co diem mo ho thi AI phai ghi vao `open questions`, khong duoc tu y hop ly hoa.

## 14. Quy tac review diagram

Nguoi review flow phai kiem:

- actor co dung khong
- step co cu the khong
- co thieu handoff khong
- decision co du nhanh khong
- happy path va reject path co day du khong
- moi step quan trong co citation ho tro khong
- flow co qua to de can tach khong

## 15. Cach gan voi draw.io

draw.io editor duoc xem la lop editor/trinh bay.

He thong nay dung `draw.io` open-source theo mo hinh self-host.

Rang buoc kien truc:

- khong phu thuoc `embed.diagrams.net`
- khong nhung editor online tu dich vu ben ngoai
- khong luu diagram phu thuoc vao mot SaaS editor
- editor phai duoc host trong ha tang cua he thong nay

Noi cach khac:

- dung ma nguon mo `jgraph/drawio`
- chay editor trong stack cua minh
- frontend/backend cua minh moi la noi quan ly save, version, auth, review

draw.io chi dong vai tro editor open-source duoc self-host trong he thong.

He thong nen luu:

- `diagram_spec` lam logic artifact
- `drawio_xml` lam editor artifact
- `preview_png` hoac `preview_svg` de xem nhanh

Khi user mo diagram:

1. load `drawio_xml` neu da co
2. neu chua co thi generate XML tu `diagram_spec`
3. mo editor draw.io open-source duoc self-host trong iframe/noi tich hop noi bo
4. save ve he thong thanh version moi

## 16. Nguyen tac san pham

He thong nay khong nham toi viec "ve so do dep".

No nham toi:

- bien tai lieu nghiep vu thanh process artifact co cau truc
- co the review
- co the version
- co the truy vet ve nguon tai lieu
- co the mo rong thanh mang luoi flow lien ket

Neu phai chon giua dep va ro nghiep vu, uu tien ro nghiep vu.
