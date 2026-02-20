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

    async def close(self):
        await self.client.aclose()
