__all__ = ["routes"]

import secrets
import logging
import time
from typing import Optional, Union, Any, MutableMapping

import yarl
from aiohttp import web, ClientSession

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


def get_redirect_uri(request: web.Request) -> str:
    """Get the redirect URI that the Spotify API expects"""
    return str(
        request.url.with_path(str(request.app.router["callback"].url_for()))
    )


@routes.get("/auth", name="auth")
async def auth(request: web.Request) -> web.Response:
    session = await get_session(request)
    session["spotify_target_url"] = request.query.get("redirect")

    # Generate a state token
    state = secrets.token_urlsafe()
    session["spotify_state"] = state

    # Construct the API OAuth2 URL
    args = dict(
        client_id=request.app["spotify_client_id"],
        response_type="code",
        redirect_uri=get_redirect_uri(request),
        state=state,
    )
    scope = request.app.get("spotify_scope")
    if scope is not None:
        args["scope"] = scope
    location = yarl.URL(api.SPOTIFY_AUTH_URL).with_query(**args)

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
    headers = {"Accept": "application/json"}
    data = dict(
        client_id=request.app.get("spotify_client_id"),
        client_secret=request.app.get("spotify_client_secret"),
        redirect_uri=get_redirect_uri(request),
        grant_type="authorization_code",
        code=request.query["code"],
    )
    async with ClientSession(raise_for_status=True) as client:
        async with client.post(
            api.SPOTIFY_TOKEN_URL, headers=headers, data=data
        ) as response:
            user_data = await response.json()

    # Expires *at* is more useful than *in* for us...
    auth = api.SpotifyAuth(
        access_token=user_data["access_token"],
        refresh_token=user_data["refresh_token"],
        expires_at=int(time.time()) + int(user_data["expires_in"]),
    )

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
    target_url = session.get(
        "spotify_target_url", request.app["spotify_default_redirect"]
    )
    if target_url is None:
        return web.Response(body="authorized")

    return web.HTTPTemporaryRedirect(location=target_url)
