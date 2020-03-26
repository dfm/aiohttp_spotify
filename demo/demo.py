import base64
from functools import wraps
from typing import Any, AsyncIterator, Awaitable, Callable, Mapping

import aiohttp_session
import toml
from aiohttp import ClientSession, web
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet

import aiohttp_spotify
from aiohttp_spotify import SpotifyAuth


def require_auth(
    handler: Callable[[web.Request, SpotifyAuth], Awaitable[web.Response]]
) -> Callable[[web.Request], Awaitable[web.Response]]:
    """A decorator requiring that the user is authenticated to see a view"""

    @wraps(handler)
    async def wrapped(request: web.Request) -> web.Response:
        session = await aiohttp_session.get_session(request)
        auth = session.get("spotify_auth")
        if auth is None:
            raise web.HTTPTemporaryRedirect(
                location=request.app["spotify_app"]
                .router["auth"]
                .url_for()
                .with_query(redirect=request.url.path)
            )
        return await handler(request, SpotifyAuth(*auth))

    return wrapped


async def index(request: web.Request) -> web.Response:
    """A placeholder index page"""
    return web.Response(body="here we are.")


@require_auth
async def me(request: web.Request, auth: SpotifyAuth) -> web.Response:
    """View to show the authorized user's Spotify user information"""
    response = await request.app["spotify_app"]["spotify_client"].request(
        request.app["client_session"], auth, "/me"
    )

    # Don't forget to update the authorization!
    if response.auth_changed:
        await update_auth(request, response.auth)

    return web.json_response(response.json())


async def update_auth(
    request: web.Request, auth: aiohttp_spotify.SpotifyAuth
) -> None:
    """Handle updating the stored authorization information"""
    session = await aiohttp_session.get_session(request)
    session["spotify_auth"] = auth


async def client_session(app: web.Application) -> AsyncIterator[None]:
    """A fixture to create a single ClientSession for the app to use"""
    async with ClientSession() as session:
        app["client_session"] = session
        yield


def parse_config() -> Mapping[str, Any]:
    """Load a TOML configuration file"""
    return toml.load("config.toml")


def app_factory(
    client_id: str, client_secret: str, redirect_uri: str
) -> web.Application:
    app = web.Application()

    # Add the main routes to the app
    app.router.add_get("/", index, name="index")
    app.router.add_get("/me", me, name="me")

    # Set up the Spotify app to instigate the OAuth flow
    app["spotify_app"] = aiohttp_spotify.spotify_app(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        handle_auth=update_auth,
        default_redirect=app.router["index"].url_for(),
    )
    app.add_subapp("/spotify", app["spotify_app"])

    # Set up the user session
    secret_key = base64.urlsafe_b64decode(fernet.Fernet.generate_key())
    aiohttp_session.setup(app, EncryptedCookieStorage(secret_key))

    # Add the ClientSession to the app
    app.cleanup_ctx.append(client_session)

    return app


if __name__ == "__main__":
    config = parse_config()
    web.run_app(
        app_factory(
            config["client_id"],
            config["client_secret"],
            config["redirect_uri"],
        ),
        port=config["port"],
    )
