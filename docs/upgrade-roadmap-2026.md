# Upgrade Roadmap 2026

Roadmap nay tong hop nhung nang cap tiep theo cho `llm-wiki` sau khi cac phase Ask AI / retrieval accuracy da hoan thanh. Muc tieu khong chi la tra loi tot hon, ma la nang cap san pham theo 4 truc: `UI/UX`, `authorization + scoping`, `multimodal ingest/retrieval`, va `wiki/evidence workflow`.

## North Star

```text
Upload source
→ parse text + image + structure
→ build scoped knowledge objects
→ browse wiki / graph / evidence naturally
→ ask grounded multimodal questions
→ review / publish with clear permissions
```

## Roadmap Summary

| Roadmap Phase | Priority | Goal |
|---|---|---|
| Phase A - UX and Product Surface | P0 | Lam app trong giong mot knowledge workspace thay vi dashboard CRUD |
| Phase B - Permission and Scope Foundation | P0 | Nang auth hien tai thanh permission + collection/workspace scope |
| Phase C - Vision and Multimodal Ingest | P1 | Dua image/diagram/table vao pipeline tri thuc thay vi bo qua |
| Phase D - Multimodal Retrieval and Ask AI | P1 | Retrieve va answer tu text + image-derived evidence + structure |
| Phase E - Wiki Browsing and Evidence Workflow | P1 | Bien wiki/page/source/graph/review thanh mot flow thong nhat |
| Phase F - Skill Packaging and Internal Extensibility | P2 | Chi them khi can phan phoi reusable AI capability noi bo |

## Phase A - UX And Product Surface

Muc tieu:
- bo visual mac dinh hien tai
- chuyen tu giao dien module roi rac sang product flow ro rang
- lam ro gia tri cua Ask AI, Sources, Pages, Graph, Review trong cung mot he thong

Checklist:
- [x] Tao design system rieng: color, typography, spacing, radius, shadow, component states
- [x] Refactor `sidebar`, `page header`, `section shell`, `empty state`, `card`, `table`, `detail panel`
- [x] Chuyen navigation tu list chuc nang sang nhom theo luong cong viec
- [x] Thiet ke lai `Dashboard` thanh knowledge operations home
- [x] Thiet ke lai `Pages`, `Graph`, `Ask`, `Sources` de visual language dong nhat
- [x] Viet lai product copy trong app va README de dinh vi san pham ro hon

Acceptance criteria:
- app khong con cam giac la admin CRUD dashboard
- user moi co the hieu flow chinh trong 1-2 phut
- `Ask`, `Sources`, `Pages`, `Graph`, `Review` co cung ngon ngu giao dien

## Phase B - Permission And Scope Foundation

Muc tieu:
- giu auth hien tai nhung nang cap authorization
- dua he thong tu `role rank` sang `permission + scope`
- tao nen cho collection/workspace scoped knowledge

Checklist:
- [x] Dinh nghia permission matrix theo resource/action
- [x] Them permission engine thay vi chi `hasRole()`
- [x] Them scope model: `global | collection | workspace`
- [x] Them membership role cho workspace/collection
- [x] Loc du lieu theo scope o query-time, khong chi o endpoint
- [x] Hien thi UI condition theo permission/scope
- [x] Them audit metadata toi thieu cho thao tac nhay cam

Acceptance criteria:
- hai user khac nhau co the thay bo du lieu khac nhau trong cung mot man
- role khong con la gate duy nhat
- co the mo rong them department/team sau nay ma khong phai viet lai auth

Implementation guidance:
- uu tien `collection scope` truoc
- chi them `department/team` khi product can chia quyen theo to chuc that

## Phase B2 - Identity And Access Operations

Muc tieu:
- bien auth foundation thanh trai nghiem van hanh duoc cho admin va user that
- khong chi co permission engine o backend, ma con co login flow, user lifecycle, va access assignment surface
- bo sung nhung phan con thieu de app co the dung nghiem tuc cho multi-user local/internal rollout

Tai sao can phase nay:
- `Phase B` da giai quyet `authorization architecture`
- nhung hien tai van thieu `identity operations`
- ket qua la app co auth backend, nhung chua co:
  - trang login rieng truoc khi vao app
  - route guard / redirect khi chua dang nhap
  - admin tao user moi
  - admin gan role va collection membership
  - optional department/team structure

Checklist:
- [x] Tao trang `/login` rieng va bo login inline khoi top bar
- [x] Them route guard cho `(main)` khi chua authenticated
- [x] Them bootstrap flow:
  - login thanh cong -> fetch `me`
  - hydrate auth context
  - redirect ve trang truoc do hoac dashboard
- [x] Them `Users` page cho admin
- [x] Them API tao user moi
- [x] Them API update user:
  - name
  - email
  - role
  - active/inactive
- [x] Them API reset password hoac set password tam thoi
- [x] Them UI assign `collection memberships`
- [x] Hien thi ro user scope:
  - shared workspace
  - collection-scoped workspace
- [x] Them audit log cho:
  - create user
  - deactivate/reactivate user
  - change role
  - change membership
- [x] Optional: them `department/team` model neu product can organizational scope that su

Acceptance criteria:
- user chua dang nhap khong vao duoc app shell chinh
- admin tao duoc user moi ma khong can patch DB tay
- admin gan duoc role va collection membership tu UI
- user login vao thay dung scope du lieu cua minh
- moi thay doi quyen co audit metadata toi thieu

