from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.demo_data import build_demo_dataset
from app.db.database import Base, engine
from app.models import (
    AuditLog,
    Claim,
    ClaimRelation,
    ChatMessage,
    ChatSession,
    Collection,
    Diagram,
    DiagramVersion,
    Entity,
    GlossaryTerm,
    Job,
    Page,
    PageClaimLink,
    PageEntityLink,
    PageLink,
    PageSourceLink,
    PageVersion,
    ReviewIssue,
    ReviewItem,
    ReviewComment,
    RuntimeConfig,
    SavedView,
    Source,
    SourceEntityLink,
    SourceSuggestion,
    SourceChunk,
    TimelineEvent,
    User,
    AuthSession,
)
from app.services.auth import ensure_dev_admin_user


def init_database(db: Session, seed_demo_data: bool = True) -> None:
    Base.metadata.create_all(bind=engine)
    ensure_dev_admin_user(db)
    has_sources = db.query(Source.id).first()
    if has_sources:
        _ensure_demo_collections(db)
    if not seed_demo_data or has_sources:
        return

    dataset = build_demo_dataset()
    db.add_all(Collection(**record) for record in dataset["collections"])
    db.flush()
    db.add_all(Source(**record) for record in dataset["sources"])
    db.flush()
    db.add_all(SourceChunk(**record) for record in dataset["chunks"])
    db.flush()
    db.add_all(Entity(**record) for record in dataset["entities"])
    db.flush()
    db.add_all(Claim(**record) for record in dataset["claims"])
    db.flush()
    db.add_all(ClaimRelation(**record) for record in dataset["claim_relations"])
    db.flush()
    db.add_all(Page(**record) for record in dataset["pages"])
    db.flush()
    db.add_all(PageVersion(**record) for record in dataset["page_versions"])
    db.flush()
    db.add_all(PageClaimLink(**record) for record in dataset["page_claim_links"])
    db.flush()
    db.add_all(PageLink(**record) for record in dataset["page_links"])
    db.flush()
    db.add_all(PageSourceLink(**record) for record in dataset["page_source_links"])
    db.flush()
    db.add_all(Job(**record) for record in dataset["jobs"])
    db.flush()
    db.add_all(ReviewItem(**record) for record in dataset["review_items"])
    db.flush()
    db.add_all(ReviewIssue(**record) for record in dataset["review_issues"])
    db.commit()


def _ensure_demo_collections(db: Session) -> None:
    if db.query(Collection.id).first():
        return

    now = datetime.now(timezone.utc)
    collections = [
        Collection(
            id="col-001",
            name="Governance & Compliance",
            slug="governance-compliance",
            description="Policies, compliance processes, safety controls, and audit evidence.",
            color="emerald",
            created_at=now,
            updated_at=now,
        ),
        Collection(
            id="col-002",
            name="Engineering Standards",
            slug="engineering-standards",
            description="LLM architecture, API standards, RAG, and technical implementation references.",
            color="blue",
            created_at=now,
            updated_at=now,
        ),
        Collection(
            id="col-003",
            name="Operations Playbooks",
            slug="operations-playbooks",
            description="SOPs and internal workflow documentation for knowledge operations.",
            color="amber",
            created_at=now,
            updated_at=now,
        ),
    ]
    db.add_all(collections)
    db.flush()

    for source in db.query(Source).all():
        terms = " ".join([source.title or "", source.description or "", " ".join(source.tags or [])]).lower()
        if any(term in terms for term in ["policy", "governance", "compliance", "safety"]):
            source.collection_id = "col-001"
        elif any(term in terms for term in ["sop", "operations", "workflow", "processing"]):
            source.collection_id = "col-003"
        elif any(term in terms for term in ["technical", "llm", "rag", "api", "engineering"]):
            source.collection_id = "col-002"

    page_source_collections = {
        page_id: collection_id
        for page_id, collection_id in db.query(PageSourceLink.page_id, Source.collection_id)
        .join(Source, Source.id == PageSourceLink.source_id)
        .filter(Source.collection_id.is_not(None))
        .all()
    }
    for page in db.query(Page).all():
        if page.id in page_source_collections:
            page.collection_id = page_source_collections[page.id]
            continue
        terms = " ".join([page.title or "", page.summary or "", " ".join(page.tags or [])]).lower()
        if any(term in terms for term in ["policy", "governance", "compliance", "safety"]):
            page.collection_id = "col-001"
        elif any(term in terms for term in ["sop", "operations", "workflow", "processing"]):
            page.collection_id = "col-003"
        elif any(term in terms for term in ["technical", "llm", "rag", "api", "engineering"]):
            page.collection_id = "col-002"

    db.commit()
