# LLM Wiki Upgrade Plan

Roadmap nay duoc lap dua tren trang thai code hien tai va target trong `hybrid-rag-karpathy-llm-wiki-prompts.md`.

## Phase 1: Foundation Data And Retrieval

Muc tieu:
- dua retrieval tu heuristic len hybrid retrieval co embeddings that
- mo duong cho citation, auto-link, lint, va graph semantic o cac phase sau

Checklist:
- [x] Them migration/schema cho embedding persistence tren `source_chunks`
- [x] Viet `embedding_client.py`
- [x] Ho tro `ollama` embeddings
- [x] Ho tro `openai-compatible` embeddings
- [x] Gan embedding vao ingest pipeline
- [x] Viet retrieval layer moi co dung embeddings khi kha dung
- [x] Refactor `query.py` sang hybrid retrieval moi
- [x] Them citation serializer chuan hon theo chunk/span
- [x] Them embedding test API
- [x] Cap nhat Settings UI de test embedding connection
- [x] Verify voi query exact match va paraphrase

Acceptance criteria:
- ingest source xong co embedding that cho chunk neu provider duoc cau hinh
- `ask/search` uu tien embedding similarity neu co
- Settings embedding co tac dung that va test duoc

## Phase 2: Knowledge Extraction And Page Types

Checklist:
- [x] Tach extraction pipeline theo stage
- [x] Them classifier cho page type candidates
- [x] Nang entity extraction
- [x] Them timeline extraction
- [x] Them glossary extraction
- [x] Them schema page-entity/source relations day du hon
- [x] Mo rong `pages` API cho page type
- [x] Them man `Entity Explorer`
- [x] Them man `Timeline Explorer`
- [x] Them man `Glossary`

## Phase 3: Auto-Link And Review Workflow

Checklist:
- [x] Thiet ke suggestion model
- [x] Them match engine source -> page/entity
- [x] Them stale/conflict heuristics
- [x] Refactor review schema cho page-level va update-level
- [x] Nang review API
- [x] Nang diff viewer
- [x] Them merge action
- [x] Them backlinks data
- [x] Test approve/reject/rebuild/merge flow

## Phase 4: Lint And Graph Upgrade

Checklist:
- [x] Viet lint engine framework
- [x] Them 6 rule lint co ban
- [x] Tao lint API
- [x] Tao `Lint Center`
- [x] Refactor graph data model
- [x] Them local graph mode
- [x] Them semantic filters
- [x] Them node detail panel

## Phase 5: Editor And Workspace UX

Checklist:
- [x] Chon editor strategy
- [x] Them split edit/preview
- [x] Them backlinks panel
- [x] Them collection tree
- [x] Them saved views
- [x] Nang source viewer
- [x] Test desktop/mobile layout

## Notes

- Chi tick cac muc da lam xong va da test.
- Uu tien hien tai: hoan tat Phase 1 truoc khi mo rong graph/editor.
- Phase 1 test script: `python backend/scripts/test_phase1.py`
- Phase 2 test script: `python backend/scripts/test_phase2.py`
- Phase 3 test scripts: `python backend/scripts/test_phase3.py`, `python backend/scripts/test_phase3_flow.py`
- Phase 4 test script: `python backend/scripts/test_phase4.py`
- Phase 5 test command: `npm run build` in `llm-wiki`
