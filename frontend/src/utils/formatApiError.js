/**
 * Message lisible à partir d’une erreur Axios / fetch.
 * - FastAPI : souvent `{ detail: "..." }`.
 * - Plugin GLPI CategoryManager (`ajax/native.php`) : `{ ok: false, error: "..." }`.
 * @param {unknown} error
 * @returns {string}
 */
export function formatApiError(error) {
  const res = error && typeof error === 'object' && 'response' in error ? error.response : null
  const data = res && typeof res === 'object' && 'data' in res ? res.data : null
  const status = res && typeof res === 'object' && 'status' in res ? res.status : null

  if (data != null) {
    if (typeof data === 'string') return data.trim() || `HTTP ${status ?? '?'}`
    if (typeof data === 'object' && data !== null) {
      // JSON du ErrorController GLPI (Symfony) : error = true, title + message souvent génériques, trace si mode debug.
      if (data.error === true) {
        const title =
          typeof data.title === 'string' && data.title.trim() !== '' ? data.title.trim() : 'Erreur GLPI'
        const msg =
          typeof data.message === 'string' && data.message.trim() !== '' ? data.message.trim() : ''
        const trace =
          typeof data.trace === 'string' && data.trace.trim() !== '' ? `\n${data.trace.trim()}` : ''
        if (msg !== '') {
          return `${title} — ${msg}${trace}`
        }
        return `${title}${trace}`.trim() || `HTTP ${status ?? '?'}`
      }
      // Réponses JSON du visualiseur (native.php) : { ok: false, error: "…" } — "error" est une chaîne ici.
      if (typeof data.error === 'string' && data.error.trim() !== '') {
        return data.error.trim()
      }
      if (typeof data.message === 'string' && data.message.trim() !== '') {
        return data.message.trim()
      }
      if (typeof data.detail === 'string') return data.detail
      if (Array.isArray(data.detail)) {
        return data.detail
          .map((x) => (x && typeof x === 'object' && 'msg' in x ? x.msg : String(x)))
          .join('; ')
      }
    }
  }
  if (status != null) {
    const msg = error && typeof error === 'object' && 'message' in error ? error.message : ''
    return `HTTP ${status}${msg ? ` — ${msg}` : ''}`
  }
  if (error instanceof Error) return error.message
  return String(error ?? 'erreur inconnue')
}
