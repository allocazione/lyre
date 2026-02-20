from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class Track:
    title: str
    artist: str
    album: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    is_now_playing: bool = False

    def __str__(self):
        return f"{self.artist} - {self.title}"

class MusicProvider(ABC):
    @abstractmethod
    async def get_now_playing(self) -> Optional[Track]:
        """Fetch the current playing track."""
        pass
