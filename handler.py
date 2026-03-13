"""
YouTube Search Tool Handler — Two-tier strategy using YouTube Data API v3 with fallback scraper.

Primary: YouTube Data API v3 (requires free API key, highly reliable)
Fallback: youtube-search-python scraper (no auth, graceful degradation)

Returns normalized video metadata optimized for card rendering.
"""

import logging
import html
import re
from typing import Dict, List, Any
import requests
from youtubesearchpython import VideosSearch

logger = logging.getLogger(__name__)

# Region code mapping: country names → ISO alpha-2 codes
REGION_CODES = {
    "united states": "US",
    "usa": "US",
    "uk": "GB",
    "united kingdom": "GB",
    "canada": "CA",
    "australia": "AU",
    "india": "IN",
    "japan": "JP",
    "south korea": "KR",
    "france": "FR",
    "germany": "DE",
    "mexico": "MX",
    "brazil": "BR",
    "russia": "RU",
    "china": "CN",
    "italy": "IT",
    "spain": "ES",
    "netherlands": "NL",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "poland": "PL",
    "singapore": "SG",
    "hong kong": "HK",
    "thailand": "TH",
    "vietnam": "VN",
    "indonesia": "ID",
    "philippines": "PH",
    "malaysia": "MY",
    "south africa": "ZA",
    "egypt": "EG",
    "turkey": "TR",
    "united arab emirates": "AE",
    "saudi arabia": "SA",
    "israel": "IL",
    "new zealand": "NZ",
    "ireland": "IE",
    "austria": "AT",
    "switzerland": "CH",
    "belgium": "BE",
    "greece": "GR",
    "argentina": "AR",
    "chile": "CL",
    "colombia": "CO",
    "peru": "PE",
}


def execute(topic: str, params: dict, config: dict = None, telemetry: dict = None) -> dict:
    """
    Execute a YouTube search or fetch trending videos.

    Two-tier strategy: API first (if key available), fallback to scraper.

    Args:
        topic: Conversation topic (passed by framework)
        params: {
            "query": str (optional, empty = trending),
            "result_count": int (optional, default 1, clamped to 1-3)
        }
        config: Tool configuration with optional YOUTUBE_API_KEY
        telemetry: Telemetry data (used for region resolution)

    Returns:
        {
            "videos": [
                {
                    "id": "...",
                    "title": "...",
                    "channel": "...",
                    "thumbnail_url": "...",
                    "duration_fmt": "3:32" or "LIVE",
                    "view_count_fmt": "1.4B views",
                    "url": "..."
                }
            ],
            "mode": "search" or "trending" or "error"
        }
    """
    query = params.get("query", "").strip()
    result_count = int(params.get("result_count", 1))
    result_count = max(1, min(3, result_count))

    region = _resolve_region_code(telemetry or {})
    api_key = (config or {}).get("YOUTUBE_API_KEY", "").strip()

    try:
        if not query:
            # Trending videos
            if api_key:
                logger.info("[YOUTUBE] Attempting trending via API")
                videos = YouTubeAPIClient(api_key).trending(result_count, region)
                if videos:
                    return {"videos": videos, "mode": "trending"}
                logger.warning("[YOUTUBE] API trending failed, falling back to scraper")

            logger.info("[YOUTUBE] Using scraper for trending")
            videos = YouTubeScraper().trending(result_count)
            return {"videos": videos, "mode": "trending"}
        else:
            # Search videos
            if api_key:
                logger.info(f"[YOUTUBE] Searching '{query}' via API")
                videos = YouTubeAPIClient(api_key).search(query, result_count, region)
                if videos:
                    return {"videos": videos, "mode": "search"}
                logger.warning(f"[YOUTUBE] API search failed for '{query}', falling back to scraper")

            logger.info(f"[YOUTUBE] Searching '{query}' via scraper")
            videos = YouTubeScraper().search(query, result_count)
            return {"videos": videos, "mode": "search"}

    except Exception as e:
        logger.error(f"[YOUTUBE] Unexpected error: {e}")
        return {"videos": [], "mode": "error", "error": str(e)}


