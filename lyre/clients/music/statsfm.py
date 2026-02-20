import httpx
from typing import Optional
from lyre.clients.music.base import MusicProvider, Track
from lyre.config import Config
from lyre.logger import logger

STATSFM_BASE_URL = "https://beta-api.stats.fm/api/v1"


class StatsFmProvider(MusicProvider):
    """Music provider that fetches currently playing data from Stats.fm beta API."""

    def __init__(self):
        self.username = Config.STATSFM_USERNAME
        self.client = httpx.AsyncClient(
            base_url=STATSFM_BASE_URL,
            timeout=10.0,
            headers={"User-Agent": "Lyre/0.1.0 (NowListening Bot)"},
        )
        logger.info(f"Initialized Stats.fm provider for user: {self.username}")

    async def get_now_playing(self) -> Optional[Track]:
        try:
            response = await self.client.get(
                f"/users/{self.username}/streams/current"
            )
            if response.status_code == 200:
                data = response.json()
                return self._parse_current_stream(data)
            elif response.status_code == 204:
                # 204 No Content = nothing currently playing
                logger.debug("Stats.fm: No track currently playing.")
                return None
            else:
                logger.warning(
                    f"Stats.fm returned status {response.status_code}: {response.text}"
                )
                # Fall back to recent streams
                return await self._get_recent_stream()
        except Exception as e:
            logger.error(f"Error fetching from Stats.fm: {e}")
            return None

    async def _get_recent_stream(self) -> Optional[Track]:
        """Fallback: fetch the most recent stream if current is unavailable."""
        try:
            response = await self.client.get(
                f"/users/{self.username}/streams/recent"
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    return self._parse_stream_item(data[0], is_now_playing=False)
                elif isinstance(data, dict) and data.get("items"):
                    return self._parse_stream_item(
                        data["items"][0], is_now_playing=False
                    )
            return None
        except Exception as e:
            logger.error(f"Error fetching recent streams from Stats.fm: {e}")
            return None

    def _parse_current_stream(self, data: dict) -> Optional[Track]:
        """Parse the /streams/current response."""
        try:
            # The response structure may vary; handle common shapes
            if isinstance(data, dict):
                # Could be nested under "item" or directly contain track info
                item = data.get("item", data)
                return self._parse_stream_item(item, is_now_playing=True)
            elif isinstance(data, list) and len(data) > 0:
                return self._parse_stream_item(data[0], is_now_playing=True)
            return None
        except Exception as e:
            logger.error(f"Error parsing Stats.fm current stream: {e}")
            return None

    def _parse_stream_item(
        self, item: dict, is_now_playing: bool = False
    ) -> Optional[Track]:
        """Parse a single stream item into a Track object."""
        try:
            track_info = item.get("track", item)
            artists = track_info.get("artists", [])
            artist_name = (
                artists[0].get("name", "Unknown Artist")
                if artists
                else track_info.get("artistName", "Unknown Artist")
            )
            album_info = track_info.get("albums", [{}])
            album_name = (
                album_info[0].get("name") if album_info else track_info.get("albumName")
            )
            image = (
                album_info[0].get("image") if album_info else track_info.get("image")
            )

            return Track(
                title=track_info.get("name", "Unknown Track"),
                artist=artist_name,
                album=album_name,
                url=track_info.get("externalIds", {}).get("spotify", [None])[0]
                if track_info.get("externalIds") and track_info.get("externalIds").get("spotify")
                else None,
                image_url=image,
                is_now_playing=is_now_playing,
            )
        except Exception as e:
            logger.error(f"Error parsing Stats.fm stream item: {e}")
            return None

    async def close(self):
        await self.client.aclose()
