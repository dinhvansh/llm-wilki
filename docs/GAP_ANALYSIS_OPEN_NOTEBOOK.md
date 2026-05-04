# Gap Analysis: `open-notebook` vs `LLM Wiki`

Tai lieu nay doi chieu nhanh giua repo hien tai va `open-notebook` de xac dinh:

- cai gi nen hoc ngay
- cai gi nen hoc sau
- cai gi khong nen copy mu

Muc tieu khong phai la bien `LLM Wiki` thanh ban sao cua `open-notebook`, ma la lay dung nhung pattern giup repo nay de scale va de van hanh hon.

## 1. Tong ket nhanh

### `open-notebook` dang hon o dau

1. Provider/model abstraction
2. Error taxonomy va exception handling
3. Module boundaries backend/frontend
4. Developer tooling va packaging
5. Product-grade documentation/onboarding

### `LLM Wiki` dang hon o dau

1. Workflow review/publish/wiki governance dung domain
2. Audit trail va admin operations
3. Lint/quality layer cho content knowledge base
4. Docker stack tach ro backend/worker/frontend/postgres/redis

## 2. Doi chieu theo nhom

### A. Provider va model lifecycle

#### Hien trang `LLM Wiki`

- Runtime provider config duoc luu theo profile co dinh trong [backend/app/core/runtime_config.py](</mnt/d/AI-native wiki platform/backend/app/core/runtime_config.py>)
- Logic goi provider nam trong [backend/app/core/llm_client.py](</mnt/d/AI-native wiki platform/backend/app/core/llm_client.py>)
- Frontend settings dang cho user nhap truc tiep provider/model trong [llm-wiki/src/app/(main)/settings/page.tsx](</mnt/d/AI-native wiki platform/llm-wiki/src/app/(main)/settings/page.tsx>)

#### Pattern tu `open-notebook`

- Co model discovery va capability classification trong [open-notebook-main/open-notebook-main/open_notebook/ai/model_discovery.py](</mnt/d/AI-native wiki platform/open-notebook-main/open-notebook-main/open_notebook/ai/model_discovery.py>)
- Model duoc xem la resource co metadata va capability, khong chi la string config

#### Diem thieu hien tai

- Chua co model registry
- Chua auto-discover model theo provider
- Chua phan biet ro language model / embedding model / speech model
- Them provider moi se tiep tuc phinh `if/else`

#### Loi ich neu hoc theo

- De support them provider ma khong be code
- Settings UI ro hon, co the chon model tu danh sach that
- Giam loi config sai tay

#### Effort

- Trung binh -> cao

#### Uu tien

- **Nen lam ngay**

---

### B. Error taxonomy va exception handling

#### Hien trang `LLM Wiki`

- Nhieu API raise `HTTPException` truc tiep trong router, vi du [backend/app/api/pages.py](</mnt/d/AI-native wiki platform/backend/app/api/pages.py>) va [backend/app/api/sources.py](</mnt/d/AI-native wiki platform/backend/app/api/sources.py>)
- LLM client hien tai nuot loi va tra `None` trong [backend/app/core/llm_client.py](</mnt/d/AI-native wiki platform/backend/app/core/llm_client.py>)
- Error connector co taxonomy rieng nho trong [backend/app/core/connectors.py](</mnt/d/AI-native wiki platform/backend/app/core/connectors.py>) nhung chua thanh he thong chung

#### Pattern tu `open-notebook`

- Co error classifier rieng trong [open-notebook-main/open-notebook-main/open_notebook/utils/error_classifier.py](</mnt/d/AI-native wiki platform/open-notebook-main/open-notebook-main/open_notebook/utils/error_classifier.py>)
- Co exception handler tap trung o [open-notebook-main/open-notebook-main/api/main.py](</mnt/d/AI-native wiki platform/open-notebook-main/open-notebook-main/api/main.py>)

#### Diem thieu hien tai

- Chua co `AppError`/`ProviderError` dung chung
- Khong phan biet ro validation error, auth error, rate-limit error, provider unavailable, config error
- Kho thong ke va kho hien thi message nhat quan tren UI

#### Loi ich neu hoc theo

- API contract nhat quan hon
- UI co the xu ly loi theo type thay vi string match
- Logs va audit co gia tri hon khi dieu tra su co

#### Effort

- Trung binh

#### Uu tien

- **Nen lam ngay**

---

### C. Module boundaries backend

