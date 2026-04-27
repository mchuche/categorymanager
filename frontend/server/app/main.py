"""
API FastAPI : santé, invalidation du cache HTTP, proxy vers apirest.php avec jetons serveur.
"""

from __future__ import annotations

import os
import pathlib
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

# IMPORTANT : charger les .env *avant* `import glpi_session` (les constantes GLPI_* y sont lues une fois).
_server_dir = pathlib.Path(__file__).resolve().parent.parent
_root_dir = _server_dir.parent
# 1) server/.env — emplacement prévu pour les secrets GLPI
load_dotenv(_server_dir / ".env")
# 2) .env à la racine du dépôt — utile si tu n’as qu’un seul fichier (VITE_* + GLPI_*)
load_dotenv(_root_dir / ".env")

from .cache_store import HttpCacheStore
from . import glpi_session

app = FastAPI(title="CategorieManager API", version="0.1.0")

# CORS si le front appelle directement le port 8000 (optionnel ; en dev Vite proxy évite ce cas)
_origins = os.environ.get("CORS_ORIGINS", "http://127.0.0.1:5174,http://localhost:5174").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache_store: Optional[HttpCacheStore] = None
_http_client: Optional[httpx.AsyncClient] = None


def get_cache() -> HttpCacheStore:
    global _cache_store
    if _cache_store is None:
        _cache_store = HttpCacheStore()
    return _cache_store


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=30.0),
            verify=os.environ.get("GLPI_TLS_VERIFY", "true").lower() in ("1", "true", "yes"),
        )
    return _http_client


@app.on_event("startup")
async def startup_event() -> None:
    """Échoue tôt si les variables GLPI manquent (évite un serveur « à moitié »)."""
    glpi_session.validate_env()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global _http_client, _cache_store
    if _http_client:
        await _http_client.aclose()
        _http_client = None
    if _cache_store:
        _cache_store.close()
        _cache_store = None


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/cache/clear")
async def clear_http_cache() -> dict:
    """Vide le cache SQLite (boutons « actualiser » côté client)."""
    n = get_cache().clear_all()
    return {"cleared": True, "rows_deleted": n}


def _should_use_cache(path: str, method: str) -> bool:
    """Pas de cache pour l’ouverture / fermeture de session GLPI."""
    p = path.lower()
    if p == "initsession" or p.startswith("initsession/"):
        return False
    if p == "killsession" or p.startswith("killsession/"):
        return False
    return True


def _build_upstream_url(path: str, request: Request) -> str:
    q = str(request.url.query)
    base = f"{glpi_session.GLPI_BASE_URL}/apirest.php/{path}"
    return f"{base}?{q}" if q else base


def _ssl_error_chain(exc: BaseException) -> str:
    """Concatène le message d’erreur et ses causes pour détecter les échecs TLS."""
    parts = [str(exc)]
    c = exc.__cause__
    depth = 0
    while c is not None and depth < 8:
        parts.append(str(c))
        c = c.__cause__
        depth += 1
    return " ".join(parts)


def _request_error_detail(exc: Exception) -> str:
    """Message lisible ; si échec SSL, indique GLPI_TLS_VERIFY=false."""
    chain = _ssl_error_chain(exc).lower()
    if "certificate_verify_failed" in chain:
        return (
            "Certificat SSL non reconnu (auto-signé ou CA d’entreprise). "
            "Ajoutez dans .env (racine ou server/) : GLPI_TLS_VERIFY=false "
            "puis redémarrez uvicorn. À utiliser seulement sur intranet / lab de confiance."
        )
    return f"Erreur réseau vers GLPI : {exc!s}"


@app.api_route("/api/glpi/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_glpi(path: str, request: Request) -> Response:
    method = request.method.upper()
    if method == "OPTIONS":
        return Response(status_code=204)

    try:
        return await _proxy_glpi_impl(path, request)
    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=_request_error_detail(e)) from e


async def _proxy_glpi_impl(path: str, request: Request) -> Response:
    method = request.method.upper()
    body = await request.body()
    client = get_http_client()
    cache = get_cache()
    upstream = _build_upstream_url(path, request)

    if method == "GET" and _should_use_cache(path, method):
        key = cache.make_key(method, upstream, b"")
        hit = cache.get(key)
        if hit:
            status_code, text, content_type = hit
            ct = content_type or "application/json"
            return Response(content=text.encode("utf-8"), status_code=status_code, media_type=ct)

    if method in ("POST", "PUT", "PATCH") and _should_use_cache(path, method):
        key = cache.make_key(method, upstream, body)
        hit = cache.get(key)
        if hit:
            status_code, text, content_type = hit
            ct = content_type or "application/json"
            return Response(content=text.encode("utf-8"), status_code=status_code, media_type=ct)

    # initSession : sans Session-Token ; réponse analyse pour session_token
    path_lower = path.lower()
    is_init = path_lower == "initsession" or path_lower.startswith("initsession/")
    is_kill = path_lower == "killsession" or path_lower.startswith("killsession/")

    async def do_request(session_tok: Optional[str]) -> httpx.Response:
        headers = glpi_session.base_headers_with_session(session_tok)
        url = _build_upstream_url(path, request)
        if method == "GET":
            return await client.get(url, headers=headers)
        if method == "POST":
            return await client.post(url, headers=headers, content=body if body else None)
        if method == "PUT":
            return await client.put(url, headers=headers, content=body if body else None)
        if method == "DELETE":
            return await client.delete(url, headers=headers)
        if method == "PATCH":
            return await client.patch(url, headers=headers, content=body if body else None)
        return await client.request(method, url, headers=headers, content=body)

    if is_init:
        r = await do_request(None)
        if r.status_code < 400:
            try:
                data = r.json()
                tok = data.get("session_token")
                if tok:
                    glpi_session.set_session_token(tok)
            except Exception:
                pass
        return _finalize_response(r, method, path, upstream, body, cache, skip_store=True)

    if is_kill:
        r = await do_request(await glpi_session.ensure_session_token(client))
        glpi_session.clear_session_token()
        return _finalize_response(r, method, path, upstream, body, cache, skip_store=True)

    # Appels métier : Session-Token requis
    session_tok = await glpi_session.ensure_session_token(client)
    r = await do_request(session_tok)

    if r.status_code == 401:
        await glpi_session.refresh_session_after_401(client)
        session_tok = await glpi_session.ensure_session_token(client)
        r = await do_request(session_tok)

    return _finalize_response(r, method, path, upstream, body, cache, skip_store=False)


def _finalize_response(
    r: httpx.Response,
    method: str,
    path: str,
    upstream: str,
    body: bytes,
    cache: HttpCacheStore,
    *,
    skip_store: bool,
) -> Response:
    text = r.text
    ct = r.headers.get("content-type", "application/json")
    out = Response(content=text.encode("utf-8"), status_code=r.status_code, media_type=ct.split(";")[0].strip())

    if r.status_code >= 400 or skip_store or not _should_use_cache(path, method):
        return out

    key = cache.make_key(method, upstream, body if method != "GET" else b"")
    try:
        cache.set(key, r.status_code, text, ct.split(";")[0].strip())
    except Exception:
        pass
    return out
