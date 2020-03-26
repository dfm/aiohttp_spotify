__all__ = ["spotify_app"]

from typing import Callable, Iterable, Optional

from aiohttp import web

from .api import SpotifyAuth
from .views import routes


def spotify_app(
    *,
    client_id: str,
    client_secret: str,
    scope: Iterable[str] = None,
    default_redirect: Optional[str] = None,
    handle_auth: Optional[Callable[[web.Request, SpotifyAuth], None]] = None,
    on_success: Optional[
        Callable[[web.Request, SpotifyAuth], web.Response]
    ] = None,
    on_error: Optional[Callable[[web.Request, str], web.Response]] = None,
) -> web.Application:
    app = web.Application()

    # Store the configuration settings on the app
    app["spotify_client_id"] = client_id
    app["spotify_client_secret"] = client_secret
    app["spotify_scope"] = None if scope is None else " ".join(scope)
    app["spotify_default_redirect"] = default_redirect
    app["spotify_handle_auth"] = handle_auth
    app["spotify_on_success"] = on_success
    app["spotify_on_error"] = on_error

    # Add the views
    app.add_routes(routes)

    return app
