from dataclasses import dataclass
from typing import Optional


@dataclass
class MediaObject:
    title: str
    date: str
    rating: float
    synopsis: str
    TMDBid: int
    type: str
    tvdb_id: Optional[int] = None
