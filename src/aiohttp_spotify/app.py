__all__ = ["spotify_app"]

import base64
from typing import Optional, Iterable, Callable, Dict, Any

import aiohttp_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
from aiohttp import web

from .views import routes


def spotify_app(
    *,
    client_id: str,
    client_secret: str,
    scope: Iterable[str] = None,
    on_success: Optional[
        Callable[[web.Request, Dict[str, Any]], web.Response]
    ] = None,
    on_error: Optional[Callable[[web.Request, str], web.Response]] = None,
    cookie_name: str = "AIOHTTP_SPOTIFY_SESSION",
) -> web.Application:
    app = web.Application()

    # Store the configuration settings on the app
    app["spotify_client_id"] = client_id
    app["spotify_client_secret"] = client_secret
    app["spotify_scope"] = None if scope is None else " ".join(scope)
    app["spotify_on_success"] = on_success
    app["spotify_on_error"] = on_error

    # Set up the session
    secret_key = base64.urlsafe_b64decode(fernet.Fernet.generate_key())
    aiohttp_session.setup(
        app, EncryptedCookieStorage(secret_key, cookie_name=cookie_name),
    )

    # Add the views
    app.add_routes(routes)

    return app
