"""Image generation backends.

``ReplicateImages`` renders via Replicate (default model ``black-forest-labs/flux-dev``,
configurable) and downloads the result bytes. ``StubImages`` produces a deterministic
SVG tile so the pipeline runs end-to-end with no token — same shape, no network.
"""

import abc
import hashlib


class ImageProvider(abc.ABC):
    @abc.abstractmethod
    async def render(self, prompt: str, index: int) -> tuple[bytes, str]:
        """Render one tile. Returns ``(data, content_type)``."""


def _hue(seed: str, salt: str) -> int:
    h = hashlib.sha256(f"{seed}|{salt}".encode()).hexdigest()
    return int(h[:6], 16) % 360


class StubImages(ImageProvider):
    """Deterministic SVG tiles — a stand-in for real renders during local dev/tests."""

    async def render(self, prompt: str, index: int) -> tuple[bytes, str]:
        h1 = _hue(prompt, "a")
        h2 = (h1 + 40 + _hue(prompt, "b") % 60) % 360
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800" role="img" aria-label="{_escape(prompt)}">
  <defs>
    <linearGradient id="g{index}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="hsl({h1} 55% 28%)"/>
      <stop offset="1" stop-color="hsl({h2} 60% 42%)"/>
    </linearGradient>
    <radialGradient id="r{index}" cx="0.7" cy="0.3" r="0.8">
      <stop offset="0" stop-color="hsl({h2} 70% 60%)" stop-opacity="0.55"/>
      <stop offset="1" stop-color="hsl({h1} 55% 28%)" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="800" height="800" fill="url(#g{index})"/>
  <rect width="800" height="800" fill="url(#r{index})"/>
  <circle cx="{200 + (index * 90) % 400}" cy="{560 - (index * 70) % 300}" r="120" fill="hsl({h2} 70% 70%)" opacity="0.14"/>
</svg>"""
        return svg.encode("utf-8"), "image/svg+xml"


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


class ReplicateImages(ImageProvider):
    def __init__(self, api_token: str, model: str) -> None:
        self.api_token = api_token
        self.model = model

    async def render(self, prompt: str, index: int) -> tuple[bytes, str]:
        import httpx  # already a dependency
        import replicate  # lazy: only needed when a token is configured

        client = replicate.Client(api_token=self.api_token)
        output = await client.async_run(
            self.model,
            input={"prompt": prompt, "aspect_ratio": "1:1", "output_format": "webp"},
        )
        item = output[0] if isinstance(output, (list, tuple)) else output
        # Newer replicate SDKs return FileOutput objects (with .url); older ones URL strings.
        url = getattr(item, "url", None) or str(item)
        async with httpx.AsyncClient(timeout=120.0) as http:
            resp = await http.get(url)
            resp.raise_for_status()
        return resp.content, resp.headers.get("content-type", "image/webp")
