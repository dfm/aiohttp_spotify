import secrets

import pytest
from aiohttp import web

import aiohttp_spotify
from aiohttp_spotify.mock_api import mock_api_app


@pytest.fixture
def client(loop, aiohttp_client, aiohttp_unused_port):
    port = aiohttp_unused_port()
    api_url = f"http://localhost:{port}/api"

    client_id = secrets.token_urlsafe()
    client_secret = secrets.token_urlsafe()

    app = web.Application()

    app["api_app"] = api_app = mock_api_app(
        client_id, client_secret, "/spotify/callback"
    )

    app["spotify_app"] = spotify_app = aiohttp_spotify.spotify_app(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="/spotify/callback",
        auth_url=f"{api_url}/authorize",
        token_url=f"{api_url}/token",
        api_url=f"{api_url}/api",
    )

    app.add_subapp("/spotify", spotify_app)
    app.add_subapp("/api", api_app)

    return loop.run_until_complete(
        aiohttp_client(app, server_kwargs={"port": port})
    )
