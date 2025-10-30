async def test_health(async_client):
    r = await async_client.get("/healthz")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