def _resolve_region_code(telemetry: dict) -> str:
    """
    Resolve user region from telemetry to ISO alpha-2 country code.

    Args:
        telemetry: Telemetry dict (may include user location/region)

    Returns:
        ISO alpha-2 code (e.g., 'US'), defaults to 'US'
    """
    region = telemetry.get("region", "").lower()
    return REGION_CODES.get(region, "US")


class YouTubeAPIClient:
    """YouTube Data API v3 client for reliable search and trending."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.timeout = 8

    def search(self, query: str, limit: int, region: str = "US") -> List[Dict[str, Any]]:
        """
        Search YouTube using search.list + batch videos.list for stats.

        Args:
            query: Search query
            limit: Number of results (1-3)
            region: ISO alpha-2 region code

        Returns:
            List of normalized video dicts
        """
        try:
            # Step 1: search.list → get video IDs
            search_params = {
                "key": self.api_key,
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": limit,
                "regionCode": region,
                "order": "relevance",
            }
            search_resp = requests.get(
                f"{self.base_url}/search",
                params=search_params,
                timeout=self.timeout,
            )
            search_resp.raise_for_status()
            search_data = search_resp.json()

            video_ids = [item["id"]["videoId"] for item in search_data.get("items", [])]
            if not video_ids:
                logger.warning(f"[YOUTUBE API] No results for '{query}'")
                return []

            # Step 2: videos.list → get stats (duration, view count)
            videos_params = {
                "key": self.api_key,
                "part": "contentDetails,statistics,snippet",
                "id": ",".join(video_ids),
            }
            videos_resp = requests.get(
                f"{self.base_url}/videos",
                params=videos_params,
                timeout=self.timeout,
            )
            videos_resp.raise_for_status()
            videos_data = videos_resp.json()

            videos = []
            for item in videos_data.get("items", []):
                video = self._format_api_video(item)
                if video:
                    videos.append(video)

            return videos[:limit]

        except requests.RequestException as e:
            logger.error(f"[YOUTUBE API] Search request failed for '{query}': {e}")
            return []
        except Exception as e:
            logger.error(f"[YOUTUBE API] Search parsing failed for '{query}': {e}")
            return []

    def trending(self, limit: int, region: str = "US") -> List[Dict[str, Any]]:
        """
        Fetch trending videos using videos.list?chart=mostPopular.

        Args:
            limit: Number of results (1-3)
            region: ISO alpha-2 region code

        Returns:
            List of normalized video dicts
        """
        try:
            params = {
                "key": self.api_key,
                "part": "contentDetails,statistics,snippet",
                "chart": "mostPopular",
                "regionCode": region,
                "maxResults": limit,
            }
            resp = requests.get(
                f"{self.base_url}/videos",
                params=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            videos = []
            for item in data.get("items", []):
                video = self._format_api_video(item)
                if video:
                    videos.append(video)

            return videos[:limit]

        except requests.RequestException as e:
            logger.error(f"[YOUTUBE API] Trending request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"[YOUTUBE API] Trending parsing failed: {e}")
            return []

    def _format_api_video(self, item: dict) -> Dict[str, Any]:
        """Format a YouTube API v3 video item to normalized format."""
        snippet = item.get("snippet", {})
        video_id = item.get("id", "")
        title = snippet.get("title", "Unknown Title")
        channel = snippet.get("channelTitle", "Unknown Channel")

        # Decode HTML entities in title
        title = html.unescape(title)

        # Duration: ISO 8601 (PT3M32S) → seconds
        duration_str = item.get("contentDetails", {}).get("duration", "PT0S")
        duration_seconds = self._parse_iso8601_duration(duration_str)
        duration_fmt = _format_duration(duration_seconds)

        # View count
        view_count = int(item.get("statistics", {}).get("viewCount", 0))
        view_count_fmt = _format_view_count(view_count)

        # Thumbnail
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
            or f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        )

        url = f"https://www.youtube.com/watch?v={video_id}"

        return {
            "id": video_id,
            "title": title,
            "channel": channel,
            "thumbnail_url": thumbnail_url,
            "duration_fmt": duration_fmt,
            "view_count_fmt": view_count_fmt,
            "url": url,
        }

    @staticmethod
    def _parse_iso8601_duration(duration_str: str) -> int:
        """Parse ISO 8601 duration (PT3M32S) to seconds."""
        match = re.match(
            r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
            duration_str,
        )
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds


class YouTubeScraper:
    """Fallback scraper using youtube-search-python (no auth required)."""

    def search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search YouTube using youtube-search-python."""
        try:
            results = VideosSearch(query, limit=limit).result().get("result", [])
            videos = []
            for item in results:
                video = self._format_scraper_video(item)
                if video:
                    videos.append(video)
            if len(videos) < limit:
                logger.warning(
                    f"[YOUTUBE SCRAPER] Requested {limit} results for '{query}' but only got {len(videos)}"
                )
            return videos[:limit]
        except Exception as e:
            logger.error(f"[YOUTUBE SCRAPER] Search failed for '{query}': {e}")
            return []

    def trending(self, limit: int) -> List[Dict[str, Any]]:
        """
        Trending via scraper: best-effort using popular search.

        youtube-search-python doesn't expose trending directly,
        so we approximate with a broad search for popular videos.
        """
        try:
            results = VideosSearch("trending now", limit=limit).result().get("result", [])
            videos = []
            for item in results:
                video = self._format_scraper_video(item)
                if video:
                    videos.append(video)
            if len(videos) < limit:
                logger.warning(
                    f"[YOUTUBE SCRAPER] Requested {limit} trending results but only got {len(videos)}"
                )
            return videos[:limit]
        except Exception as e:
            logger.error(f"[YOUTUBE SCRAPER] Trending failed: {e}")
            return []

    @staticmethod
    def _format_scraper_video(item: dict) -> Dict[str, Any]:
        """Format a youtube-search-python result to normalized format."""
        video_id = item.get("id", "")
        title = item.get("title", "Unknown Title")
        channel = item.get("channel", {}).get("name", "Unknown Channel")

        # Decode HTML entities
        title = html.unescape(title)

        # Duration: scraper returns string like "3:32" or "1:23:45"
        duration_str = item.get("duration", "0:00")
        duration_fmt = _format_duration_from_string(duration_str)

        # View count: scraper returns string like "1.2M views"
        view_count_str = item.get("views", "0")
        view_count_fmt = _format_view_count_from_string(view_count_str)

        # Thumbnail
        thumbnail_url = item.get("thumbnails", [{}])[0].get("url")
        if not thumbnail_url:
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"

        url = f"https://www.youtube.com/watch?v={video_id}"

        return {
            "id": video_id,
            "title": title,
            "channel": channel,
            "thumbnail_url": thumbnail_url,
            "duration_fmt": duration_fmt,
            "view_count_fmt": view_count_fmt,
            "url": url,
        }


def _format_duration(seconds: int) -> str:
    """
    Format duration in seconds to "mm:ss" or "h:mm:ss" or "LIVE".

    Args:
        seconds: Duration in seconds (0 for live streams)

    Returns:
        Formatted duration string
    """
    if seconds == 0:
        return "LIVE"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def _format_duration_from_string(duration_str: str) -> str:
    """Parse pre-formatted duration string and return as-is or clean it."""
    if not duration_str or duration_str == "0:00":
        return "LIVE"
    return duration_str


def _format_view_count(count: int) -> str:
    """
    Format view count to human-readable format (e.g., "1.2B views").

    Args:
        count: View count as integer

    Returns:
        Formatted view count string
    """
    if not count:
        return "0 views"

    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B views"
    elif count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M views"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K views"
    else:
        return f"{count} views"


def _format_view_count_from_string(view_str: str) -> str:
    """Extract and normalize view count from string (e.g., '1.2M views')."""
    if not view_str:
        return "0 views"
    # Return as-is if it looks reasonable (contains number + unit)
    if any(unit in view_str.lower() for unit in ["views", "k", "m", "b"]):
        return view_str
    return "0 views"
