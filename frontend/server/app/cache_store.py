"""
Persistance du cache HTTP (réponses JSON renvoyées par le proxy GLPI).
Invalidation : uniquement via POST /api/cache/clear (manuel), pas d’expiration TTL.
"""

import hashlib
import sqlite3
import threading
from pathlib import Path
from typing import Optional, Tuple

_lock = threading.Lock()


def _default_db_path() -> Path:
    """Répertoire `server/data/` créé si besoin."""
    base = Path(__file__).resolve().parent.parent / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base / "http_cache.sqlite3"


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS http_cache (
            cache_key TEXT PRIMARY KEY,
            status_code INTEGER NOT NULL,
            body TEXT NOT NULL,
            content_type TEXT
        )
        """
    )
    conn.commit()
    return conn


class HttpCacheStore:
    """Accès thread-safe au fichier SQLite."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._path = db_path or _default_db_path()
        with _lock:
            self._conn = _connect(self._path)

    def close(self) -> None:
        with _lock:
            self._conn.close()

    @staticmethod
    def make_key(method: str, url: str, body: bytes) -> str:
        """Clé stable : méthode + URL complète + hash du corps (POST)."""
        h = hashlib.sha256()
        h.update(method.upper().encode())
        h.update(b"\n")
        h.update(url.encode())
        h.update(b"\n")
        h.update(body or b"")
        return h.hexdigest()

    def get(self, cache_key: str) -> Optional[Tuple[int, str, Optional[str]]]:
        with _lock:
            cur = self._conn.execute(
                "SELECT status_code, body, content_type FROM http_cache WHERE cache_key = ?",
                (cache_key,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return int(row[0]), str(row[1]), row[2]

    def set(self, cache_key: str, status_code: int, body: str, content_type: Optional[str]) -> None:
        with _lock:
            self._conn.execute(
                """
                INSERT INTO http_cache (cache_key, status_code, body, content_type)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                  status_code = excluded.status_code,
                  body = excluded.body,
                  content_type = excluded.content_type
                """,
                (cache_key, status_code, body, content_type),
            )
            self._conn.commit()

    def clear_all(self) -> int:
        """Retourne le nombre de lignes supprimées (approximatif)."""
        with _lock:
            cur = self._conn.execute("DELETE FROM http_cache")
            self._conn.commit()
            return cur.rowcount if cur.rowcount is not None else 0