Backend design detail:
- model:
  - tiep tuc dung `users`
  - tiep tuc dung `collection_memberships`
  - neu can `departments`, them table rieng o buoc sau
- API toi thieu:
  - `POST /api/auth/login`
  - `GET /api/auth/me`
  - `POST /api/auth/logout`
  - `GET /api/admin/users`
  - `POST /api/admin/users`
  - `PATCH /api/admin/users/{id}`
  - `POST /api/admin/users/{id}/set-password`
  - `PUT /api/collections/{id}/memberships`
- permission de gate:
  - `admin:read`
  - `admin:write` neu can tach rieng
  - `collection:write`
- audit:
  - `create_user`
  - `update_user_role`
  - `set_user_password`
  - `set_collection_memberships`
  - `deactivate_user`

Frontend design detail:
- routes:
  - `/login`
  - `/admin/users`
- auth UX:
  - neu chua token -> redirect `/login`
  - neu token het han -> clear session va redirect `/login`
  - top bar chi hien account menu sau khi auth
- admin users page:
  - bang user
  - filter theo role / active state
  - drawer hoac side panel de edit
  - section membership cho moi user
- collection membership UX:
  - moi collection co list member
  - moi user co list collection access
  - role trong collection: `viewer | contributor | editor | admin`

Implementation slices:
- Slice 1:
  - `/login`
  - auth guard
  - logout UX dung chuan
- Slice 2:
  - list users
  - create user
  - activate/deactivate
- Slice 3:
  - role update
  - set/reset password
- Slice 4:
  - collection membership management UI/API polish
- Slice 5:
  - neu can moi them `department/team`

Verification:
- backend:
  - test login fail/success
  - test unauthenticated redirect behavior bang smoke
  - test admin create user
  - test non-admin bi chan khi tao user
  - test membership change anh huong den list sources/pages/collections
- frontend:
  - build
  - smoke `/login -> dashboard`
  - smoke `/admin/users -> create user -> logout -> login user moi`
- docker:
  - smoke full local flow voi it nhat 2 user role khac nhau

Recommendation:
- nen lam `Phase B2` ngay sau roadmap hien tai neu muc tieu la demo/shipping cho nhieu nguoi dung that
- chua can them `department/team` neu collection scope da du cho use case hien tai

Trang thai hien tai:
- da xong `Slice 1-5` o muc production-local:
  - `/login`
  - auth guard
  - `/admin/users`
  - create/update user
  - activate/deactivate
  - set password
  - assign collection memberships
  - department model + user department assignment

## Phase C - Vision And Multimodal Ingest

Muc tieu:
- dua image, scan, table, diagram vao ingest pipeline
- hoc pattern tot tu Arkon nhung di xa hon captioning don thuan

Checklist:
- [x] Extract image tu PDF/DOCX trong ingest
- [x] Caption image bang vision model co kem page context
- [x] Persist image object rieng trong DB/storage
- [x] Inject stable image markers vao source text / source structure
- [x] Them OCR flow cho scanned PDF/image source
- [x] Them table/diagram extraction object
- [x] Them debug surface cho image-derived artifacts trong Source Detail

Acceptance criteria:
- image quan trong khong bi mat khoi pipeline
- source detail cho thay duoc text, image, OCR, section structure trong cung mot noi
- diagram/table co the tro thanh evidence object thay vi text phu

## Phase D - Multimodal Retrieval And Ask AI

Muc tieu:
- nang Ask AI tu text-grounded QA thanh multimodal grounded QA
- cho phep evidence den tu chunk, claim, summary, knowledge unit, image, bang, diagram

Checklist:
- [x] Mo rong retrieval object schema cho image/table/diagram evidence
- [x] Them hybrid retrieval qua text + image-derived summaries
- [x] Them rerank aware of candidate type
- [x] Them context assembly bao phu ca structural va visual evidence
- [x] Hien thi provenance theo candidate type trong Ask AI UI
- [x] Phan biet ro grounded fact, inference, va unsupported gap
- [x] Them benchmark/eval cho multimodal cases

Acceptance criteria:
- cau hoi lien quan den so do/bang/anh co the tra loi dua tren evidence that
- user nhin vao citation biet evidence do den tu text hay visual artifact
- multimodal benchmark co baseline va regression gate rieng

## Phase E - Wiki Browsing And Evidence Workflow

Muc tieu:
- bien wiki thanh surface trung tam cua san pham
- lien thong page, source, graph, citations, review, ask

Checklist:
- [x] Nang `Pages` thanh 3-panel hoac split-view browse experience
- [x] Them backlinks / outlinks / related evidence panel
- [x] Lien ket truc tiep tu Ask citation sang Source Detail va Page context
- [x] Lien ket tu Graph node sang page/source inspector
- [x] Cai thien review queue de reviewer thay ro evidence va change intent
- [x] Them version/revision drilldown de nguoi dung hieu page duoc tao tu dau

Acceptance criteria:
- user co the di tu answer -> citation -> source -> page -> graph ma khong bi dut context
- wiki khong con la tap hop page roi rac
- review flow du minh bach de debug tai sao trang duoc approve/publish

