import argparse
import base64
from functools import wraps
from typing import Callable, Awaitable, AsyncIterator

import aiohttp_session
from cryptography import fernet
from aiohttp import web, ClientSession
from aiohttp_session.cookie_storage import EncryptedCookieStorage

import aiohttp_spotify
from aiohttp_spotify import SpotifyAuth, SpotifyClient


async def client_session(app: web.Application) -> AsyncIterator[None]:
    async with ClientSession() as session:
        app["client_session"] = session
        yield


def parse_config() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client_id", required=True)
    parser.add_argument("--client_secret", required=True)
    parser.add_argument("-p", "--port", type=int, default=5000)
    return parser.parse_args()


def require_auth(
    handler: Callable[[web.Request, SpotifyAuth], Awaitable[web.Response]]
) -> Callable[[web.Request], Awaitable[web.Response]]:
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
    return web.Response(body="hi!")


@require_auth
async def me(request: web.Request, auth: SpotifyAuth) -> web.Response:
    auth, status, headers, content = await request.app[
        "spotify_client"
    ].request(request.app["client_session"], auth, "/me", parse_json=True)
    return web.json_response(content)


async def update_auth(request: web.Request, auth: aiohttp_spotify.SpotifyAuth):
    session = await aiohttp_session.get_session(request)
    session["spotify_auth"] = auth


def app_factory(client_id: str, client_secret: str) -> web.Application:
    app = web.Application()

    app.router.add_get("/", index, name="index")
    app.router.add_get("/me", me, name="me")

    app["spotify_app"] = aiohttp_spotify.spotify_app(
        client_id=client_id,
        client_secret=client_secret,
        handle_auth=update_auth,
    )
    app.add_subapp("/spotify", app["spotify_app"])

    # Set up the user session
    secret_key = base64.urlsafe_b64decode(fernet.Fernet.generate_key())
    aiohttp_session.setup(app, EncryptedCookieStorage(secret_key))

    app.cleanup_ctx.append(client_session)

    app["spotify_client"] = SpotifyClient(
        client_id=client_id, client_secret=client_secret
    )

    return app


if __name__ == "__main__":
    config = parse_config()
    web.run_app(
        app_factory(config.client_id, config.client_secret), port=config.port
    )
