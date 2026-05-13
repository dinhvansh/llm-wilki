from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(512))
    url: Mapped[str | None] = mapped_column(String(512))
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ingest_status: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    collection_id: Mapped[str | None] = mapped_column(ForeignKey("collections.id"), index=True)

    chunks: Mapped[list["SourceChunk"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    artifacts: Mapped[list["SourceArtifactRecord"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    knowledge_units: Mapped[list["KnowledgeUnit"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    extraction_runs: Mapped[list["ExtractionRun"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    page_links: Mapped[list["PageSourceLink"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    suggestions: Mapped[list["SourceSuggestion"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    storage_objects: Mapped[list["StorageObject"]] = relationship(back_populates="source")
    collection: Mapped["Collection | None"] = relationship(back_populates="sources")


class StorageObject(Base):
    __tablename__ = "storage_objects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    backend: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    bucket: Mapped[str | None] = mapped_column(String(255), index=True)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    local_path: Mapped[str | None] = mapped_column(String(1024))
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    content_type: Mapped[str | None] = mapped_column(String(128))
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum_sha256: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    owner: Mapped[str] = mapped_column(String(128), nullable=False, default="system", index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), index=True)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("source_artifacts.id"), index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    source: Mapped["Source | None"] = relationship(back_populates="storage_objects")
    artifact: Mapped["SourceArtifactRecord | None"] = relationship(back_populates="storage_objects")


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(32), nullable=False, default="slate")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    sources: Mapped[list["Source"]] = relationship(back_populates="collection")
    pages: Mapped[list["Page"]] = relationship(back_populates="collection")
    diagrams: Mapped[list["Diagram"]] = relationship(back_populates="collection")
    memberships: Mapped[list["CollectionMembership"]] = relationship(back_populates="collection", cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship(back_populates="collection")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="department")


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str] = mapped_column(String(255), default="")
    page_number: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    span_start: Mapped[int] = mapped_column(Integer, nullable=False)
    span_end: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    source: Mapped["Source"] = relationship(back_populates="chunks")
    claims: Mapped[list["Claim"]] = relationship(back_populates="source_chunk", cascade="all, delete-orphan")
    knowledge_units: Mapped[list["KnowledgeUnit"]] = relationship(back_populates="source_chunk", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="private", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    owner_name: Mapped[str] = mapped_column(String(128), nullable=False, default="Current User", index=True)
    collection_id: Mapped[str | None] = mapped_column(ForeignKey("collections.id"), index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    archived_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), index=True)

    anchors: Mapped[list["NoteAnchor"]] = relationship(back_populates="note", cascade="all, delete-orphan")
    versions: Mapped[list["NoteVersion"]] = relationship(back_populates="note", cascade="all, delete-orphan")
    owner: Mapped["User | None"] = relationship(back_populates="notes")
    collection: Mapped["Collection | None"] = relationship(back_populates="notes")


class NoteAnchor(Base):
    __tablename__ = "note_anchors"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str | None] = mapped_column(String(128), index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), index=True)
    chunk_id: Mapped[str | None] = mapped_column(ForeignKey("source_chunks.id"), index=True)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("source_artifacts.id"), index=True)
    page_id: Mapped[str | None] = mapped_column(ForeignKey("pages.id"), index=True)
    section_key: Mapped[str | None] = mapped_column(String(128), index=True)
    review_item_id: Mapped[str | None] = mapped_column(ForeignKey("review_items.id"), index=True)
    ask_message_id: Mapped[str | None] = mapped_column(ForeignKey("chat_messages.id"), index=True)
    citation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    snippet: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    note: Mapped["Note"] = relationship(back_populates="anchors")


class NoteVersion(Base):
    __tablename__ = "note_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    change_summary: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    note: Mapped["Note"] = relationship(back_populates="versions")


class SourceArtifactRecord(Base):
    __tablename__ = "source_artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="available")
    content_type: Mapped[str | None] = mapped_column(String(128))
    summary: Mapped[str | None] = mapped_column(Text)
    preview_text: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(512))
    page_number: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    source: Mapped["Source"] = relationship(back_populates="artifacts")
    storage_objects: Mapped[list["StorageObject"]] = relationship(back_populates="artifact")


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unverified", index=True)
    merged_into_entity_id: Mapped[str | None] = mapped_column(String(64), index=True)
    reviewed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(128))
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    source_links: Mapped[list["SourceEntityLink"]] = relationship(back_populates="entity", cascade="all, delete-orphan")
    page_links: Mapped[list["PageEntityLink"]] = relationship(back_populates="entity", cascade="all, delete-orphan")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_chunk_id: Mapped[str] = mapped_column(ForeignKey("source_chunks.id"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    canonical_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    extracted_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(128))
    entity_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    extraction_method: Mapped[str] = mapped_column(String(32), nullable=False, default="heuristic")
    evidence_span_start: Mapped[int | None] = mapped_column(Integer)
    evidence_span_end: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    source_chunk: Mapped["SourceChunk"] = relationship(back_populates="claims")
    page_links: Mapped[list["PageClaimLink"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    knowledge_units: Mapped[list["KnowledgeUnit"]] = relationship(back_populates="claim", cascade="all, delete-orphan")


class KnowledgeUnit(Base):
    __tablename__ = "knowledge_units"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    source_chunk_id: Mapped[str | None] = mapped_column(ForeignKey("source_chunks.id"), index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id"), index=True)
    unit_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="draft")
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="pending")
    canonical_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="proposed")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    topic: Mapped[str | None] = mapped_column(String(128))
    entity_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_span_start: Mapped[int | None] = mapped_column(Integer)
    evidence_span_end: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    source: Mapped["Source"] = relationship(back_populates="knowledge_units")
    source_chunk: Mapped["SourceChunk | None"] = relationship(back_populates="knowledge_units")
    claim: Mapped["Claim | None"] = relationship(back_populates="knowledge_units")


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    run_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(32), nullable=False, default="heuristic")
    task_profile: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    model_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    input_chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    finished_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), index=True)

    source: Mapped["Source"] = relationship(back_populates="extraction_runs")


class ClaimRelation(Base):
    __tablename__ = "claim_relations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    from_claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id"))
    from_entity_id: Mapped[str | None] = mapped_column(ForeignKey("entities.id"))
    to_claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id"))
    to_entity_id: Mapped[str | None] = mapped_column(ForeignKey("entities.id"))
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)


