"""telltape: live financial and world news headlines in your terminal."""

from .cli import main
from .engine import NewsEngine
from .models import FeedSource, Headline

__all__ = ["main", "NewsEngine", "FeedSource", "Headline"]
__version__ = "0.1.0"
