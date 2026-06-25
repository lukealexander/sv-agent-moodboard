"""Pluggable providers for the moodboard agent.

Each provider has a real implementation (Anthropic / Replicate / S3) and a
deterministic stub. The factories below choose the stub whenever the relevant
credential is absent, so the whole service runs end-to-end with no external
configuration — the same hermetic philosophy as ``LOCAL_DEV``.
"""

from functools import lru_cache

from app.config import settings
from app.providers.images import ImageProvider, ReplicateImages, StubImages
from app.providers.llm import (
    AnthropicLLM,
    LLMProvider,
    MoodboardComposition,
    StubLLM,
)
from app.providers.storage import LocalStorage, S3Storage, Storage

__all__ = [
    "ImageProvider",
    "LLMProvider",
    "Storage",
    "MoodboardComposition",
    "get_llm",
    "get_images",
    "get_storage",
]


@lru_cache(maxsize=1)
def get_llm() -> LLMProvider:
    if settings.llm_stubbed:
        return StubLLM()
    return AnthropicLLM(api_key=settings.anthropic_api_key, model=settings.anthropic_model)


@lru_cache(maxsize=1)
def get_images() -> ImageProvider:
    if settings.images_stubbed:
        return StubImages()
    return ReplicateImages(api_token=settings.replicate_api_token, model=settings.replicate_model)


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    if settings.storage_uses_s3:
        return S3Storage(bucket=settings.s3_bucket, prefix=settings.s3_prefix)
    return LocalStorage(root=settings.storage_dir)