#### Hien trang `LLM Wiki`

- Business logic dang tap trung rat nhieu trong `backend/app/services/*`
- Nhung file lon nhu [backend/app/services/query.py](</mnt/d/AI-native wiki platform/backend/app/services/query.py>) va [backend/app/services/sources.py](</mnt/d/AI-native wiki platform/backend/app/services/sources.py>) dang gan nhieu trach nhiem trong mot module

#### Pattern tu `open-notebook`

- Chia package theo capability/domain: `ai`, `domain`, `database`, `utils`
- Data access co lop dung lai trong [open-notebook-main/open-notebook-main/open_notebook/database/repository.py](</mnt/d/AI-native wiki platform/open-notebook-main/open-notebook-main/open_notebook/database/repository.py>)

#### Diem thieu hien tai

- Service layer dang la noi gom ca orchestration, query logic, serialization, retrieval, side effects
- Kho chia ownership khi repo lon len
- Refactor sau nay se ton hon neu de muon

#### Loi ich neu hoc theo

- De test tung khuc logic
- De tach module retrieval/provider/review/ops
- De giao viec theo module neu team lon hon

#### Effort

- Cao

#### Uu tien

- **Nen hoc sau**

---

### D. Frontend app foundation

#### Hien trang `LLM Wiki`

- API client dang kha mong o [llm-wiki/src/services/api-client.ts](</mnt/d/AI-native wiki platform/llm-wiki/src/services/api-client.ts>)
- Auth state dung context/localStorage trong [llm-wiki/src/providers/auth-provider.tsx](</mnt/d/AI-native wiki platform/llm-wiki/src/providers/auth-provider.tsx>)
- Services phan bo theo module nghiep vu la hop ly, nhung lifecycle auth/error/retry chua tap trung

#### Pattern tu `open-notebook`

- Axios client co interceptor o [open-notebook-main/open-notebook-main/frontend/src/lib/api/client.ts](</mnt/d/AI-native wiki platform/open-notebook-main/open-notebook-main/frontend/src/lib/api/client.ts>)
- Auth state tach store rieng trong [open-notebook-main/open-notebook-main/frontend/src/lib/stores/auth-store.ts](</mnt/d/AI-native wiki platform/open-notebook-main/open-notebook-main/frontend/src/lib/stores/auth-store.ts>)

#### Diem thieu hien tai

- Chua co xu ly 401/expiry/re-auth dong bo
- Chua co central response normalization
- Co nguy co logic auth bi lap lai khi frontend tang scope

#### Loi ich neu hoc theo

- Frontend de scale hon
- De them retry, toast, redirect, request tracing
- Giam bug auth state khong dong nhat

#### Effort

- Trung binh

#### Uu tien

- **Nen lam ngay**

---

### E. Developer tooling va release ergonomics

#### Hien trang `LLM Wiki`

- Co cac script thuc dung o `scripts/`:
  - [scripts/run_regression.ps1](</mnt/d/AI-native wiki platform/scripts/run_regression.ps1>)
  - [scripts/docker_smoke.ps1](</mnt/d/AI-native wiki platform/scripts/docker_smoke.ps1>)
  - [scripts/e2e_smoke.ps1](</mnt/d/AI-native wiki platform/scripts/e2e_smoke.ps1>)
  - [scripts/reset_local.ps1](</mnt/d/AI-native wiki platform/scripts/reset_local.ps1>)
- Docker stack kha ro o [docker-compose.yml](</mnt/d/AI-native wiki platform/docker-compose.yml>)

#### Pattern tu `open-notebook`

- Co task entrypoint thong nhat trong [open-notebook-main/open-notebook-main/Makefile](</mnt/d/AI-native wiki platform/open-notebook-main/open-notebook-main/Makefile>)
- Python packaging/dev tooling gom trong [open-notebook-main/open-notebook-main/pyproject.toml](</mnt/d/AI-native wiki platform/open-notebook-main/open-notebook-main/pyproject.toml>)

#### Diem thieu hien tai

- Chua co mot diem vao duy nhat cho dev workflow
- Lenh van hanh/contributor phu thuoc nho script name
- Python tooling chua gom thanh package/dev profile ro rang

#### Loi ich neu hoc theo

- Repo de onboarding hon
- CI/CD de quy uoc hon
- Giam chi phi nho lenh cho team

#### Effort

- Thap -> trung binh

