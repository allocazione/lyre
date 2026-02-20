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

    async def set_online(self) -> None:
        """Mark the bot as online in the bio."""
        profile = await self.get_profile()
        current_bio = profile.get("description", "") or ""

        # Cache the user's real bio (with all bot headers stripped)
        self._clean_bio = self._clean_bot_header(current_bio)

        if self._clean_bio:
            new_bio = f"[Online] Currently running.\n\n{self._clean_bio}"
        else:
            new_bio = "[Online] Currently running."
        await self.update_bio(new_bio)
        logger.info("Status set to Online.")

    async def set_offline(self) -> None:
        """Mark the bot as offline in the bio."""
        if self._clean_bio is None:
            profile = await self.get_profile()
            current_bio = profile.get("description", "") or ""
            self._clean_bio = self._clean_bot_header(current_bio)

        if self._clean_bio:
            new_bio = f"[Offline]\n\n{self._clean_bio}"
        else:
            new_bio = "[Offline]"
        await self.update_bio(new_bio)
        logger.info("Status set to Offline.")

    async def update_now_playing(self, track_str: str, link: str = "") -> None:
        """Update the bio with the currently playing track.

        Args:
            track_str: Display string for the track (e.g. "Artist - Title").
            link: Optional URL (song.link, Spotify, etc.) shown below the header.
        """
        if self._clean_bio is None:
            profile = await self.get_profile()
            current_bio = profile.get("description", "") or ""
            self._clean_bio = self._clean_bot_header(current_bio)

        header = f"[Online] Now listening: {track_str}"
        if link:
            header += f"\n{link}"

        if self._clean_bio:
            new_bio = f"{header}\n\n{self._clean_bio}"
        else:
            new_bio = header
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
    def _clean_bot_header(bio: str) -> str:
        """Remove all bot status and attached song links from the top of the bio.

        Uses a loop to gracefully handle multiple accumulated headers or orphaned
        links left by older versions of the bot.
        """
        if not bio:
            return ""

        lines = bio.split("\n")

        # Platform prefixes emitted by SongLinkClient.format_links (full listing)
        _PLATFORM_PREFIXES = (
            "Spotify:", "Apple Music:", "YouTube:", "YouTube Music:",
            "Tidal:", "Amazon Music:", "Deezer:", "SoundCloud:", "song.link:",
        )

        # All URL domains the bot could possibly insert
        _BOT_DOMAINS = (
            "song.link", "album.link", "odesli.co",
            "last.fm", "spotify.com", "stats.fm",
            "music.apple.com", "youtube.com", "youtubemusic.com",
            "tidal.com", "amazon.", "deezer.com", "soundcloud.com",
        )

        while lines:
            first = lines[0].strip()

            # 1. Remove bot status markers ([Online] / [Offline])
            if first.startswith("[Online]") or first.startswith("[Offline]"):
                lines.pop(0)
                continue

            # 2. Remove orphaned "Now listening" lines
            if first.startswith("Now listening:"):
                lines.pop(0)
                continue

            # 3. Remove music platform URLs
            if first.startswith(("http://", "https://")):
                url = first.lower()
                if any(domain in url for domain in _BOT_DOMAINS):
                    lines.pop(0)
                    continue

            # 4. Remove "Platform: URL" lines from full song.link listings
            if first.startswith(_PLATFORM_PREFIXES):
                lines.pop(0)
                continue

            # 5. Remove blank lines used as spacing
            if first == "":
                lines.pop(0)
                continue

            # If we reach here, it's normal user bio text
            break

        return "\n".join(lines).strip()

    async def close(self):
        await self.client.aclose()
