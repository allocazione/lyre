"""Song.link (Odesli) API client.

Takes a song URL (from Last.fm, Spotify, etc.) or an artist + title
query and returns links to the same song on other streaming platforms.

API docs: https://odesli.co/
Endpoint: https://api.song.link/v1-alpha.1/links
"""

import httpx
from typing import Optional
from lyre.logger import logger


# Platforms we care about, in display order
_PLATFORM_LABELS = {
    "spotify": "Spotify",
    "appleMusic": "Apple Music",
    "youtube": "YouTube",
    "youtubeMusic": "YouTube Music",
    "tidal": "Tidal",
    "amazonMusic": "Amazon Music",
    "deezer": "Deezer",
    "soundcloud": "SoundCloud",
}


class SongLinkClient:
    """Client for the song.link / Odesli API."""

    BASE_URL = "https://api.song.link/v1-alpha.1/links"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_links(self, song_url: str) -> Optional[dict[str, str]]:
        """Fetch cross-platform links for a given song URL.

        Args:
            song_url: A URL to a song on any supported platform
                      (Last.fm, Spotify, YouTube, etc.)

        Returns:
            A dict mapping platform name -> URL, or None if lookup fails.
        """
        if not song_url:
            return None

        try:
            response = await self.client.get(
                self.BASE_URL,
                params={"url": song_url},
            )

            if response.status_code != 200:
                logger.debug(f"song.link returned {response.status_code} for {song_url}")
                return None

            data = response.json()
            links_by_platform = data.get("linksByPlatform", {})

            result = {}
            for platform_key, label in _PLATFORM_LABELS.items():
                platform_data = links_by_platform.get(platform_key)
                if platform_data and platform_data.get("url"):
                    result[label] = platform_data["url"]

            # Also grab the universal page URL from song.link itself
            page_url = data.get("pageUrl")
            if page_url:
                result["song.link"] = page_url

            if result:
                logger.debug(f"Found {len(result)} platform links for: {song_url}")
            return result if result else None

        except Exception as e:
            logger.warning(f"song.link lookup failed: {e}")
            return None

    def format_links(self, links: dict[str, str], compact: bool = True) -> str:
        """Format platform links for display in a note or bio.

        Args:
            links: Dict of platform name -> URL from get_links().
            compact: If True, return a single song.link URL. If False,
                     return all individual platform links.
        """
        if not links:
            return ""

        if compact:
            # Prefer the universal song.link page
            if "song.link" in links:
                return links["song.link"]
            # Fall back to the first available platform URL (e.g. Spotify)
            for platform, url in links.items():
                return url
            return ""

        # Full listing (for notes)
        parts = []
        for platform, url in links.items():
            if platform == "song.link":
                continue  # Skip the universal link in full listing
            parts.append(f"{platform}: {url}")

        return "\n".join(parts)

    async def close(self):
        await self.client.aclose()
