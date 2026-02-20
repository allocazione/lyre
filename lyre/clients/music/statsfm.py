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

    def _parse_current_stream(self, data) -> Optional[Track]:
        """Parse the /streams/current response."""
        try:
            if data is None:
                return None
            
            # The API sometimes returns the last played track even when paused,
            # but marks it with "isPlaying": false.
            if isinstance(data, dict):
                is_playing = data.get("isPlaying")
                # If explicitly marked as not playing, return None
                if is_playing is False:
                    logger.debug("Stats.fm reports track is paused (isPlaying=False).")
                    return None
                    
                item = data.get("item") or data
                return self._parse_stream_item(item, is_now_playing=True)
                
            elif isinstance(data, list) and len(data) > 0 and data[0]:
                item = data[0]
                if isinstance(item, dict) and item.get("isPlaying") is False:
                    logger.debug("Stats.fm reports track is paused (isPlaying=False).")
                    return None
                return self._parse_stream_item(item, is_now_playing=True)
                
            return None
        except Exception as e:
            logger.error(f"Error parsing Stats.fm current stream: {e}")
            return None

    def _parse_stream_item(
        self, item, is_now_playing: bool = False
    ) -> Optional[Track]:
        """Parse a single stream item into a Track object."""
        if not item or not isinstance(item, dict):
            return None

        try:
            track_info = item.get("track") or item
            if not isinstance(track_info, dict):
                return None

            # -- Artist --
            artists = track_info.get("artists") or []
            first_artist = artists[0] if artists else None
            if first_artist and isinstance(first_artist, dict):
                artist_name = first_artist.get("name") or "Unknown Artist"
            else:
                artist_name = track_info.get("artistName") or "Unknown Artist"

            # -- Album --
            albums = track_info.get("albums") or []
            first_album = albums[0] if albums else None
            if first_album and isinstance(first_album, dict):
                album_name = first_album.get("name")
                image = first_album.get("image")
            else:
                album_name = track_info.get("albumName")
                image = track_info.get("image")

            # -- URL (Spotify external ID) --
            external_ids = track_info.get("externalIds")
            url = None
            if external_ids and isinstance(external_ids, dict):
                spotify_ids = external_ids.get("spotify")
                if spotify_ids and isinstance(spotify_ids, list) and len(spotify_ids) > 0:
                    url = spotify_ids[0]

            return Track(
                title=track_info.get("name") or "Unknown Track",
                artist=artist_name,
                album=album_name,
                url=url,
                image_url=image,
                is_now_playing=is_now_playing,
            )
        except Exception as e:
            logger.error(f"Error parsing Stats.fm stream item: {e}")
            return None

    async def close(self):
        await self.client.aclose()
