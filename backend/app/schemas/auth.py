from __future__ import annotations

from pydantic import BaseModel


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    departmentId: str | None = None
    departmentName: str | None = None
    permissions: list[str] = []
    scopeMode: str = "all"
    accessibleCollectionIds: list[str] = []
    collectionMemberships: list[dict] = []


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut
