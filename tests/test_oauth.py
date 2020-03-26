import yarl


async def test_redirect(client):
    resp = await client.get("/spotify/auth", allow_redirects=False)
    assert resp.status == 307

    resp = await client.get("/spotify/auth")
    assert resp.status == 200
    assert yarl.URL(resp.url).path == "/spotify/callback"
