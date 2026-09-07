"""
Autenticacion contra Microsoft Graph via OAuth 2.0 Client Credentials
(app-only, sin usuario interactivo -- ver Fase 1, punto 8).
"""

from __future__ import annotations

import requests

_TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"


class GraphAuthError(Exception):
    """Fallo obteniendo el access token de Microsoft Graph."""


def get_graph_token(tenant_id: str, client_id: str, client_secret: str, timeout_ms: int) -> str:
    """Solicita un access token de aplicacion (scope .default) y lo devuelve.

    El token nunca debe registrarse en logs ni excepciones.
    """
    try:
        response = requests.post(
            _TOKEN_URL_TEMPLATE.format(tenant_id=tenant_id),
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=timeout_ms / 1000,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        # No se incluye el cuerpo de la respuesta ni la excepcion original
        # sin filtrar: podrian reflejar el client_secret enviado si Entra ID
        # lo repite en un mensaje de error de validacion.
        error = GraphAuthError("No se pudo obtener el token de Microsoft Graph.")
        # Se adjunta la respuesta (si existe) para que app.services.retry
        # pueda respetar Retry-After si Entra ID responde 429.
        error.response = getattr(exc, "response", None)
        raise error from None

    return response.json()["access_token"]
