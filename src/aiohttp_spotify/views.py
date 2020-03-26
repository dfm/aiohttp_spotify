__all__ = ["routes"]

import logging
import secrets
from typing import Any, MutableMapping, Optional, Union

from aiohttp import ClientSession, web

from . import api

logger = logging.getLogger("aiohttp_spotify")

try:
    import aiohttp_session
except ImportError:
    logger.warn(
        "The OAuth flow for the Spotify API will be more secure if "
        "aiohttp_session is installed"
    )
    aiohttp_session = None

routes = web.RouteTableDef()


async def get_session(
    request: web.Request,
) -> Union[MutableMapping[str, Any], aiohttp_session.Session]:
    if aiohttp_session is None:
        return {}
    try:
        session = await aiohttp_session.get_session(request)
    except RuntimeError:
        session = {}
    return session


@routes.get("/auth", name="auth")
async def auth(request: web.Request) -> web.Response:
    session = await get_session(request)
    session["spotify_target_url"] = request.query.get("redirect")

    # Generate a state token
    state = secrets.token_urlsafe()
    session["spotify_state"] = state

    # Construct the redirect URL
    location = request.app["spotify_client"].get_oauth_url(state=state)

    return web.HTTPTemporaryRedirect(location=str(location))


@routes.get("/callback", name="callback")
async def callback(request: web.Request) -> web.Response:
    error = request.query.get("error")
    if error is not None:
        print(f"error: {error}")
        return await handle_error(request, error)

    code = request.query.get("code")
    if code is None:
        return await handle_error(request)

    session = await get_session(request)

    # Check that the 'state' matches
    state = session.pop("spotify_state", None)
    returned_state = request.query.get("state")
    if state is not None and state != returned_state:
        return await handle_error(request)

    # Construct the request to get the tokens
    async with ClientSession(raise_for_status=True) as client:
        auth = await request.app["spotify_client"].get_auth(client, code)

    return await handle_success(request, auth)


async def handle_error(
    request: web.Request, error: Optional[str] = None
) -> web.Response:
    if error is None:
        error = "Invalid request"
    handler = request.app.get("spotify_on_error")
    if handler is not None:
        return await handler(request, error)
    raise web.HTTPInternalServerError(
        text=f"Unhandled authorization error {error}"
    )


async def handle_success(
    request: web.Request, auth: api.SpotifyAuth
) -> web.Response:
    handler = request.app.get("spotify_handle_auth")
    if handler is not None:
        await handler(request, auth)

    handler = request.app.get("spotify_on_success")
    if handler is not None:
        return await handler(request, auth)

    session = await get_session(request)
    target_url = session.get("spotify_target_url")
    if target_url is None:
        target_url = request.app["spotify_default_redirect"]
        if target_url is None:
            return web.Response(body="authorized")

    return web.HTTPTemporaryRedirect(location=target_url)
