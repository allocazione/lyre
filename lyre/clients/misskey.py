import httpx
from typing import Optional
from lyre.config import Config
from lyre.logger import logger


class MisskeyClient:
    """Client for interacting with the Misskey API.

    Handles bio updates (online/offline status) and posting notes
    for currently playing tracks.
    """

    def __init__(self):
        self.instance_url = Config.MISSKEY_INSTANCE_URL.rstrip("/")
        self.token = Config.MISSKEY_TOKEN
        self.client = httpx.AsyncClient(
            base_url=self.instance_url,
            timeout=15.0,
            headers={"Content-Type": "application/json"},
        )
        self._clean_bio: Optional[str] = None
        logger.info(f"Initialized Misskey client for instance: {self.instance_url}")

    async def verify_credentials(self) -> dict:
        """Verify the access token and return account info.
        Used by --debug-acc flag."""
        response = await self.client.post(
            "/api/i",
            json={"i": self.token},
        )
        if response.status_code >= 400:
            logger.error(f"Misskey API error in verify_credentials ({response.status_code}): {response.text}")
        response.raise_for_status()
        data = response.json()
        logger.info(f"Authenticated as: @{data.get('username', 'unknown')}")
        return data

    async def get_profile(self) -> dict:
        """Get the current user profile."""
        response = await self.client.post(
            "/api/i",
            json={"i": self.token},
        )
        if response.status_code >= 400:
            logger.error(f"Misskey API error in get_profile ({response.status_code}): {response.text}")
        response.raise_for_status()
        return response.json()

    async def update_bio(self, bio: str) -> None:
        """Update the user's profile description (bio)."""
        response = await self.client.post(
            "/api/i/update",
            json={
                "i": self.token,
                "description": bio,
            },
        )
        if response.status_code >= 400:
            logger.error(f"Misskey API error in update_bio ({response.status_code}): {response.text}")
        response.raise_for_status()
        logger.info(f"Bio updated.")

    async def _ensure_clean_bio(self) -> None:
        """Fetch and cache the user's real bio once, stripping all bot content."""
        if self._clean_bio is not None:
            return
        profile = await self.get_profile()
        current_bio = profile.get("description", "") or ""
        self._clean_bio = self._clean_bot_lines(current_bio)
        logger.debug(f"Cached clean bio ({len(self._clean_bio)} chars).")

    def _build_bio(self, header: str) -> str:
        """Construct the full bio: header + cached clean user bio."""
        if self._clean_bio:
            return f"{header}\n\n{self._clean_bio}"
        return header

    async def set_online(self, message: str = "Currently running.") -> None:
        """Mark the bot as online in the bio.

        Args:
            message: Status text shown after the [Online] tag.
        """
        await self._ensure_clean_bio()
        new_bio = self._build_bio(f"[Online] {message}")
        await self.update_bio(new_bio)
        logger.info("Status set to Online.")

    async def set_offline(self) -> None:
        """Mark the bot as offline in the bio."""
        await self._ensure_clean_bio()
        new_bio = self._build_bio("[Offline]")
        await self.update_bio(new_bio)
        logger.info("Status set to Offline.")

    async def update_now_playing(self, track_str: str, link: str = "") -> None:
        """Update the bio with the currently playing track.

        Args:
            track_str: Display string for the track (e.g. "Artist - Title").
            link: Optional URL (song.link, Spotify, etc.) shown below the header.
        """
        await self._ensure_clean_bio()
        header = f"[Online] Now listening: {track_str}"
        if link:
            header += f"\n{link}"
        new_bio = self._build_bio(header)
        await self.update_bio(new_bio)

    async def post_note(self, text: str, visibility: str = "home") -> dict:
        """Post a note (status update) to Misskey.

        Args:
            text: The note content.
            visibility: One of 'public', 'home', 'followers', 'specified'.
        """
        response = await self.client.post(
            "/api/notes/create",
            json={
                "i": self.token,
                "text": text,
                "visibility": visibility,
            },
        )
        if response.status_code >= 400:
            logger.error(f"Misskey API error in post_note ({response.status_code}): {response.text}")
        response.raise_for_status()
        data = response.json()
        note_id = data.get("createdNote", {}).get("id", "unknown")
        logger.info(f"Posted note (id: {note_id}).")
        return data

    @staticmethod
    def _clean_bot_lines(bio: str) -> str:
        """Strip ALL bot-generated lines from anywhere in the bio.

        Removes every line that looks like bot output: [Online]/[Offline]
        markers, "Now listening:" lines, music-platform URLs, and
        "Platform: URL" listings.  Returns only the user's own content.
        """
        if not bio:
            return ""

        _PLATFORM_PREFIXES = (
            "Spotify:", "Apple Music:", "YouTube:", "YouTube Music:",
            "Tidal:", "Amazon Music:", "Deezer:", "SoundCloud:", "song.link:",
        )

        _BOT_DOMAINS = (
            "song.link", "album.link", "odesli.co",
            "last.fm", "spotify.com", "open.spotify.com", "stats.fm",
            "music.apple.com", "youtube.com", "youtubemusic.com",
            "tidal.com", "amazon.", "deezer.com", "soundcloud.com",
        )

        keep: list[str] = []
        for line in bio.split("\n"):
            stripped = line.strip()

            if stripped.startswith(("[Online]", "[Offline]")):
                continue
            if stripped.startswith("Now listening:"):
                continue
            if stripped.startswith("Nothing playing"):
                continue
            if stripped.startswith("Currently running"):
                continue
            if stripped.startswith(_PLATFORM_PREFIXES):
                continue
            if stripped.startswith(("http://", "https://")):
                if any(d in stripped.lower() for d in _BOT_DOMAINS):
                    continue

            keep.append(line)

        return "\n".join(keep).strip()

    async def close(self):
        await self.client.aclose()
