"""Song.link (Odesli) API client.

Takes a song URL (from Last.fm, Spotify, etc.) or an artist + title
query and returns links to the same song on other streaming platforms.

API docs: https://odesli.co/
Endpoint: https://api.song.link/v1-alpha.1/links
"""

import httpx
from typing import Optional
from urllib.parse import quote, urlparse
from lyre.logger import logger


# Domains the song.link API can actually resolve.
_SUPPORTED_DOMAINS = {
    "open.spotify.com",
    "spotify.com",
    "music.apple.com",
    "itunes.apple.com",
    "youtube.com",
    "www.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "tidal.com",
    "listen.tidal.com",
    "music.amazon.com",
    "amazon.com",
    "deezer.com",
    "www.deezer.com",
    "soundcloud.com",
    "m.soundcloud.com",
    "pandora.com",
    "www.pandora.com",
    "audiomack.com",
    "www.audiomack.com",
    "audius.co",
    "www.audius.co",
}


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

    @staticmethod
    def _is_supported_url(url: str) -> bool:
        """Return True if the URL belongs to a streaming platform that
        the song.link API can resolve."""
        try:
            host = urlparse(url).hostname or ""
            host = host.lower().removeprefix("www.")
            return any(host == d or host == d.removeprefix("www.") for d in _SUPPORTED_DOMAINS)
        except Exception:
            return False

    async def get_links(
        self,
        song_url: str,
        *,
        artist: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[dict[str, str]]:
        """Fetch cross-platform links for a given song URL.

        Args:
            song_url: A URL to a song on any supported streaming platform.
            artist:   Fallback artist name (used to build a song.link
                      search URL when the URL is unsupported).
            title:    Fallback track title (same purpose as *artist*).

        Returns:
            A dict mapping platform name -> URL, or None if lookup fails.
        """
        if not song_url:
            return self._search_fallback(artist, title)

        # Skip URLs that the API cannot resolve (e.g. Last.fm)
        if not self._is_supported_url(song_url):
            logger.debug(
                f"Skipping song.link lookup — unsupported URL domain: {song_url}"
            )
            return self._search_fallback(artist, title)

        try:
            response = await self.client.get(
                self.BASE_URL,
                params={"url": song_url},
            )

            if response.status_code != 200:
                logger.debug(f"song.link returned {response.status_code} for {song_url}")
                return self._search_fallback(artist, title)

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
                return result

            return self._search_fallback(artist, title)

        except Exception as e:
            logger.warning(f"song.link lookup failed: {e}")
            return self._search_fallback(artist, title)

    @staticmethod
    def _search_fallback(
        artist: Optional[str] = None, title: Optional[str] = None
    ) -> Optional[dict[str, str]]:
        """Build a song.link search-page URL from artist + title.

        This doesn't hit the API — it just gives the user a clickable
        link to the song.link website search for the track.
        """
        if not artist or not title:
            return None
        query = f"{artist} {title}"
        search_url = f"https://song.link/s/{quote(query)}"
        logger.debug(f"Using song.link search fallback: {search_url}")
        return {"song.link": search_url}

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
