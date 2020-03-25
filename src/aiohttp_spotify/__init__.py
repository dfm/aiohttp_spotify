__all__ = ["__version__", "spotify_app", "SpotifyAuth", "SpotifyClient"]

from .app import spotify_app
from .api import SpotifyAuth, SpotifyClient
from .aiohttp_spotify_version import __version__

__uri__ = "https://github.com/dfm/aiohttp_spotify"
__author__ = "Daniel Foreman-Mackey"
__email__ = "foreman.mackey@gmail.com"
__license__ = "MIT"
__description__ = "An interface to the Spotify API that supports aiohttp"