## Phase F - Skill Packaging And Internal Extensibility

Muc tieu:
- chi them khi can phan phoi capability noi bo dang reusable package
- tranh mo rong qua som neu chua co use case ro

Checklist:
- [x] Dinh nghia scope cua `skill` trong san pham: prompt pack, tool pack, hay workflow pack
- [x] Them package metadata + version + storage layout
- [x] Them visibility/scope cho skill
- [x] Them browse/inspect/release workflow cho skill
- [x] Neu can, them contribution/review flow cho skill update

Acceptance criteria:
- skill giai quyet mot nhu cau phan phoi capability cu the
- khong lam product surface phinh ra neu user chua can

## Delivery Order

```text
1. Phase A - UX and Product Surface
2. Phase B - Permission and Scope Foundation
3. Phase C - Vision and Multimodal Ingest
4. Phase D - Multimodal Retrieval and Ask AI
5. Phase E - Wiki Browsing and Evidence Workflow
6. Phase F - Skill Packaging and Internal Extensibility
```

Ly do:
- `A` va `B` tao ra product shell dung
- `C` va `D` tao ra nang luc AI/knowledge tiep theo
- `E` bien nang luc do thanh trai nghiem thuc te
- `F` la optional extensibility layer, khong nen lam som

## Suggested Execution Strategy

- Sprint 1-2: Phase A
- Sprint 2-3: Phase B
- Sprint 3-4: Phase C
- Sprint 4-5: Phase D
- Sprint 5-6: Phase E
- Sau khi co use case ro: Phase F

## Exit Criteria

Roadmap nay duoc xem la hoan thanh khi:

- san pham co visual/system identity ro rang
- permission va scope du de chay multi-user nghiem tuc
- ingest va retrieval xu ly duoc multimodal evidence
- Ask AI + Wiki + Source + Graph + Review lien thong thanh mot workflow
- moi nang cap chinh deu co benchmark/eval/regression gate

## Execution Plan Snapshot - 2026-05-11

Muc tieu cua dot nay:
- khoa mot lat cat hoan chinh cho `Phase A foundation` va `Phase B foundation`
- khong mo rong sang vision/retrieval khi shell va permission model chua on dinh

Audit map:
- `Phase A`: frontend shell nam chu yeu o `llm-wiki/src/styles`, `src/components/layout`, `src/app/(main)`
- `Phase B`: auth/scoping nam chu yeu o `backend/app/services/auth.py`, `backend/app/core/identity.py`, `backend/app/api/*`, `backend/app/services/{collections,pages,sources}.py`
- `Phase C`: multimodal foundation nam o `backend/app/core/ingest.py`, `backend/app/services/sources.py`, `backend/app/api/sources.py`, `llm-wiki/src/app/(main)/sources/[id]/page.tsx`
- `Phase D`: retrieval/ask nam chu yeu o `backend/app/services/query.py`, `backend/app/schemas/query.py`, `llm-wiki/src/app/(main)/ask/page.tsx`
- `Phase E-F`: chua implement trong dot nay; se tiep tuc sau khi multimodal ask foundation on dinh

Execution order:
1. cap nhat design tokens va app shell
2. them permission payload vao auth contract
3. them collection membership + scope filter o backend
4. noi permission/scope vao frontend navigation
5. verify bang `python -m compileall` va `npm --prefix llm-wiki run build`

## Phase Status

| Phase | Status | Notes |
|---|---|---|
| Phase A - UX and Product Surface | completed | da xong shell, workspace IA, visual language, dashboard surface, va README/product framing |
| Phase B - Permission and Scope Foundation | completed | da xong permission engine, collection scope, membership model, va audit metadata toi thieu |
| Phase C - Vision and Multimodal Ingest | completed | da xong artifact/ocr/table/source detail surface, image persistence, va contextual vision caption fallback |
| Phase D - Multimodal Retrieval and Ask AI | completed | da xong artifact retrieval/provenance flow va regression/eval cho multimodal cases |
| Phase E - Wiki Browsing and Evidence Workflow | completed | da xong ask/source/page/graph/review linking chinh va evidence CTA workflow |
| Phase F - Skill Packaging and Internal Extensibility | completed | da co registry file-based, scope dinh nghia workflow pack, va review/release flow toi thieu |

## Implementation Log

### Phase A foundation

Da thay doi:
- lam moi `llm-wiki/src/styles/globals.css` thanh mot visual system am, editorial hon
- refactor `sidebar`, `top-bar`, `page-header`, `app/(main)/layout.tsx`, `app/(main)/page.tsx`
- doi navigation tu flat feature list sang nhom `Workspace / Knowledge / Governance`
- noi shell voi auth scope de user thay duoc bieu dien `shared workspace` vs `collection scoped`

Tac dong:
- khong doi API
- doi visual shell va navigation behavior
- bat dau UI gating theo permission thay vi chi role admin

File chinh:
- `llm-wiki/src/styles/globals.css`
- `llm-wiki/src/components/layout/sidebar.tsx`
- `llm-wiki/src/components/layout/top-bar.tsx`
- `llm-wiki/src/components/layout/page-header.tsx`
- `llm-wiki/src/app/(main)/layout.tsx`
- `llm-wiki/src/app/(main)/page.tsx`

### Phase B foundation

