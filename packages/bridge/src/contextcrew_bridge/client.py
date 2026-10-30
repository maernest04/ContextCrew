import httpx

from contextcrew_bridge.config import BridgeConfig


class BackendError(Exception):
    pass


async def request(config: BridgeConfig, method: str, path: str, **kwargs) -> dict:
    try:
        async with httpx.AsyncClient(
            base_url=config.api_url,
            headers={"Authorization": f"Bearer {config.token}"},
            timeout=10,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = await client.request(method, path, **kwargs)
        if response.is_error or response.is_redirect:
            raise BackendError(
                f"Backend returned HTTP {response.status_code}; operation not confirmed"
            )
        return response.json()
    except (httpx.HTTPError, ValueError):
        raise BackendError(
            "Backend unavailable or invalid response; operation not confirmed"
        ) from None
