from pydantic import BaseModel


class TimeSeriesPointOut(BaseModel):
    date: str
    value: int
    label: str | None = None


class ActivityItemOut(BaseModel):
    id: str
    type: str
    description: str
    entityId: str | None = None
    entityTitle: str | None = None
    timestamp: str
    user: str | None = None


class JobStepOut(BaseModel):
    name: str
    status: str
    progress: int | None = None
    details: dict = {}
    updatedAt: str | None = None


class JobOut(BaseModel):
    id: str
    jobType: str
    status: str
    startedAt: str
    finishedAt: str | None = None
    inputRef: str
    outputRef: str | None = None
    errorMessage: str | None = None
    logsJson: list[str]
    stepsJson: list[JobStepOut] = []
    progressPercent: int = 0
    actor: str = "System"
    retryOfJobId: str | None = None
    attempt: int = 1
    maxAttempts: int = 3
    heartbeatAt: str | None = None
    cancelRequested: bool = False


class DashboardStatsOut(BaseModel):
    totalSources: int
    totalPages: int
    publishedPages: int
    draftPages: int
    inReviewPages: int
    stalePages: int
    unverifiedClaims: int
    reviewQueueCount: int
    lastSyncTime: str
    failedJobsCount: int
    totalChunks: int
    totalEntities: int
    sourceTypeBreakdown: dict[str, int]
    pageStatusBreakdown: dict[str, int]
    pagesPublishedOverTime: list[TimeSeriesPointOut]
    recentActivity: list[ActivityItemOut]
    failedJobs: list[JobOut]