Da thay doi:
- mo rong auth payload voi `permissions`, `scopeMode`, `accessibleCollectionIds`, `collectionMemberships`
- them `backend/app/services/permissions.py`
- them model `CollectionMembership`
- them migration `backend/migrations/versions/0013_collection_memberships.py`
- them scope-aware filtering cho collections, sources, pages list/read
- chuyen mot so route write sang `require_permission(...)`
- them frontend support cho permission-aware auth context

Tac dong:
- frontend co the render navigation theo permission
- backend co the restrict du lieu theo collection scope
- user khong co membership van giu hanh vi backward-compatible: thay full data

File chinh:
- `backend/app/services/permissions.py`
- `backend/app/services/auth.py`
- `backend/app/core/identity.py`
- `backend/app/models/records.py`
- `backend/app/models/__init__.py`
- `backend/app/api/auth.py`
- `backend/app/api/collections.py`
- `backend/app/api/pages.py`
- `backend/app/api/sources.py`
- `backend/app/services/{collections,pages,sources}.py`
- `backend/app/schemas/{auth,source}.py`
- `backend/migrations/versions/0013_collection_memberships.py`
- `llm-wiki/src/providers/auth-provider.tsx`
- `llm-wiki/src/lib/types/index.ts`
- `llm-wiki/src/services/mock/mock-collections.ts`

### Phase C completion slice

Da thay doi:
- them `source artifacts` contract de Source Detail co the inspect artifact dang co thay vi doc truc tiep `metadataJson`
- expose artifact endpoint moi: `/api/sources/{source_id}/artifacts`
- synthesize artifact tu:
  - `docling` / OCR metadata
  - `sectionSummaries` + `sourceSections`
  - `notebookContext`
  - table-like chunks
  - image assets trong upload asset directory neu co
- them tab `Artifacts` vao `Source Detail` va summary card cho multimodal readiness
- noi them ingest cho `docx` va `image_ocr`:
  - `docx` co `orderedBlocks`, `images`, `imageCount`, `tableCount`
  - `image_ocr` co image artifact goc ngay ca khi OCR job chua xong
- doi upload asset URL sang proxy path on dinh `/backend-uploads/...` thay vi hardcode `localhost:8000`
- persist `multimodalArtifacts` manifest ngay trong `metadataJson` khi ingest hoan tat
- them model `SourceArtifactRecord` + migration `0014_source_artifacts.py`
- persist artifact rows rieng trong DB de Ask / Source Detail / review workflow khong phai reconstruct lai toan bo manifest
- mo rong image artifact captioning:
  - uu tien multimodal LLM neu runtime support image input
  - fallback theo page context / paragraph context neu runtime khong ho tro
  - luu `captionSource` vao metadata artifact de biet caption den tu vision hay fallback

Tac dong:
- da co image persistence rieng trong DB va duong caption co context cho artifact image
- da tao UI/API surface on dinh de cac phase sau dua image/table/ocr evidence vao retrieval va ask
- page generation va answer illustration pipeline co the tai su dung `orderedBlocks/images` on dinh hon
- artifact consumer ve sau co the doc manifest on dinh thay vi parse lai metadata thô

File chinh:
- `backend/app/services/sources.py`
- `backend/app/api/sources.py`
- `backend/app/schemas/source.py`
- `backend/app/core/ingest.py`
- `backend/app/core/llm_client.py`
- `backend/app/models/{records,__init__}.py`
- `backend/migrations/versions/0014_source_artifacts.py`
- `backend/app/services/query.py`
- `llm-wiki/src/lib/types/index.ts`
- `llm-wiki/src/components/data-display/markdown-renderer.tsx`
- `llm-wiki/next.config.ts`
- `llm-wiki/src/services/{types,real-sources}.ts`
- `llm-wiki/src/services/mock/mock-sources.ts`
- `llm-wiki/src/hooks/use-sources.ts`
- `llm-wiki/src/app/(main)/sources/[id]/page.tsx`
- `backend/scripts/test_phase54.py`

### Phase D completion slice

Da thay doi:
- them candidate moi `artifact_summary` trong Ask retrieval de doc `metadataJson.multimodalArtifacts`
- artifact retrieval hien uu tien cac artifact type:
  - `structure`
  - `notebook`
  - `table`
  - `ocr`
  - `image`
- them text synthesis rieng cho artifact de co the rerank theo title, summary, preview, section titles, prompt suggestions, table preview, OCR metadata
- mo rong retrieval policy + rerank logic de `artifact_summary` co the tham gia summary/procedure/policy/risk intent
- sua `source_query` trong Ask de source-scoped retrieval khong bi title/description term filter loai mat notebook/artifact candidates
- mo rong context pack va citation payload voi:
  - `artifactId`
  - `artifactType`
- ep source-scoped Ask uu tien dua it nhat mot artifact grounded vao `selectedContext` neu source co multimodal manifest
- them deep link tu Ask citation sang `Source Detail`
  - citation artifact-level mo thang tab `Artifacts`
  - source detail auto highlight artifact duoc trich dan
  - chunk citation van mo tab `Chunks` nhu truoc
- them artifact workflow o frontend:
  - Ask UI tach rieng `Artifact Evidence` va `Text Evidence`
  - Source Detail artifact co nut `Ask About Artifact`
  - `prompt` duoc seed san khi mo Ask tu artifact
