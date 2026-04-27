/**
 * Mémorisation de l’index du curseur « période Sunburst » (sessionStorage, par URL GLPI).
 * Les compteurs filtrés ne sont pas stockés ici — seulement la préférence utilisateur.
 *
 * Accès disque : `browserLocalCache.js` (variantes `*Session*` pour sessionStorage).
 */

import { getSessionString, setSessionString, removeSessionItem } from './browserLocalCache'

const KEY_PREFIX = 'categorie_manager_sunburst_period_idx_v1_'

/**
 * @param {string} glpiBaseUrl
 */
export function sunburstPeriodIndexStorageKey(glpiBaseUrl) {
  const u = (glpiBaseUrl || '').trim().replace(/\/$/, '')
  return `${KEY_PREFIX}${encodeURIComponent(u)}`
}

/**
 * @param {string} glpiBaseUrl
 * @returns {number|null} index valide ou null
 */
export function readSunburstPeriodIndex(glpiBaseUrl) {
  const raw = getSessionString(sunburstPeriodIndexStorageKey(glpiBaseUrl))
  if (raw == null || raw === '') return null
  const n = Number.parseInt(raw, 10)
  return Number.isFinite(n) ? n : null
}

/**
 * @param {string} glpiBaseUrl
 * @param {number} index
 */
export function writeSunburstPeriodIndex(glpiBaseUrl, index) {
  setSessionString(sunburstPeriodIndexStorageKey(glpiBaseUrl), String(index))
}

export function clearSunburstPeriodIndexStorage(glpiBaseUrl) {
  removeSessionItem(sunburstPeriodIndexStorageKey(glpiBaseUrl))
}
