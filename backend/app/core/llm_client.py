from __future__ import annotations

import base64
import json
import re
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

            if profile.provider == "gemini":
                if not profile.api_key:
                    return None
                model = re.sub(r"^models/", "", profile.model.strip())
                with httpx.Client(timeout=profile.timeout_seconds) as client:
                    response = client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                        params={"key": profile.api_key},
                        json={
                            "systemInstruction": {"parts": [{"text": system_prompt}]},
                            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                            "generationConfig": {"temperature": 0.1},
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    return "\n".join(str(part.get("text") or "") for part in parts if isinstance(part, dict)).strip() or None

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

    def complete_with_image(
        self,
        profile: LLMProfile,
        system_prompt: str,
        user_prompt: str,
        *,
        image_bytes: bytes,
        mime_type: str,
    ) -> str | None:
        if not self.is_enabled(profile) or not image_bytes or not mime_type:
            return None

        try:
            if profile.provider == "openai":
                client = OpenAI(api_key=profile.api_key, timeout=profile.timeout_seconds)
                data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
                response = client.chat.completions.create(
                    model=profile.model,
                    temperature=0.1,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_prompt},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        },
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
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_prompt},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": mime_type,
                                        "data": base64.b64encode(image_bytes).decode("ascii"),
                                    },
                                },
                            ],
                        }
                    ],
                )
                parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
                return "\n".join(parts).strip() or None

            if profile.provider == "openai_compatible":
                headers = {"Content-Type": "application/json"}
                if profile.api_key:
                    headers["Authorization"] = f"Bearer {profile.api_key}"
                data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
                with httpx.Client(timeout=profile.timeout_seconds) as client:
                    response = client.post(
                        f"{profile.base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json={
                            "model": profile.model,
                            "temperature": 0.1,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": user_prompt},
                                        {"type": "image_url", "image_url": {"url": data_url}},
                                    ],
                                },
                            ],
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    return payload["choices"][0]["message"]["content"]
        except Exception:
            return None

        return None


llm_client = LLMClient()
