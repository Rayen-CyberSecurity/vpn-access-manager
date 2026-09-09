"""Thin HTTP wrapper for the VPN Access Manager API."""

import requests


class ApiError(Exception):
    """Carry an API error message to the user interface."""

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
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.exceptions.ConnectionError:
            raise ApiError(f"Cannot reach the server at {self.base_url}.")
        except requests.exceptions.Timeout:
            raise ApiError("The server did not respond in time.")

        if response.status_code >= 400:
            try:
                detail = response.json()["detail"]
                if isinstance(detail, list):
                    detail = "; ".join(
                        item.get("msg", str(item)) for item in detail
                    )
            except Exception:
                detail = f"HTTP {response.status_code}"

            raise ApiError(str(detail), response.status_code)

        return response.json()

    def gateways(self):
        return self._call("GET", "/gateways")

    def sessions(self, status=None, gateway=None):
        params = {}

        if status:
            params["status"] = status

        if gateway:
            params["gateway"] = gateway

        return self._call("GET", "/sessions", params=params)

    def get_session(self, session_id: int):
        return self._call("GET", f"/sessions/{session_id}")

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
