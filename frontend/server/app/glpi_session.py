"""
Session GLPI côté serveur : initSession une fois, Session-Token réutilisé pour les appels suivants.
killSession vide le jeton en mémoire ; une 401 sur un appel déclenche un nouvel initSession.
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx
from fastapi import HTTPException

GLPI_BASE_URL = os.environ.get("GLPI_BASE_URL", "").rstrip("/")
GLPI_APP_TOKEN = os.environ.get("GLPI_APP_TOKEN", "")
GLPI_USER_TOKEN = os.environ.get("GLPI_USER_TOKEN", "")

_session_token: Optional[str] = None
_lock = asyncio.Lock()


def validate_env() -> None:
    if not GLPI_BASE_URL or not GLPI_APP_TOKEN or not GLPI_USER_TOKEN:
        raise RuntimeError(
            "Variables manquantes : GLPI_BASE_URL, GLPI_APP_TOKEN, GLPI_USER_TOKEN "
            "(fichier server/.env ou environnement)"
        )


def base_headers_with_session(session_token: Optional[str] = None) -> dict[str, str]:
    h: dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": f"user_token {GLPI_USER_TOKEN}",
        "App-Token": GLPI_APP_TOKEN,
    }
    if session_token:
        h["Session-Token"] = session_token
    return h


def clear_session_token() -> None:
    global _session_token
    _session_token = None


def set_session_token(token: str) -> None:
    """Après initSession proxifié : mémorise le jeton pour les appels suivants."""
    global _session_token
    _session_token = token


async def fetch_init_session(client: httpx.AsyncClient) -> str:
    """Appelle initSession et mémorise le session_token."""
    global _session_token
    url = f"{GLPI_BASE_URL}/apirest.php/initSession"
    try:
        r = await client.get(url, headers=base_headers_with_session(None))
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Connexion à GLPI impossible ({GLPI_BASE_URL}) : {e!s}",
        ) from e

    if r.status_code >= 400:
        # Remonter le code et le corps GLPI au lieu d’un 500 FastAPI opaque
        raise HTTPException(status_code=r.status_code, detail=r.text[:8000])

    try:
        data = r.json()
    except Exception:
        raise HTTPException(
            status_code=502,
            detail=f"Réponse initSession non-JSON : {r.text[:2000]}",
        )

    tok = data.get("session_token")
    if not tok:
        raise HTTPException(
            status_code=502,
            detail="Réponse initSession sans session_token (vérifiez App-Token / User-Token).",
        )
    _session_token = tok
    return tok


async def ensure_session_token(client: httpx.AsyncClient) -> str:
    """Retourne un Session-Token valide (init si besoin)."""
    global _session_token
    if _session_token:
        return _session_token
    async with _lock:
        if _session_token:
            return _session_token
        await fetch_init_session(client)
        assert _session_token
        return _session_token


async def refresh_session_after_401(client: httpx.AsyncClient) -> str:
    """Invalide la session et en obtient une nouvelle (après 401 GLPI)."""
    global _session_token
    async with _lock:
        _session_token = None
        await fetch_init_session(client)
        assert _session_token
        return _session_token
