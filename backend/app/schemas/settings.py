from pydantic import BaseModel, Field


class AIModelProfilePayload(BaseModel):
    provider: str = "none"
    model: str = ""
    apiKey: str = ""
    baseUrl: str = ""
    timeoutSeconds: int = Field(default=90, ge=5, le=600)


class AITaskProfilesPayload(BaseModel):
    ingest_summary: AIModelProfilePayload = Field(default_factory=AIModelProfilePayload)
    claim_extraction: AIModelProfilePayload = Field(default_factory=AIModelProfilePayload)
    entity_glossary_timeline: AIModelProfilePayload = Field(default_factory=AIModelProfilePayload)
    bpm_generation: AIModelProfilePayload = Field(default_factory=AIModelProfilePayload)
    ask_answer: AIModelProfilePayload = Field(default_factory=AIModelProfilePayload)
    review_assist: AIModelProfilePayload = Field(default_factory=AIModelProfilePayload)
    embeddings: AIModelProfilePayload = Field(default_factory=lambda: AIModelProfilePayload(timeoutSeconds=90))


class SettingsPayload(BaseModel):
    answerProvider: str = "none"
    answerModel: str = ""
    answerApiKey: str = ""
    answerBaseUrl: str = ""
    answerTimeoutSeconds: int = Field(default=90, ge=5, le=600)
    ingestProvider: str = "none"
    ingestModel: str = ""
    ingestApiKey: str = ""
    ingestBaseUrl: str = ""
    ingestTimeoutSeconds: int = Field(default=90, ge=5, le=600)
    embeddingProvider: str = "none"
    embeddingModel: str = ""
    embeddingApiKey: str = ""
    embeddingBaseUrl: str = ""
    aiTaskProfiles: AITaskProfilesPayload = Field(default_factory=AITaskProfilesPayload)
    chunkMode: str = Field(default="structured", pattern="^(structured|window)$")
    chunkSizeWords: int = Field(default=180, ge=50, le=2000)
    chunkOverlapWords: int = Field(default=30, ge=0, le=500)
    retrievalLimit: int = Field(default=4, ge=1, le=20)
    hybridSemanticWeight: float = Field(default=0.35, ge=0.0, le=1.0)
    searchResultLimit: int = Field(default=20, ge=1, le=100)
    graphNodeLimit: int = Field(default=250, ge=25, le=2000)
    lintPageLimit: int = Field(default=500, ge=50, le=5000)
    autoReviewThreshold: float = Field(default=0.76, ge=0.0, le=1.0)


class SettingsResponse(SettingsPayload):
    updatedAt: str


class TestConnectionPayload(BaseModel):
    provider: str = "none"
    model: str = ""
    apiKey: str = ""
    baseUrl: str = ""
    timeoutSeconds: int = Field(default=90, ge=5, le=600)
    purpose: str = "answer"


class TestConnectionResponse(BaseModel):
    success: bool
    provider: str
    model: str
    purpose: str
    message: str
    latencyMs: int | None = None
