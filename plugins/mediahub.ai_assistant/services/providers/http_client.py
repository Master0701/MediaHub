from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ProviderHttpError(RuntimeError):
    pass


def request_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: int = 20,
) -> Any:
    if params:
        encoded = urlencode({key: value for key, value in params.items() if value is not None}, doseq=True)
        url = f"{url}{'&' if '?' in url else '?'}{encoded}"

    payload = None
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "MediaHub-KI-Assistent/0.8.0",
        **(headers or {}),
    }
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    request = Request(url, data=payload, headers=request_headers, method=method.upper())
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return json.loads(response.read().decode(charset, errors="replace"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise ProviderHttpError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
    except URLError as exc:
        raise ProviderHttpError(f"Netzwerkfehler: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ProviderHttpError("Quelle lieferte keine gültige JSON-Antwort.") from exc