#### Uu tien

- **Nen lam ngay**

---

### F. Tai lieu va contributor guidance

#### Hien trang `LLM Wiki`

- Root README da du sat project o [README.md](</mnt/d/AI-native wiki platform/README.md>)
- Da co docs cho user va flow nghiep vu:
  - [docs/HUONG_DAN_SU_DUNG.md](</mnt/d/AI-native wiki platform/docs/HUONG_DAN_SU_DUNG.md>)
  - [docs/FLOW_NGHIEP_VU.md](</mnt/d/AI-native wiki platform/docs/FLOW_NGHIEP_VU.md>)
  - [docs/FLOW_XU_LY_HE_THONG.md](</mnt/d/AI-native wiki platform/docs/FLOW_XU_LY_HE_THONG.md>)

#### Pattern tu `open-notebook`

- README co tinh product onboarding manh hon
- Co local guidance theo module trong nhieu `CLAUDE.md`

#### Diem thieu hien tai

- Chua co maintainer guidance theo tung module
- Chua co doc “kien truc cho dev moi vao”
- Chua co quy uoc sua code theo module ownership

#### Loi ich neu hoc theo

- Giam chi phi onboarding contributor
- Giam sua sai pattern kien truc

#### Effort

- Thap

#### Uu tien

- **Nen hoc sau**

---

### G. Domain workflow va governance

#### Hien trang `LLM Wiki`

- Manh ve review, lint, audit, admin ops:
  - [backend/app/api/review.py](</mnt/d/AI-native wiki platform/backend/app/api/review.py>)
  - [backend/app/services/lint.py](</mnt/d/AI-native wiki platform/backend/app/services/lint.py>)
  - [backend/app/services/audit.py](</mnt/d/AI-native wiki platform/backend/app/services/audit.py>)
  - [backend/app/api/admin.py](</mnt/d/AI-native wiki platform/backend/app/api/admin.py>)
  - [backend/app/core/observability.py](</mnt/d/AI-native wiki platform/backend/app/core/observability.py>)

#### Pattern tu `open-notebook`

- Manh o AI workbench va provider architecture, nhung khong phai bai toan governance wiki noi bo giong minh

#### Danh gia

- Day la phan **khong nen copy mu**
- Day cung la phan repo minh nen giu lam loi the rieng

#### Uu tien

- **Giu nguyen dinh huong, khong doi theo `open-notebook`**

## 3. Danh sach khuyen nghi hanh dong

### Nhom 1: Nen lam ngay

1. Tao `AppError` + `ProviderError` + global exception mapper
2. Refactor `llm_client` va `embedding_client` theo provider registry
3. Them model registry/discovery cho settings
4. Nang cap frontend API client + auth store
5. Them task runner chung cho local/dev/test/docker

### Nhom 2: Nen hoc sau

1. Tach `services/*` thanh package theo domain/capability
2. Them data access abstractions dung muc
3. Bo sung maintainer docs theo module

### Nhom 3: Khong nen copy mu

1. Kien truc all-in-one cho moi use case AI
2. Tang abstraction cho speech/media neu project chua can
3. Di chuyen theo database/model cua ho chi vi thay “co ve dep”

## 4. De xuat phase tiep theo

Neu mo them mot phase sau Phase 22, thu tu hop ly nhat la:

### Phase 23 - Reliability va Provider Architecture

Checklist de xuat:

- [ ] Them `AppError` taxonomy va global exception handlers
- [ ] Chuan hoa provider error mapping cho LLM va embedding
- [ ] Tao provider registry cho `openai`, `anthropic`, `ollama`, `openai_compatible`
- [ ] Tach model metadata/capability khoi raw string settings
- [ ] Nang cap frontend `api-client` de xu ly 401, typed error, request correlation
- [ ] Them task runner gom local/dev/test/docker commands
- [ ] Viet tai lieu contributor architecture ngan cho phase moi

## 5. Ket luan

`open-notebook` la repo dang hoc o cach lam san pham va cach to chuc he thong AI tong quat.  
`LLM Wiki` khong thua o huong domain, nhung dang thieu nen tang ky thuat de scale sach.

Neu chi lay mot cau ket luan:

- `open-notebook` cho minh hoc **cach xay nen tang**
- `LLM Wiki` dang dung de xay **dung bai toan**

Huong dung la giu domain cua minh, nhung hoc kien truc cua ho o nhung lop nen.