class SourceEntityLink(Base):
    __tablename__ = "source_entity_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), nullable=False, index=True)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)

    source: Mapped["Source"] = relationship()
    entity: Mapped["Entity"] = relationship(back_populates="source_links")


class SourceSuggestion(Base):
    __tablename__ = "source_suggestions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    suggestion_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str | None] = mapped_column(String(64), index=True)
    target_label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reason: Mapped[str] = mapped_column(Text, default="")
    evidence_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped["Source"] = relationship(back_populates="suggestions")


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    page_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    content_md: Mapped[str] = mapped_column(Text, default="")
    content_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    content_html: Mapped[str | None] = mapped_column(Text)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_composed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_reviewed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), index=True)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    parent_page_id: Mapped[str | None] = mapped_column(ForeignKey("pages.id"))
    key_facts: Mapped[list[str]] = mapped_column(JSON, default=list)
    related_page_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    related_entity_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    collection_id: Mapped[str | None] = mapped_column(ForeignKey("collections.id"), index=True)

    versions: Mapped[list["PageVersion"]] = relationship(back_populates="page", cascade="all, delete-orphan")
    claim_links: Mapped[list["PageClaimLink"]] = relationship(back_populates="page", cascade="all, delete-orphan")
    source_links: Mapped[list["PageSourceLink"]] = relationship(back_populates="page", cascade="all, delete-orphan")
    entity_links: Mapped[list["PageEntityLink"]] = relationship(back_populates="page", cascade="all, delete-orphan")
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(back_populates="page", cascade="all, delete-orphan")
    glossary_terms: Mapped[list["GlossaryTerm"]] = relationship(back_populates="page", cascade="all, delete-orphan")
    collection: Mapped["Collection | None"] = relationship(back_populates="pages")


class Diagram(Base):
    __tablename__ = "diagrams"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, default="")
    notation: Mapped[str] = mapped_column(String(32), nullable=False, default="bpm")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="draft")
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    collection_id: Mapped[str | None] = mapped_column(ForeignKey("collections.id"), index=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    drawio_xml: Mapped[str] = mapped_column(Text, default="")
    spec_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_page_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    actor_lanes: Mapped[list[str]] = mapped_column(JSON, default=list)
    entry_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    exit_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    related_diagram_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    published_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), index=True)

    versions: Mapped[list["DiagramVersion"]] = relationship(back_populates="diagram", cascade="all, delete-orphan")
    collection: Mapped["Collection | None"] = relationship(back_populates="diagrams")


class DiagramVersion(Base):
    __tablename__ = "diagram_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    diagram_id: Mapped[str] = mapped_column(ForeignKey("diagrams.id"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    drawio_xml: Mapped[str] = mapped_column(Text, default="")
    spec_json: Mapped[dict] = mapped_column(JSON, default=dict)
    change_summary: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_by_agent_or_user: Mapped[str] = mapped_column(String(128), nullable=False)

    diagram: Mapped["Diagram"] = relationship(back_populates="versions")


