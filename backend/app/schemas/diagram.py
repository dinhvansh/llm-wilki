from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class DiagramOut(BaseModel):
    id: str
    slug: str
    title: str
    objective: str
    notation: str
    status: str
    owner: str
    collectionId: str | None = None
    currentVersion: int
    flowDocument: dict
    sourcePageIds: list[str]
    sourceIds: list[str]
    actorLanes: list[str]
    entryPoints: list[str]
    exitPoints: list[str]
    relatedDiagramIds: list[str]
    relatedDiagrams: list[dict] = []
    linkedPages: list[dict] = []
    linkedSources: list[dict] = []
    createdAt: str
    updatedAt: str
    publishedAt: str | None = None


class DiagramVersionOut(BaseModel):
    id: str
    diagramId: str
    versionNo: int
    flowDocument: dict
    changeSummary: str
    createdAt: str
    createdByAgentOrUser: str


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int
    page: int
    pageSize: int
    hasMore: bool
