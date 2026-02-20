from typing import Optional

import asyncio
import pylast

from lyre.clients.music.base import MusicProvider, Track
from lyre.config import Config
from lyre.logger import logger

class LastFmProvider(MusicProvider):
    def __init__(self):
        self.network = pylast.LastFMNetwork(
            api_key=Config.LASTFM_API_KEY,
            api_secret=Config.LASTFM_API_SECRET
        )
        self.user = self.network.get_user(Config.LASTFM_USERNAME)
        logger.info(f"Initialized Last.fm provider for user: {Config.LASTFM_USERNAME}")

    async def get_now_playing(self) -> Optional[Track]:
        try:
            # pylast is synchronous, so we run it in an executor
            loop = asyncio.get_event_loop()
            track = await loop.run_in_executor(None, self._fetch_now_playing)
            return track
        except Exception as e:
            logger.error(f"Error fetching from Last.fm: {e}")
            return None

    def _fetch_now_playing(self) -> Optional[Track]:
        try:
            # get_now_playing returns the track if it's currently playing, else None
            now_playing = self.user.get_now_playing()
            if now_playing:
                return Track(
                    title=now_playing.title,
                    artist=now_playing.artist.name,
                    album=now_playing.get_album().title if now_playing.get_album() else None,
                    url=now_playing.get_url(),
                    image_url=now_playing.get_cover_image(),
                    is_now_playing=True
                )
            
            # Optionally check recent tracks if we want the *last* played, but the prompt says "Now Listening"
            return None
        except Exception as e:
             logger.error(f"Error in _fetch_now_playing: {e}")
             return None