- them regression/eval cho multimodal retrieval:
  - `test_phase53.py` cho artifact citation flow
  - `evaluate_quality.py --tag multimodal` voi case `artifact-multimodal-summary`

Tac dong:
- Ask AI khong con chi retrieve chunk/claim/notebook note ma co the retrieve artifact-level evidence tu source detail manifest
- diagnostics/admin debug hien candidate artifact ro hon
- citations co the chi ra artifact provenance thay vi chi chunk-level provenance
- user co the di truc tiep tu answer -> artifact duoc dung lam evidence ma khong phai tim tay trong source detail
- user co the di nguoc tu artifact -> ask scoped question ma khong phai tu viet prompt lai
- chua co visual retrieval thuc su cho image embedding; artifact retrieval hien van dua tren text summary/preview cua artifact

File chinh:
- `backend/app/services/query.py`
- `backend/app/schemas/query.py`
- `backend/scripts/evaluate_quality.py`
- `backend/evals/golden_dataset.json`
- `llm-wiki/src/lib/types/index.ts`
- `llm-wiki/src/app/(main)/ask/page.tsx`
- `llm-wiki/src/app/(main)/sources/[id]/page.tsx`

### Phase E foundation slice

Da thay doi:
- mo rong `Graph` inspector de node chi hien metric khong nua, ma co action tiep theo ro rang:
  - `Open page`
  - `Ask this page`
  - `Inspect source`
  - `Ask linked source`
- doi `sourceIds` trong graph detail tu text chip sang link thao tac duoc
- mo rong `Pages` context panel:
  - moi citation co CTA `Inspect source chunk`
  - moi citation co CTA `Ask about this citation`
- mo rong `Review Queue`:
  - them comment thread tren review item
  - them CTA `Ask this page`, `Inspect first source`, `Ask about top evidence`

Tac dong:
- user co the di tu graph node sang page/source/ask ma khong bi dut context
- graph bat dau dong vai tro inspector co ich cho workflow debug knowledge, khong chi la visualization
- page context panel bat dau dong vai tro evidence navigator thay vi chi liet ke citation
- review queue co du evidence handoff de reviewer khong can nhay tay giua cac module

File chinh:
- `llm-wiki/src/app/(main)/graph/page.tsx`
- `llm-wiki/src/app/(main)/pages/[slug]/page.tsx`
- `llm-wiki/src/app/(main)/review/page.tsx`
- `llm-wiki/src/hooks/use-review.ts`
- `llm-wiki/src/services/real-review.ts`

### Phase F completion slice

Da thay doi:
- them registry `skill package` dang file-based o `backend/skill_packages`
- them API:
  - `GET /api/skills`
  - `GET /api/skills/{id}`
- them review/release API:
  - `POST /api/skills/{id}/comments`
  - `POST /api/skills/{id}/submit-review`
  - `POST /api/skills/{id}/approve`
  - `POST /api/skills/{id}/release`
- them UI browse `Skill Packages`
- them permission `skill:read`
- them permission `skill:write`
- them sample package `multimodal-review-assistant`
- chot scope cua skill trong san pham la `workflow_pack`
- them contribution/review flow toi thieu tren page `Skill Packages`:
  - add comment
  - submit review
  - approve
  - release

Tac dong:
- roadmap khong con `Phase F = chua bat dau`
- reusable workflow package da co metadata, version, scope, review history, va browse/release surface toi thieu
- reviewer co the de lai note va day package qua cac trang thai release co kiem soat

File chinh:
- `backend/app/api/skills.py`
- `backend/app/services/skills.py`
- `backend/skill_packages/multimodal-review-assistant.json`
- `llm-wiki/src/app/(main)/skills/page.tsx`
- `llm-wiki/src/hooks/use-skills.ts`
- `llm-wiki/src/services/{index,types,real-skills}.ts`
- `llm-wiki/src/services/mock/{index,mock-skills}.ts`
- `llm-wiki/src/components/layout/sidebar.tsx`
- `backend/scripts/test_phase55.py`

## Verification

Da chay:
- `python -m compileall backend/app backend/migrations`
- `npm --prefix llm-wiki run build`
- `docker compose up -d --build --force-recreate backend frontend worker`
- `docker compose up -d --build --force-recreate backend`
- smoke auth/query flow tren Docker
- smoke artifact endpoint tren Docker: `/api/sources/{id}/artifacts`
- smoke upload `image_ocr` source tren Docker va verify artifact image URL duoc expose qua `/backend-uploads/...`
- smoke text ingest tren Docker va verify `metadataJson.multimodalArtifacts` duoc persist sau khi source `indexed`
- smoke source-scoped Ask tren Docker va verify:
  - `artifact_summary` xuat hien trong `diagnostics.topCandidates`
  - `artifact_summary` duoc dua vao `diagnostics.selectedContext`
  - citation tra ve `candidateType=artifact_summary` va `artifactType=notebook`
