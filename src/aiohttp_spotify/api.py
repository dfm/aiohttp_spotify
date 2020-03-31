__all__ = ["SpotifyAuth", "SpotifyResponse", "SpotifyClient"]

import asyncio
import json
import time
from typing import Any, Iterable, Mapping, NamedTuple, Optional

import yarl
from aiohttp import ClientSession


class SpotifyAuth(NamedTuple):
    """Authorization information for accessing the API"""

    access_token: str
    refresh_token: str
    expires_at: int


class SpotifyResponse(NamedTuple):
    """The contents of a response from the API"""

    auth_changed: bool
    auth: SpotifyAuth
    status: int
    headers: Mapping[str, str]
    body: bytes

    def json(self) -> Mapping[str, Any]:
        """Parse the response body as JSON"""
        return json.loads(self.body)


class SpotifyClient:
    """An interface to the Spotify API

    Args:
        client_id (str): The client ID for your app from Spotify
        client_secret (str): The client secret for your app
        redirect_uri (str): The URI registered with Spotify as the redirect
        scope (Iterable[str], optional): A list of access scopes to request

    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: Optional[str] = None,
        scope: Optional[Iterable[str]] = None,
        auth_url: str = "https://accounts.spotify.com/authorize",
        token_url: str = "https://accounts.spotify.com/api/token",
        api_url: str = "https://api.spotify.com/v1",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = None if scope is None else " ".join(scope)
        self.auth_url = auth_url
        self.token_url = token_url
        self.api_url = api_url

    def get_oauth_url(self, *, state: Optional[str] = None) -> yarl.URL:
        """Get the URL to start the OAuth flow

        Client's should redirect to this URL.

        Args:
            state (Optional[str], optional): If provided, this string will be
                returned to the callback for added security

        Raises:
            ValueError: If a redirect URI was not provided

        Returns:
            yarl.URL: The URL of the flow

        """
        if self.redirect_uri is None:
            raise ValueError(
                "A 'redirect_uri' must be provided for the OAuth flow"
            )
        args = dict(
            client_id=self.client_id,
            response_type="code",
            redirect_uri=self.redirect_uri,
            state=state,
        )
        if self.scope is not None:
            args["scope"] = self.scope
        return yarl.URL(self.auth_url).with_query(**args)

    async def get_auth(self, session: ClientSession, code: str) -> SpotifyAuth:
        """Given a OAuth code, get the full authorization access

        Args:
            session (ClientSession): A session for executing HTTP requests
            code (str): The code returned by the API

        Raises:
            ValueError: If a redirect URI was not provided

        Returns:
            SpotifyAuth: The authorization information

        """
        if self.redirect_uri is None:
            raise ValueError(
                "A 'redirect_uri' must be provided for the OAuth flow"
            )
        headers = {"Accept": "application/json"}
        data = dict(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            grant_type="authorization_code",
            code=code,
        )

        async with session.post(
            self.token_url, headers=headers, data=data
        ) as response:
            user_data = await response.json()

        return SpotifyAuth(
            access_token=user_data["access_token"],
            refresh_token=user_data["refresh_token"],
            expires_at=int(time.time()) + int(user_data["expires_in"]),
        )

    async def update_auth(
        self, session: ClientSession, auth: SpotifyAuth
    ) -> SpotifyAuth:
        """Update the authorization by requesting a new access token

        Args:
            session (ClientSession): A session for executing HTTP requests
            auth (SpotifyAuth): The current authorization information

        Returns:
            SpotifyAuth: The updated information

        """
        data = dict(
            client_id=self.client_id,
            client_secret=self.client_secret,
            grant_type="refresh_token",
            refresh_token=auth.refresh_token,
        )
        async with session.post(self.token_url, data=data) as response:
            response.raise_for_status()
            user_data = await response.json()
        return SpotifyAuth(
            access_token=user_data["access_token"],
            refresh_token=auth.refresh_token,
            expires_at=int(time.time()) + int(user_data["expires_in"]),
        )

    async def request(
        self,
        session: ClientSession,
        auth: SpotifyAuth,
        endpoint: str,
        *,
        method: str = "GET",
        **payload,
    ) -> SpotifyResponse:
        """Make a request to the API

        Note that this handles rate limiting.

        Args:
            session (ClientSession): A session for executing HTTP requests
            auth (SpotifyAuth): The current authorization information
            endpoint (str): The API endpoint to be requested
            method (str, optional): The HTTP method. Defaults to "GET".

        Returns:
            SpotifyResponse: The response from the request

        """
        # Update the access token if it is to expire soon
        auth_changed = False
        if auth.expires_at - time.time() <= 60:
            auth_changed = True
            auth = await self.update_auth(session, auth)

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {auth.access_token}",
        }
        async with session.request(
            method, self.api_url + endpoint, headers=headers, **payload
        ) as response:
            if response.status == 429:
                # We got rate limited!
                await asyncio.sleep(int(response.headers["Retry-After"]))
                return await self.request(
                    session, auth, endpoint, method=method, **payload
                )

            response.raise_for_status()

            return SpotifyResponse(
                auth_changed,
                auth,
                response.status,
                response.headers,
                await response.read(),
            )
