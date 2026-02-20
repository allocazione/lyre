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
        self._original_bio: Optional[str] = None
        logger.info(f"Initialized Misskey client for instance: {self.instance_url}")

    async def verify_credentials(self) -> dict:
        """Verify the access token and return account info.
        Used by --debug-acc flag."""
        response = await self.client.post(
            "/api/i",
            json={"i": self.token},
        )
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
        response.raise_for_status()
        logger.info(f"Bio updated.")

    async def set_online(self) -> None:
        """Mark the bot as online in the bio."""
        profile = await self.get_profile()
        current_bio = profile.get("description", "") or ""
        self._original_bio = current_bio

        # Remove any existing status line and prepend online status
        clean_bio = self._strip_status_line(current_bio)
        clean_bio = self._strip_now_playing_line(clean_bio)
        if clean_bio:
            new_bio = f"[Online] Currently running.\n\n{clean_bio}"
        else:
            new_bio = "[Online] Currently running."
        await self.update_bio(new_bio)
        logger.info("Status set to Online.")

    async def set_offline(self) -> None:
        """Mark the bot as offline in the bio."""
        profile = await self.get_profile()
        current_bio = profile.get("description", "") or ""

        clean_bio = self._strip_status_line(current_bio)
        # Also strip any "now listening" line
        clean_bio = self._strip_now_playing_line(clean_bio)
        if clean_bio:
            new_bio = f"[Offline]\n\n{clean_bio}"
        else:
            new_bio = "[Offline]"
        await self.update_bio(new_bio)
        logger.info("Status set to Offline.")

    async def update_now_playing(self, track_str: str) -> None:
        """Update the bio with the currently playing track."""
        profile = await self.get_profile()
        current_bio = profile.get("description", "") or ""

        clean_bio = self._strip_status_line(current_bio)
        clean_bio = self._strip_now_playing_line(clean_bio)
        if clean_bio:
            new_bio = f"[Online] Now listening: {track_str}\n\n{clean_bio}"
        else:
            new_bio = f"[Online] Now listening: {track_str}"
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
        response.raise_for_status()
        data = response.json()
        note_id = data.get("createdNote", {}).get("id", "unknown")
        logger.info(f"Posted note (id: {note_id}).")
        return data

    @staticmethod
    def _strip_status_line(bio: str) -> str:
        """Remove existing [Online]/[Offline] lines from bio."""
        lines = bio.split("\n")
        # Only remove lines that explicitly start with our status markers
        filtered = [
            line
            for line in lines
            if not line.strip().startswith("[Online]")
            and not line.strip().startswith("[Offline]")
        ]
        return "\n".join(filtered).strip()

    @staticmethod
    def _strip_now_playing_line(bio: str) -> str:
        """Remove 'Now listening:' lines."""
        lines = bio.split("\n")
        # Only remove the line if it starts with the specific prefix to avoid
        # stripping user text that happens to contain "Now listening:"
        filtered = [
            line for line in lines if not line.strip().startswith("Now listening:")
        ]
        return "\n".join(filtered).strip()

    async def close(self):
        await self.client.aclose()
