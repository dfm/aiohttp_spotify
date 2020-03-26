__all__ = [
    "__version__",
    "spotify_app",
    "SpotifyAuth",
    "SpotifyClient",
    "SpotifyResponse",
]

from .aiohttp_spotify_version import __version__
from .api import SpotifyAuth, SpotifyClient, SpotifyResponse
from .app import spotify_app

__uri__ = "https://github.com/dfm/aiohttp_spotify"
__author__ = "Daniel Foreman-Mackey"
__email__ = "foreman.mackey@gmail.com"
__license__ = "MIT"
__description__ = "An interface to the Spotify API that supports aiohttp"
