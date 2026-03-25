from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any

import requests

from .env import ensure_env_loaded

log = logging.getLogger(__name__)

JLCPCB_OPENAPI_ENDPOINT = "https://open.jlcpcb.com"


class JLCOpenAPIError(RuntimeError):
    """Base class for JLC OpenAPI failures."""


class JLCOpenAPIConfigurationError(JLCOpenAPIError):
    """Raised when required JLC OpenAPI credentials are missing."""


class JLCOpenAPIRequestError(JLCOpenAPIError):
    """Raised for transport or HTTP-level request failures."""


class JLCOpenAPIBusinessError(JLCOpenAPIError):
    """Raised when JLC returns a business-level error response."""


@dataclass(frozen=True)
class JLCOpenAPICredentials:
    app_id: str
    access_key: str
    secret_key: str


def _env_value(name: str) -> str:
    return os.getenv(name, "").strip()


def load_jlc_openapi_credentials() -> JLCOpenAPICredentials | None:
    """
    Load signing credentials for the JLC OpenAPI from the local environment.

    The signing triplet is:
    - JLCPCB_APP_ID
    - JLCPCB_ACCESS_KEY
    - JLCPCB_SECRET_KEY
    """
    ensure_env_loaded()

    app_id = _env_value("JLCPCB_APP_ID")
    access_key = _env_value("JLCPCB_ACCESS_KEY")
    secret_key = _env_value("JLCPCB_SECRET_KEY")

    if app_id and access_key and secret_key:
        return JLCOpenAPICredentials(
            app_id=app_id,
            access_key=access_key,
            secret_key=secret_key,
        )

    return None


def detail_url_for_code(component_code: str) -> str:
    """Return the public JLC part-detail URL for a component code."""
    return f"https://jlcpcb.com/partdetail/{component_code}"


class JLCOpenAPIClient:
    """
    Thin direct HTTP client for the live JLC OpenAPI.

    The official Java SDK is currently incomplete relative to the live docs, so
    this client signs and issues the requests directly.
    """

    def __init__(
        self,
        *,
        app_id: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint: str = JLCPCB_OPENAPI_ENDPOINT,
        timeout_seconds: float = 20.0,
    ) -> None:
        ensure_env_loaded()

        self.endpoint = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.credentials = JLCOpenAPICredentials(
            app_id=(app_id or _env_value("JLCPCB_APP_ID")),
            access_key=(access_key or _env_value("JLCPCB_ACCESS_KEY")),
            secret_key=(secret_key or _env_value("JLCPCB_SECRET_KEY")),
        )

    def is_configured(self) -> bool:
        return bool(
            self.credentials.app_id
            and self.credentials.access_key
            and self.credentials.secret_key
        )

    def get_component_infos(self, *, last_key: str = "") -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if last_key:
            payload["lastKey"] = last_key
        return self._post("/overseas/openapi/component/getComponentInfos", payload)

    def get_private_component_library(self) -> list[dict[str, Any]]:
        response = self._post("/overseas/openapi/component/getPrivateComponentLibrary", {})
        data = response.get("data")
        if isinstance(data, list):
            return data
        raise JLCOpenAPIRequestError("JLC private component library response was not a list.")

    def get_component_detail_by_code(self, component_code: str) -> dict[str, Any] | None:
        details = self.get_component_detail_by_codes([component_code])
        return details[0] if details else None

    def get_component_detail_by_codes(self, component_codes: list[str]) -> list[dict[str, Any]]:
        cleaned_codes = [code.strip() for code in component_codes if code and code.strip()]
        if not cleaned_codes:
            raise ValueError("component_codes must contain at least one non-empty code.")

        response = self._post(
            "/overseas/openapi/component/getComponentDetailByCode",
            {"componentCodes": cleaned_codes},
        )

        data = response.get("data")
        if isinstance(data, list):
            return data
        raise JLCOpenAPIRequestError("JLC component detail response was not a list.")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_configured()

        body_text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        headers = {
            "Content-Type": "application/json",
            "Authorization": self._build_authorization_header(
                method="POST",
                path=path,
                body_text=body_text,
            ),
        }

        url = f"{self.endpoint}{path}"

        try:
            response = requests.post(
                url,
                data=body_text.encode("utf-8"),
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise JLCOpenAPIRequestError(
                f"JLC OpenAPI request failed for {path}: {exc}"
            ) from exc

        try:
            payload_obj = response.json()
        except ValueError as exc:
            raise JLCOpenAPIRequestError(
                f"JLC OpenAPI response for {path} was not valid JSON (status {response.status_code})."
            ) from exc

        if response.status_code != 200:
            message = payload_obj.get("message") if isinstance(payload_obj, dict) else None
            raise JLCOpenAPIRequestError(
                f"JLC OpenAPI HTTP {response.status_code} for {path}: {message or 'request failed'}"
            )

        if not isinstance(payload_obj, dict):
            raise JLCOpenAPIRequestError(
                f"JLC OpenAPI response for {path} was not an object."
            )

        if payload_obj.get("code") != 200 or payload_obj.get("success") is not True:
            raise JLCOpenAPIBusinessError(
                f"JLC OpenAPI business failure for {path}: "
                f"code={payload_obj.get('code')} message={payload_obj.get('message')}"
            )

        return payload_obj

    def _build_authorization_header(self, *, method: str, path: str, body_text: str) -> str:
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        string_to_sign = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_text}\n"
        signature = base64.b64encode(
            hmac.new(
                self.credentials.secret_key.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("ascii")

        return (
            "JOP "
            f'appid="{self.credentials.app_id}",'
            f'accesskey="{self.credentials.access_key}",'
            f'nonce="{nonce}",'
            f'timestamp="{timestamp}",'
            f'signature="{signature}"'
        )

    def _require_configured(self) -> None:
        if self.is_configured():
            return
        raise JLCOpenAPIConfigurationError(
            "JLCPCB OpenAPI credentials are not configured. "
            "Set JLCPCB_APP_ID, JLCPCB_ACCESS_KEY, and JLCPCB_SECRET_KEY."
        )
