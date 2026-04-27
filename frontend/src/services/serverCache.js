/**
 * Invalidation du cache HTTP côté backend (SQLite), distinct du cache navigateur.
 * Appelé lors des actions « actualiser » pour forcer de nouveaux allers-retours GLPI.
 */

/**
 * Vide le cache SQLite du serveur FastAPI.
 * @returns {Promise<boolean>} true si la requête a réussi
 */
export async function clearServerHttpCache() {
  try {
    // Plugin GLPI : no-op côté PHP ; dev : cache SQLite FastAPI
    const url =
      typeof window !== 'undefined' && window.__CM_PLUGIN_WEB__
        ? `${String(window.__CM_PLUGIN_WEB__).replace(/\/?$/, '')}/ajax/cache_clear.php`
        : '/api/cache/clear'
    const r = await fetch(url, { method: 'POST' })
    return r.ok
  } catch (e) {
    console.warn('[serverCache] clearServerHttpCache:', e)
    return false
  }
}