- frontend build sau khi them citation deep-link + artifact highlight
- frontend build sau khi them `Artifact Evidence` grouping va `Ask About Artifact` CTA
- frontend build sau khi them graph inspector action flow cho page/source/ask
- frontend build sau khi them page citation CTA `Inspect source chunk` va `Ask about this citation`
- backend compile sau khi them skill registry va actor audit metadata mo rong
- `backend/scripts/test_phase53.py`
- `backend/scripts/test_phase54.py`
- `backend/scripts/test_phase55.py`
- `backend/scripts/evaluate_quality.py --tag multimodal`
- frontend build sau khi them review comments, skill registry page, va nav entry
- docker rebuild full stack sau khi them image persistence + skill review flow
- smoke auth co token tren Docker:
  - `POST /api/auth/login`
  - `GET /api/auth/me`
  - `GET /api/collections`
  - `GET /api/skills`
  - `GET /api/sources/{id}/artifacts`
  - `POST /api/ask` voi `sourceId` scope

Ket qua:
- backend compile pass
- frontend production build pass
- docker stack rebuild/recreate pass
- auth, collections, search, ask, va source artifact endpoint deu tra ket qua tren local stack
- `image_ocr` upload tra artifact image ngay trong luc job OCR van con xu ly
- source ingest moi co `multimodalArtifacts` manifest persist trong metadata va endpoint artifact tra nhat quan
- source-scoped Ask da retrieve va cite duoc artifact-level evidence tu multimodal manifest
- Ask citation artifact-level co duong dan UX on dinh de mo dung artifact trong source detail
- source artifact da co duong dan UX nguoc lai de mo Ask voi scope/prompt san
- graph node detail da co action flow thang sang page/source/ask va build pass
- page citation panel da co action flow sang source chunk va Ask scoped prompt
- review queue da co comment thread va evidence CTA
- skill registry toi thieu da co API + page browse + sample package
- `test_phase53.py` pass, xac nhan multimodal artifact citation flow van dung
- `test_phase54.py` pass, xac nhan image artifact duoc persist rieng va caption metadata co mat
- `test_phase55.py` pass, xac nhan skill review lifecycle `comment -> submit_review -> approve -> release`
- `evaluate_quality.py --tag multimodal` pass, xac nhan case artifact-aware multimodal summary retrieve dung `artifact_summary`
- docker stack rebuild pass; smoke auth/artifact/skill/ask co token pass tren stack local

Residual risk:
- chua co migration/backfill cho membership data cu vi feature moi chua co du lieu lich su
- chua gate tat ca API bang permission engine; mot so route van con role-based
- chua co automated tests cho scope filtering edge cases
- OCR/image ingest co the mat hon 40 giay cho cold start worker; hien da co fallback hien anh goc trong luc cho artifact semantic xuat hien
- artifact manifest van uu tien text-grounded summary/context; khi runtime khong co multimodal model thi caption se fallback thay vi vision that
- chua co image embedding retrieval hay table semantic parser sau; artifact retrieval hien dua tren caption/summary/prompt surface da persist

## Release readiness re-check - 2026-05-11

Verdict:
- `Local demo / stakeholder review`: YES.
- `Internal beta with controlled users`: YES, after cleaning repo artifacts before handoff.
- `Production release`: NOT YET.

Da verify lai:
- `python -m compileall backend/app backend/migrations backend/scripts` pass.
- `powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild` pass:
  - backend health/readiness 200
  - frontend 200
  - draw.io 200
  - auth smoke pass voi `admin`
- `python backend/scripts/evaluate_quality.py --tag multimodal` pass.
- `python backend/scripts/evaluate_quality.py` pass full gate:
  - retrieval hit rate 1.0
  - retrieval recall@5 1.0
  - rerank precision@5 1.0
  - citation coverage 1.0
  - answer faithfulness 1.0
  - unsupported claim count 0
  - behavior gates all passed
- `npm --prefix llm-wiki run build` pass.

Fix trong lan re-check:
- `backend/scripts/evaluate_quality.py` tu phat hien SQLite eval DB stale.
- Neu `quality_eval.db` local bi lock tren Windows, runner tu dung runtime eval DB moi de khong lam hong quality gate.

Danh gia "thong minh":
- Ask AI da co retrieval diagnostics, citation/provenance, source-scoped ask, conflict/authority handling, follow-up clarification, notebook/artifact evidence, va multimodal artifact summary.
- Workflow da noi duoc `Ask -> citation/source -> page -> graph/review` o muc su dung duoc.
- Permission/scope/admin da co nen tang: login, users, departments, system roles, collection scope.
- Skill package da co metadata/version/scope/review lifecycle toi thieu, phu hop lam internal workflow pack.

Release blockers truoc production:
- Worktree dang rat dirty va co untracked `_tmp_arkon/`; can curate commit/staging, bo artifact nghien cuu ra khoi release package.
- Custom role builder chua that su cho admin tao role tuy bien; hien la system roles/catalog.
- UI admin vua sua nhieu, can Playwright/manual regression cho login, sidebar, users, departments, roles, edit modal.
- Permission engine chua gate 100% tat ca API route; con route role-based.
- Vision/retrieval multimodal hien chu yeu dua tren artifact caption/summary; chua co image embedding retrieval chuyen sau.
- Can secret/env hardening truoc production: JWT secret, CORS, upload limits, data retention, backup/restore, audit export.

## Target/GAP re-plan - 2026-05-12

