"""Assemble a moodboard into a single self-contained HTML file.

Images are inlined as data URIs so the file is portable and shareable on its own —
it doesn't depend on any asset URL being reachable. The chrome is on-brand
(Supervenient ground/facets), but the moodboard *content* (palette, imagery) is the
user's. ``html.escape`` is applied to every piece of model/user text.
"""

import base64
from html import escape


def _data_uri(content_type: str, data: bytes) -> str:
    return f"data:{content_type};base64,{base64.b64encode(data).decode('ascii')}"


def assemble_html(
    *,
    title: str,
    summary: str,
    notes: list[str],
    palette: list[dict],
    images: list[dict],
) -> str:
    """``palette`` items: {hex, name}. ``images`` items: {data, content_type, alt}."""
    swatches = "\n".join(
        f'<li class="sw"><span class="chip" style="background:{escape(str(s.get("hex", "#000")))}"></span>'
        f'<span class="swmeta"><b>{escape(str(s.get("name", "")))}</b><code>{escape(str(s.get("hex", "")))}</code></span></li>'
        for s in palette
    )
    tiles = "\n".join(
        f'<figure class="tile"><img loading="lazy" alt="{escape(str(img.get("alt", "")))}" '
        f'src="{_data_uri(str(img.get("content_type", "image/png")), img["data"])}"></figure>'
        for img in images
        if img.get("data")
    )
    note_items = "\n".join(f"<li>{escape(n)}</li>" for n in notes if n)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — moodboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lexend:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; margin: 0; }}
  body {{
    font-family: 'Lexend', system-ui, sans-serif;
    color: #fff;
    background:
      radial-gradient(1200px 700px at 75% -10%, rgba(143,217,115,.10), transparent 60%),
      radial-gradient(900px 600px at 10% 110%, rgba(47,182,212,.12), transparent 55%),
      #241036;
    line-height: 1.55;
    padding: clamp(24px, 5vw, 64px);
  }}
  .wrap {{ max-width: 1040px; margin: 0 auto; }}
  header {{ max-width: 60ch; }}
  .kicker {{ font-size: 13px; letter-spacing: .04em; color: #c9bbdd; }}
  h1 {{ font-weight: 500; font-size: clamp(28px, 5vw, 48px); line-height: 1.1; letter-spacing: -.02em; margin: 6px 0 10px; text-wrap: balance; }}
  .summary {{ color: #c9bbdd; font-size: 18px; text-wrap: pretty; }}
  .palette {{ list-style: none; display: flex; flex-wrap: wrap; gap: 14px; margin: 40px 0; padding: 0; }}
  .sw {{ display: flex; align-items: center; gap: 10px; }}
  .chip {{ width: 40px; height: 40px; border-radius: 10px; border: 1px solid rgba(255,255,255,.14); box-shadow: 0 6px 20px rgba(36,16,54,.5); }}
  .swmeta {{ display: flex; flex-direction: column; line-height: 1.25; }}
  .swmeta b {{ font-weight: 500; }}
  .swmeta code {{ font-size: 12px; color: #c9bbdd; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin: 8px 0 40px; }}
  .tile {{ margin: 0; border-radius: 16px; overflow: hidden; aspect-ratio: 1; background: #341852; box-shadow: 0 16px 48px rgba(36,16,54,.55); }}
  .tile img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .notes {{ max-width: 60ch; color: #c9bbdd; padding-left: 1.1em; }}
  .notes li {{ margin: 4px 0; }}
  footer {{ margin-top: 48px; font-size: 13px; color: #9c8fb5; }}
  @media (prefers-reduced-motion: no-preference) {{
    .tile {{ transition: transform .24s cubic-bezier(.2,0,0,1); }}
    .tile:hover {{ transform: translateY(-3px); }}
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <p class="kicker">Moodboard</p>
      <h1>{escape(title)}</h1>
      <p class="summary">{escape(summary)}</p>
    </header>
    {f'<ul class="palette">{swatches}</ul>' if swatches else ''}
    {f'<div class="grid">{tiles}</div>' if tiles else ''}
    {f'<ul class="notes">{note_items}</ul>' if note_items else ''}
    <footer>Generated with Agent Moodboard.</footer>
  </div>
</body>
</html>"""