class PageVersion(Base):
    __tablename__ = "page_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_agent_or_user: Mapped[str] = mapped_column(String(128), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)

    page: Mapped["Page"] = relationship(back_populates="versions")


class PageClaimLink(Base):
    __tablename__ = "page_claim_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), nullable=False, index=True)
    section_key: Mapped[str] = mapped_column(String(128), nullable=False)
    citation_style: Mapped[str] = mapped_column(String(32), nullable=False)

    page: Mapped["Page"] = relationship(back_populates="claim_links")
    claim: Mapped["Claim"] = relationship(back_populates="page_links")


class PageEntityLink(Base):
    __tablename__ = "page_entity_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False, default="mentions")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)

    page: Mapped["Page"] = relationship(back_populates="entity_links")
    entity: Mapped["Entity"] = relationship(back_populates="page_links")


class PageLink(Base):
    __tablename__ = "page_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    from_page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), nullable=False, index=True)
    to_page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    auto_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PageSourceLink(Base):
    __tablename__ = "page_source_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)

    page: Mapped["Page"] = relationship(back_populates="source_links")
    source: Mapped["Source"] = relationship(back_populates="page_links")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), index=True)
    page_id: Mapped[str | None] = mapped_column(ForeignKey("pages.id"), index=True)
    event_date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    sort_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    precision: Mapped[str] = mapped_column(String(32), nullable=False, default="day")
    entity_ids: Mapped[list[str]] = mapped_column(JSON, default=list)

    page: Mapped["Page"] = relationship(back_populates="timeline_events")


class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), index=True)
    page_id: Mapped[str | None] = mapped_column(ForeignKey("pages.id"), index=True)
    term: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_term: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)

    page: Mapped["Page"] = relationship(back_populates="glossary_terms")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    finished_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    input_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    output_ref: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    logs_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    steps_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actor: Mapped[str] = mapped_column(String(128), nullable=False, default="System")
    retry_of_job_id: Mapped[str | None] = mapped_column(String(64), index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    heartbeat_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    object_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="reader")
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"), index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    collection_memberships: Mapped[list["CollectionMembership"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    department: Mapped["Department | None"] = relationship(back_populates="users")
    notes: Mapped[list["Note"]] = relationship(back_populates="owner")


class CollectionMembership(Base):
    __tablename__ = "collection_memberships"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    collection_id: Mapped[str] = mapped_column(ForeignKey("collections.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="viewer", index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    collection: Mapped["Collection"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="collection_memberships")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="sessions")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    response_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class ReviewItem(Base):
    __tablename__ = "review_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), nullable=False, index=True)
    page_title: Mapped[str] = mapped_column(String(255), nullable=False)
    page_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    page_status: Mapped[str] = mapped_column(String(32), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    old_content_md: Mapped[str] = mapped_column(Text, default="")
    new_content_md: Mapped[str] = mapped_column(Text, default="")
    change_summary: Mapped[str] = mapped_column(String(255), default="")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(128))
    previous_version: Mapped[int | None] = mapped_column(Integer)
    source_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_snippets: Mapped[list[dict]] = mapped_column(JSON, default=list)

    issues: Mapped[list["ReviewIssue"]] = relationship(back_populates="review_item", cascade="all, delete-orphan")


class ReviewIssue(Base):
    __tablename__ = "review_issues"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    review_item_id: Mapped[str] = mapped_column(ForeignKey("review_items.id"), nullable=False, index=True)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    source_chunk_id: Mapped[str | None] = mapped_column(ForeignKey("source_chunks.id"))
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id"))

    review_item: Mapped["ReviewItem"] = relationship(back_populates="issues")


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    review_item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class SavedView(Base):
    __tablename__ = "saved_views"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    view_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    filters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    run_name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed", index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    case_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    quality_gates_json: Mapped[dict] = mapped_column(JSON, default=dict)
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    report_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class RuntimeConfig(Base):
    __tablename__ = "runtime_config"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    answer_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    answer_model: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    answer_api_key: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    answer_base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    answer_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    ingest_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    ingest_model: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    ingest_api_key: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    ingest_base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    ingest_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    embedding_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    embedding_api_key: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    embedding_base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    ai_task_profiles: Mapped[dict] = mapped_column(JSON, default=dict)
    chunk_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="structured")
    chunk_size_words: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    chunk_overlap_words: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    retrieval_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    hybrid_semantic_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.35)
    search_result_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    graph_node_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=250)
    lint_page_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    auto_review_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.76)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
