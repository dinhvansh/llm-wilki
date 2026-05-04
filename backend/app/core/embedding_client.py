from __future__ import annotations

from math import sqrt

import httpx
from openai import OpenAI

from app.core.runtime_config import LLMProfile


class EmbeddingClient:
    @staticmethod
    def is_enabled(profile: LLMProfile) -> bool:
        return profile.provider != "none" and bool(profile.model)

    def embed_texts(self, profile: LLMProfile, texts: list[str]) -> list[list[float]] | None:
        if not self.is_enabled(profile) or not texts:
            return None

        try:
            if profile.provider == "openai":
                client = OpenAI(api_key=profile.api_key, timeout=profile.timeout_seconds)
                response = client.embeddings.create(model=profile.model, input=texts)
                return [self._normalize(item.embedding) for item in response.data]

            if profile.provider == "openai_compatible":
                headers = {"Content-Type": "application/json"}
                if profile.api_key:
                    headers["Authorization"] = f"Bearer {profile.api_key}"
                with httpx.Client(timeout=profile.timeout_seconds) as client:
                    response = client.post(
                        f"{profile.base_url.rstrip('/')}/embeddings",
                        headers=headers,
                        json={"model": profile.model, "input": texts},
                    )
                    response.raise_for_status()
                    payload = response.json()
                    return [self._normalize(item["embedding"]) for item in payload["data"]]

            if profile.provider == "ollama":
                vectors: list[list[float]] = []
                with httpx.Client(timeout=profile.timeout_seconds) as client:
                    for text in texts:
                        response = client.post(
                            f"{profile.base_url.rstrip('/')}/api/embed",
                            json={"model": profile.model, "input": text},
                        )
                        response.raise_for_status()
                        payload = response.json()
                        embedding = payload.get("embeddings", [[]])[0] if payload.get("embeddings") else payload.get("embedding", [])
                        vectors.append(self._normalize(embedding))
                return vectors
        except Exception:
            return None

        return None

    @staticmethod
    def cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        return max(0.0, min(1.0, sum(l * r for l, r in zip(left, right))))

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        if not vector:
            return []
        norm = sqrt(sum(value * value for value in vector))
        if norm == 0:
            return [0.0 for _ in vector]
        return [float(value / norm) for value in vector]


embedding_client = EmbeddingClient()