Status:
- [x] Code audit for Ask AI, storage, notes, permissions, UX workflow, and release readiness.
- [x] Target state defined for smart Ask, smart storage, smart notes, and evidence workflow.
- [x] GAP matrix and implementation order documented.
- [x] Implementation tracking checklist and test tracking checklist documented.
- [x] P0 storage foundation implemented.
- [x] P0 first-class notes implemented.
- [x] P1 Ask intelligence hardening implemented.
- [x] P1 evidence-centered UX implemented.
- [x] P1 permission completion implemented.
- [x] P2 release hardening completed.

Implementation log:
- 2026-05-12: Started P0 storage foundation. Added `StorageObject` model/migration, local + S3-compatible storage write/read path, MinIO service in Docker Compose, source upload storage object persistence, source storage object metadata endpoint, and backend download endpoint.
- 2026-05-12: Continued P0 storage foundation. Added artifact storage object linkage, source detail storage object UI, dry-run orphan cleanup script, and MinIO env defaults.
- 2026-05-12: Started P0 first-class notes. Added `Note`, `NoteAnchor`, and `NoteVersion` model/migration, notes service/API, permission matrix entries, frontend note service/hooks, Ask citation `Save note`, source detail Notes tab, and permission-filtered note candidates in Ask retrieval.
- 2026-05-12: Completed first-class notes foundation. Added source artifact/chunk `Save note`, note search indexing, note-to-page-draft endpoint/action, note-to-review-item endpoint/action, restore endpoint, and authenticated search/Ask note retrieval.
- 2026-05-12: Hardened Ask citation policy for single-source definition/source lookup intents and added `citationPrecision >= 0.9` as a quality gate.
- 2026-05-12: Completed P1 permission route hardening for non-admin business APIs. Jobs, review, settings, Ask save-draft, lint, diagrams, and saved views now use permission dependencies; admin bootstrap/user-management and destructive collection delete remain explicit admin-only boundaries.
- 2026-05-12: Started P1 Ask hardening by extracting citation selection into `backend/app/services/evidence_policy.py` so citation precision policy is independently testable without changing answer behavior.
- 2026-05-12: Added lightweight `answer_verifier` service and Ask diagnostics `answerVerification` so each answer reports support/coverage/citation risk before response persistence.
- 2026-05-12: Added visible Ask UI evidence verification card showing supported/inspect status, coverage, citation count, and risk.
- 2026-05-12: Added shared `EvidenceCard` and `EvidenceDrawer` components, moved Ask citations onto shared evidence UI, added Ask citation inspect drawer/actions, and moved Review source evidence snippets onto shared evidence cards with open/ask actions.
- 2026-05-12: Moved source detail chunk inspector onto shared `EvidenceCard` with Ask scoped and Save note actions.
- 2026-05-12: Improved release smoke reliability by excluding `_tmp_arkon/`, adding MinIO to Docker smoke, authenticating the jobs endpoint in smoke, and moving Redis host port from `6379` to `56379` to avoid local Windows port conflicts.
- 2026-05-12: Hardened `benchmark_retrieval.py` to recreate stale default SQLite benchmark DBs when schema columns are missing.
- 2026-05-12: Added `docs/permissions-and-scope.md`, `docs/PRODUCTION_RELEASE_CHECKLIST.md`, and `docs/RELEASE_NOTES_TEMPLATE.md` to make permission/scope policy and release criteria explicit.
- 2026-05-12: Completed evidence-centered UX pass across Ask, Review, Source Detail, Page Detail, and Graph using shared `EvidenceCard`/`EvidenceDrawer`, with source/page/ask/save-note/review actions wired from evidence surfaces.
- 2026-05-12: Verified admin UX split: Users, Departments, and Roles stay as separate pages; Users uses table/list plus create/edit modal instead of a giant inline form; sidebar active-state now keeps `/admin` exact so child routes do not double-highlight Operations.
- 2026-05-12: Added release hardening scripts for backup/restore smoke and clean seed/reset dry-run, and ignored local `tmp/` backup artifacts from release packaging.
- 2026-05-12: Verified note scope filtering with Docker API smoke: private anchored notes are visible to owner only, workspace notes are visible to allowed readers, and collection notes do not leak to restricted users outside the collection.
- 2026-05-12: Added deterministic citation evidence grading (`relevance`, `specificity`, `authority`, `freshness`, `termCoverage`, `contradictionRisk`) and per-citation reasons from `evidence_policy.py`; Ask UI now shows the reason/grade on evidence cards and drawers.
- 2026-05-12: Added `POST /api/ask/feedback` for `helpful`, `wrong`, `missing_source`, and `bad_citation` feedback, persisted as `ask_feedback` audit log entries without changing answer generation.
- 2026-05-12: Extracted Ask retrieval orchestration into `backend/app/services/retrieval_candidates.py` and context selection into `backend/app/services/context_assembly.py`; `query.py` now keeps DB-specific scoring helpers and answer orchestration.
- 2026-05-12: Completed clean Docker release-candidate reset from empty volumes via `scripts/clean_seed_reset.ps1 -Apply`; migrations, seed/bootstrap, MinIO bucket, backend, worker, frontend, and smoke checks passed from a fresh stack.

Verification:
- 2026-05-12: `python -m compileall backend/app backend/migrations` pass.
- 2026-05-12: `python -m alembic heads` shows `0016_storage_objects (head)`.
- 2026-05-12: local storage adapter smoke pass with `STORAGE_BACKEND=local`.
- 2026-05-12: `docker compose config --quiet` pass after adding MinIO service.
- 2026-05-12: `npm --prefix llm-wiki run build` pass after source storage UI and Ask note action.
- 2026-05-12: SQLite notes smoke pass: create note with Ask citation anchor, list by source, verify anchor citation id.
- 2026-05-12: `python backend/scripts/evaluate_quality.py` pass with citationPrecision `1.0`, unsupportedClaimCount `0`, and all quality gates passed including the new citationPrecision gate.
- 2026-05-12: Docker backend/worker/minio rebuild pass after Docker Desktop started; MinIO healthy on `19000/19001`.
- 2026-05-12: MinIO storage smoke pass through API: `POST /api/sources/upload` created source `src-784d2e01`, storage object `sto-c2bde0d23b`, backend `s3`, bucket `llm-wiki`; backend download endpoint returned 20 bytes with expected content.
- 2026-05-12: `python -m compileall backend/app backend/migrations backend/scripts` pass after permission route hardening.
- 2026-05-12: Docker backend/worker rebuild pass after permission changes.
- 2026-05-12: Permission smoke pass: admin `GET /api/settings` = 200, admin `GET /api/jobs` = 200, reader `GET /api/saved-views` = 200, reader `GET /api/settings` = 403.
- 2026-05-12: `python backend/scripts/evaluate_quality.py` pass after evidence policy extraction; citationPrecision remains `1.0`, unsupportedClaimCount remains `0`.
- 2026-05-12: `python -m compileall backend/app backend/migrations backend/scripts` and `python backend/scripts/evaluate_quality.py` pass after answer verifier; quality gates remain all passed.
- 2026-05-12: `npm --prefix llm-wiki run build` pass after adding frontend `answerVerification` diagnostics type.
- 2026-05-12: Docker backend/worker rebuild pass after Ask verifier changes; API smoke `POST /api/ask` returned one citation and `answerVerification.supported=true`, coverage `1.0`, risk `low`.
- 2026-05-12: `npm --prefix llm-wiki run build` pass after Ask evidence verification UI; Docker frontend rebuilt and recreated, all core containers healthy on `3100`, `18000`, `55432`, `19000/19001`.
- 2026-05-12: Permission role smoke pass: reader settings 403/saved views 200, editor lint 200/settings 403, reviewer settings read 200/write 403, admin settings/jobs 200.
- 2026-05-12: `powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild` pass after Redis port change; backend, frontend, draw.io, MinIO all returned OK.
- 2026-05-12: `python backend/scripts/benchmark_retrieval.py` pass after stale SQLite guard; all benchmark quality gates passed.
- 2026-05-12: `npm --prefix llm-wiki run build`, `python backend/scripts/evaluate_quality.py`, and Docker frontend rebuild/recreate pass after shared evidence card/drawer; all containers healthy.
- 2026-05-12: `npm --prefix llm-wiki run build` pass after source detail shared evidence card integration.
- 2026-05-12: `npm --prefix llm-wiki run build`, `python backend/scripts/evaluate_quality.py`, `python backend/scripts/benchmark_retrieval.py`, and `python -m compileall backend/app backend/migrations backend/scripts` pass after Page/Graph evidence drawer work.
- 2026-05-12: Docker frontend/backend rebuild and recreate pass; `powershell -ExecutionPolicy Bypass -File .\scripts\docker_smoke.ps1 -SkipBuild` pass with backend, frontend, draw.io, MinIO, auth, collections, and jobs checks.
- 2026-05-12: `powershell -ExecutionPolicy Bypass -File .\scripts\backup_restore_smoke.ps1` pass: Postgres custom dump can be listed by `pg_restore`, and MinIO bucket is listable.
- 2026-05-12: Docker scope smoke pass: private note search hits owner=1/reader=0; workspace note visible to reader; collection note visible to admin and hidden from restricted user outside collection.
- 2026-05-12: Docker Ask feedback smoke pass: `POST /api/ask` returned one citation with `evidenceGrade` and `citationReason`; `POST /api/ask/feedback` returned success with rating `helpful`.
- 2026-05-12: `python backend/scripts/evaluate_quality.py` pass after citation grading and feedback endpoint; citationPrecision remains `1.0`, unsupportedClaimCount remains `0`, all quality gates passed.
- 2026-05-12: `python -m compileall backend/app backend/migrations backend/scripts`, `python backend/scripts/evaluate_quality.py`, and `npm --prefix llm-wiki run build` pass after retrieval/context refactor.
- 2026-05-12: Fresh-stack `scripts/clean_seed_reset.ps1 -Apply` pass after confirmed destructive reset; follow-up `scripts/docker_smoke.ps1 -SkipBuild` pass with `Collections=3`, `Jobs=4`, authenticated admin, frontend, backend, draw.io, and MinIO OK.
- 2026-05-12: `python backend/scripts/benchmark_retrieval.py` pass after clean reset; benchmark quality gates all passed.

New planning document:
- `docs/ai-knowledge-workspace-gap-plan-2026.md`

Key conclusion:
- Ask AI is usable and already beyond demo-level, but production intelligence now depends on storage, notes, and evidence workflow foundations.
- Biggest gaps: MinIO/S3-backed storage, first-class anchored notes, evidence drawer/actions, permission completion, and release packaging cleanup.
