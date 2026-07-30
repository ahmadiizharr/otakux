import httpx

from .config import settings

_BASE_URL = (
    f"https://api.cloudflare.com/client/v4/accounts/{settings.cf_account_id}"
    f"/d1/database/{settings.cf_d1_database_id}/query"
)


class D1Error(Exception):
    pass


async def query(sql: str, params: list | None = None) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _BASE_URL,
            headers={"Authorization": f"Bearer {settings.cf_api_token}"},
            json={"sql": sql, "params": params or []},
            timeout=30,
        )

    data = resp.json()
    if not data.get("success"):
        raise D1Error(data.get("errors"))

    return data["result"][0]["results"]
