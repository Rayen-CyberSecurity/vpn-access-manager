"""Thin HTTP wrapper. Contains no business rules on purpose."""

import requests


class ApiError(Exception):
    """Carries the server's own message so the UI can show it verbatim."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ApiClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _call(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        if method != "GET":
            headers["X-API-Key"] = self.api_key
        try:
            r = requests.request(
                method, url, headers=headers, timeout=self.timeout, **kwargs
            )
        except requests.exceptions.ConnectionError:
            raise ApiError(f"Cannot reach the server at {self.base_url}.")
        except requests.exceptions.Timeout:
            raise ApiError("The server did not respond in time.")

        if r.status_code >= 400:
            try:
                detail = r.json()["detail"]
                if isinstance(detail, list):        # 422 from Pydantic
                    detail = "; ".join(d.get("msg", str(d)) for d in detail)
            except Exception:
                detail = f"HTTP {r.status_code}"
            raise ApiError(str(detail), r.status_code)

        return r.json()

    # ---- endpoints ----
    def health(self):
        return self._call("GET", "/health")

    def users(self):
        return self._call("GET", "/users")

    def gateways(self):
        return self._call("GET", "/gateways")

    def sessions(self, status=None, gateway=None):
        params = {}
        if status:
            params["status"] = status
        if gateway:
            params["gateway"] = gateway
        return self._call("GET", "/sessions", params=params)

    def open_session(self, user_id: int, gateway_id: int, client_ip: str):
        return self._call(
            "POST",
            "/sessions",
            json={
                "user_id": user_id,
                "gateway_id": gateway_id,
                "client_ip": client_ip,
            },
        )

    def close_session(self, session_id: int, bytes_transferred: int = 0):
        return self._call(
            "POST",
            f"/sessions/{session_id}/close",
            json={"bytes_transferred": bytes_transferred},
        )
