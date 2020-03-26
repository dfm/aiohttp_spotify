__all__ = ["spotify_app"]

from typing import Callable, Iterable, Optional

from aiohttp import web

from .api import SpotifyAuth, SpotifyClient
from .views import routes


def spotify_app(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    scope: Optional[Iterable[str]] = None,
    default_redirect: Optional[str] = None,
    handle_auth: Optional[Callable[[web.Request, SpotifyAuth], None]] = None,
    on_success: Optional[
        Callable[[web.Request, SpotifyAuth], web.Response]
    ] = None,
    on_error: Optional[Callable[[web.Request, str], web.Response]] = None,
    auth_url: str = "https://accounts.spotify.com/authorize",
    token_url: str = "https://accounts.spotify.com/api/token",
    api_url: str = "https://api.spotify.com/v1",
) -> web.Application:
    app = web.Application()

    # Add the views
    app.add_routes(routes)

    # Set up the client
    app["spotify_client"] = SpotifyClient(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        auth_url=auth_url,
        token_url=token_url,
        api_url=api_url,
    )

    # Store the configuration settings on the app
    app["spotify_default_redirect"] = default_redirect
    app["spotify_handle_auth"] = handle_auth
    app["spotify_on_success"] = on_success
    app["spotify_on_error"] = on_error

    return app
