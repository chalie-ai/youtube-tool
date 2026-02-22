"""
YouTube Tool Runner — Decodes IPC payload and generates HTML cards.

Renders two card formats based on result_count:
1. Single video: Full YouTube embed iframe with metadata
2. Three videos: Thumbnail grid with clickable links
"""

import sys
import json
import base64
from handler import execute


# YouTube logo SVG (simplified play button icon)
YOUTUBE_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="#FF0000">
  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
</svg>"""

# Play button overlay SVG
PLAY_BUTTON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="60" height="60" fill="white">
  <circle cx="50" cy="50" r="50" fill="rgba(0,0,0,0.4)"/>
  <polygon points="35,25 35,75 75,50" fill="white"/>
</svg>"""


def main():
    """Decode IPC payload and execute tool, then render appropriate HTML card."""
    try:
        payload = json.loads(base64.b64decode(sys.argv[1]))
    except (IndexError, json.JSONDecodeError, ValueError) as e:
        print(json.dumps({"error": f"Invalid payload: {e}"}))
        return

    params = payload.get("params", {})
    settings = payload.get("settings", {})
    telemetry = payload.get("telemetry", {})

    result = execute(topic="", params=params, config=settings, telemetry=telemetry)

    videos = result.get("videos", [])
    mode = result.get("mode", "unknown")

    if not videos:
        error_msg = result.get("error", "No videos found")
        print(json.dumps({
            "text": f"Unable to fetch videos: {error_msg}",
            "html": f"<p>Error: {error_msg}</p>",
            "title": "YouTube"
        }))
        return

    result_count = len(videos)

    if result_count == 1:
        # Single video embed card
        html = _render_single_video_card(videos[0])
        text = _build_single_video_text(videos[0])
    else:
        # Three-video grid card
        html = _render_three_video_grid(videos)
        text = _build_multi_video_text(videos)

    output = {
        "text": text,
        "html": html,
        "title": "YouTube"
    }

    print(json.dumps(output))


def _render_single_video_card(video: dict) -> str:
    """
    Render single-video card: thumbnail with play button, click-to-play iframe.

    Args:
        video: Video dict with {id, title, channel, thumbnail_url, duration_fmt}

    Returns:
        HTML string
    """
    video_id = video.get("id", "")
    channel = video.get("channel", "")
    duration = video.get("duration_fmt", "")
    thumbnail_url = video.get("thumbnail_url") or f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    embed_url = f"https://www.youtube-nocookie.com/embed/{video_id}?autoplay=1"

    channel_badge = f'<span style="position:absolute;bottom:10px;left:10px;color:rgba(255,255,255,0.8);font-size:11px;font-family:system-ui,sans-serif;text-shadow:0 1px 4px rgba(0,0,0,0.8);">{channel}</span>' if channel else ""
    duration_badge = f'<span style="position:absolute;bottom:10px;right:10px;background:rgba(0,0,0,0.82);color:#fff;padding:2px 6px;border-radius:3px;font-size:11px;font-weight:700;font-family:system-ui,sans-serif;letter-spacing:0.02em;">{duration}</span>' if duration else ""

    return f"""<div style="position:relative;width:100%;aspect-ratio:16/9;border-radius:10px;overflow:hidden;background:#000;cursor:pointer;">
  <div class="yt-th" style="position:relative;width:100%;height:100%;">
    <img src="{thumbnail_url}" style="width:100%;height:100%;object-fit:cover;display:block;"/>
    <div style="position:absolute;inset:0;background:linear-gradient(transparent 55%,rgba(0,0,0,0.65));pointer-events:none;"></div>
    {channel_badge}
    {duration_badge}
    <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;">
      <div style="width:58px;height:58px;background:rgba(255,0,0,0.92);border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 24px rgba(0,0,0,0.55);">
        <svg viewBox="0 0 24 24" width="24" height="24" fill="white" style="margin-left:3px;"><path d="M8 5v14l11-7z"/></svg>
      </div>
    </div>
  </div>
  <iframe class="yt-fr" style="display:none;width:100%;height:100%;border:none;" src="about:blank" data-src="{embed_url}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
</div>"""


def _render_three_video_grid(videos: list) -> str:
    """
    Render three-video thumbnail grid with clickable cards.

    Args:
        videos: List of 1-3 video dicts

    Returns:
        HTML string
    """
    grid_html = '<div style="display:flex;gap:12px;flex-wrap:wrap;font-family:sans-serif;">'

    for i, video in enumerate(videos[:3]):
        video_id = video.get("id", "")
        title = video.get("title", "Video")
        channel = video.get("channel", "Unknown")
        thumbnail_url = video.get("thumbnail_url", "")
        url = video.get("url", f"https://www.youtube.com/watch?v={video_id}")
        duration = video.get("duration_fmt", "")

        # Build thumbnail card with play button overlay
        card_html = f"""
        <a href="{url}" target="_blank" style="flex:1;min-width:280px;text-decoration:none;color:inherit;">
            <div style="position:relative;width:100%;aspect-ratio:16/9;overflow:hidden;border-radius:8px;background:#000;">
                <img src="{thumbnail_url}" alt="{title}" style="width:100%;height:100%;object-fit:cover;"/>
                <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity 200ms;">
                    {PLAY_BUTTON_SVG}
                </div>
                <span style="position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,0.8);color:white;padding:4px 8px;border-radius:3px;font-size:12px;font-weight:600;">{duration}</span>
            </div>
            <div style="padding:8px 0;">
                <p style="margin:0 0 4px 0;font-size:14px;font-weight:600;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">{title}</p>
                <p style="margin:0;font-size:12px;color:#666;">{channel}</p>
            </div>
        </a>
        """
        grid_html += card_html

    grid_html += "</div>"

    return grid_html


def _build_single_video_text(video: dict) -> str:
    """Build detailed text for single video result."""
    title = video.get("title", "Video")
    channel = video.get("channel", "Unknown")
    view_count = video.get("view_count_fmt", "")
    duration = video.get("duration_fmt", "")
    return f"{title} — by {channel} ({view_count}, {duration})"


def _build_multi_video_text(videos: list) -> str:
    """Build detailed text for multiple video results."""
    lines = [f"Found {len(videos)} videos:"]
    for i, video in enumerate(videos[:3], 1):
        title = video.get("title", "Video")
        channel = video.get("channel", "Unknown")
        view_count = video.get("view_count_fmt", "")
        lines.append(f"{i}. {title} — {channel} ({view_count})")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
