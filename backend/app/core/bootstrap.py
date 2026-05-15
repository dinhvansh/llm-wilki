from datetime import datetime, timezone

from sqlalchemy import inspect, text
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
    _ensure_page_content_json_column()
    _ensure_diagram_flow_document_columns()
    _ensure_entity_management_columns()
    _ensure_runtime_secret_columns()
    _backfill_page_content_json(db)
    _backfill_diagram_flow_documents(db)
    _backfill_entity_management_fields(db)
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


def _ensure_page_content_json_column() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("pages")}
    if "content_json" in columns:
        return
    statement = "ALTER TABLE pages ADD COLUMN content_json JSON"
    with engine.begin() as connection:
        connection.execute(text(statement))


def _ensure_diagram_flow_document_columns() -> None:
    inspector = inspect(engine)
    json_sql = "JSONB" if engine.dialect.name == "postgresql" else "JSON"
    statements: list[str] = []
    diagram_columns = {column["name"] for column in inspector.get_columns("diagrams")}
    version_columns = {column["name"] for column in inspector.get_columns("diagram_versions")}
    if "flow_document" not in diagram_columns:
        statements.append(f"ALTER TABLE diagrams ADD COLUMN flow_document {json_sql}")
    if "flow_document" not in version_columns:
        statements.append(f"ALTER TABLE diagram_versions ADD COLUMN flow_document {json_sql}")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _ensure_entity_management_columns() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("entities")}
    statements: list[str] = []
    dialect = engine.dialect.name
    datetime_sql = "TIMESTAMP WITH TIME ZONE" if dialect == "postgresql" else "DATETIME"
    json_sql = "JSONB" if dialect == "postgresql" else "JSON"
    if "status" not in columns:
        statements.append("ALTER TABLE entities ADD COLUMN status VARCHAR(32) DEFAULT 'active'")
    if "verification_status" not in columns:
        statements.append("ALTER TABLE entities ADD COLUMN verification_status VARCHAR(32) DEFAULT 'unverified'")
    if "merged_into_entity_id" not in columns:
        statements.append("ALTER TABLE entities ADD COLUMN merged_into_entity_id VARCHAR(64)")
    if "reviewed_at" not in columns:
        statements.append(f"ALTER TABLE entities ADD COLUMN reviewed_at {datetime_sql}")
    if "reviewed_by" not in columns:
        statements.append("ALTER TABLE entities ADD COLUMN reviewed_by VARCHAR(128)")
    if "updated_at" not in columns:
        statements.append(f"ALTER TABLE entities ADD COLUMN updated_at {datetime_sql}")
    if "metadata_json" not in columns:
        statements.append(f"ALTER TABLE entities ADD COLUMN metadata_json {json_sql}")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _ensure_runtime_secret_columns() -> None:
    if engine.dialect.name != "postgresql":
        return
    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("runtime_config")}
    secret_columns = ("answer_api_key", "ingest_api_key", "embedding_api_key")
    statements = []
    for column_name in secret_columns:
        column_type = str(columns.get(column_name, {}).get("type", "")).lower()
        if "text" not in column_type:
            statements.append(f"ALTER TABLE runtime_config ALTER COLUMN {column_name} TYPE TEXT")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _backfill_page_content_json(db: Session) -> None:
    from app.services.page_blocks import markdown_to_blocks

    pages = db.query(Page).all()
    changed = False
    for page in pages:
        if page.content_json:
            continue
        page.content_json = markdown_to_blocks(page.content_md)
        changed = True
    if changed:
        db.commit()


def _backfill_diagram_flow_documents(db: Session) -> None:
    from app.services.diagrams import flow_document_from_spec

    changed = False
    for diagram in db.query(Diagram).all():
        if diagram.flow_document:
            continue
        diagram.flow_document = flow_document_from_spec(
            diagram.spec_json or {},
            title=diagram.title,
            objective=diagram.objective or "",
            owner=diagram.owner,
            source_page_ids=diagram.source_page_ids or [],
            source_ids=diagram.source_ids or [],
        )
        changed = True
    for version in db.query(DiagramVersion).all():
        if version.flow_document:
            continue
        diagram = db.query(Diagram).filter(Diagram.id == version.diagram_id).first()
        version.flow_document = flow_document_from_spec(
            version.spec_json or {},
            title=diagram.title if diagram else "",
            objective=diagram.objective if diagram else "",
            owner=diagram.owner if diagram else "",
            source_page_ids=diagram.source_page_ids if diagram else [],
            source_ids=diagram.source_ids if diagram else [],
        )
        changed = True
    if changed:
        db.commit()


def _backfill_entity_management_fields(db: Session) -> None:
    now = datetime.now(timezone.utc)
    changed = False
    for entity in db.query(Entity).all():
        if not entity.status:
            entity.status = "active"
            changed = True
        if not entity.verification_status:
            entity.verification_status = "unverified"
            changed = True
        if entity.updated_at is None:
            entity.updated_at = entity.created_at or now
            changed = True
        if entity.metadata_json is None:
            entity.metadata_json = {}
            changed = True
    if changed:
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
