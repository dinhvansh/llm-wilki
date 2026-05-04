from __future__ import annotations

import json
from typing import Iterable

import httpx
from anthropic import Anthropic
from openai import OpenAI

from app.core.runtime_config import LLMProfile


class LLMClient:
    @staticmethod
    def is_enabled(profile: LLMProfile) -> bool:
        return profile.provider != "none" and bool(profile.model)

    def complete(self, profile: LLMProfile, system_prompt: str, user_prompt: str) -> str | None:
        if not self.is_enabled(profile):
            return None

        try:
            if profile.provider == "openai":
                client = OpenAI(api_key=profile.api_key, timeout=profile.timeout_seconds)
                response = client.chat.completions.create(
                    model=profile.model,
                    temperature=0.1,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return response.choices[0].message.content or None

            if profile.provider == "anthropic":
                client = Anthropic(api_key=profile.api_key, timeout=profile.timeout_seconds)
                response = client.messages.create(
                    model=profile.model,
                    max_tokens=1200,
                    temperature=0.1,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
                return "\n".join(parts).strip() or None

            if profile.provider == "openai_compatible":
                headers = {"Content-Type": "application/json"}
                if profile.api_key:
                    headers["Authorization"] = f"Bearer {profile.api_key}"
                with httpx.Client(timeout=profile.timeout_seconds) as client:
                    response = client.post(
                        f"{profile.base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json={
                            "model": profile.model,
                            "temperature": 0.1,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    return payload["choices"][0]["message"]["content"]

            if profile.provider == "ollama":
                with httpx.Client(timeout=profile.timeout_seconds) as client:
                    response = client.post(
                        f"{profile.base_url.rstrip('/')}/api/chat",
                        json={
                            "model": profile.model,
                            "stream": False,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    return payload.get("message", {}).get("content")
        except Exception:
            return None

        return None


llm_client = LLMClient()
