/**
 * Cache persistant (localStorage) de la matrice « 12 mois glissants » par instance GLPI.
 * Invalidation : même clé de fenêtre temporelle (bornes des 12 mois) + même ensemble d’ids catégories.
 * Les jetons API ne sont jamais stockés ici.
 *
 * Persistance via `browserLocalCache.js`.
 */

import { readJson, writeJson, removeItem } from './browserLocalCache'

const STORAGE_VERSION = 1
const KEY_PREFIX = 'categorie_manager_heatmap12_v'

/**
 * @param {string} glpiBaseUrl
 */
export function heatmap12CacheKey(glpiBaseUrl) {
  const u = (glpiBaseUrl || '').trim().replace(/\/$/, '')
  return `${KEY_PREFIX}${STORAGE_VERSION}_${encodeURIComponent(u)}`
}

/**
 * Signature des plages mensuelles (dépend de « maintenant » — change au fil des mois / jours).
 * @param {Array<{ startStr: string, endStr: string }>} monthRanges
 */
export function heatmapWindowKey(monthRanges) {
  if (!monthRanges?.length) return ''
  return monthRanges.map((m) => `${m.startStr}|${m.endStr}`).join(';;')
}

/**
 * @param {Array<number|string>} categoryIds
 */
export function heatmapCategoryIdsKey(categoryIds) {
  return [...categoryIds]
    .map((id) => Number(id))
    .sort((a, b) => a - b)
    .join(',')
}

/**
 * @returns {{ savedAt: string, matrix: object, categoryIdsKey: string, windowKey: string } | null}
 */
export function readHeatmap12Cache(glpiBaseUrl, categoryIdsKey, windowKey) {
  const parsed = readJson(heatmap12CacheKey(glpiBaseUrl))
  if (!parsed || parsed.schemaVersion !== STORAGE_VERSION || !parsed.matrix) return null
  if (parsed.categoryIdsKey !== categoryIdsKey || parsed.windowKey !== windowKey) return null
  return {
    savedAt: typeof parsed.savedAt === 'string' ? parsed.savedAt : null,
    matrix: parsed.matrix,
    categoryIdsKey: parsed.categoryIdsKey,
    windowKey: parsed.windowKey
  }
}

/**
 * @param {object} matrix — sortie de buildRootBranchMatrix (sérialisable JSON)
 * @returns {string|null} savedAt ISO
 */
export function writeHeatmap12Cache(glpiBaseUrl, matrix, categoryIdsKey, windowKey) {
  const savedAt = new Date().toISOString()
  const payload = {
    schemaVersion: STORAGE_VERSION,
    savedAt,
    categoryIdsKey,
    windowKey,
    matrix
  }
  if (writeJson(heatmap12CacheKey(glpiBaseUrl), payload, { logLabel: 'heatmap12Cache' })) {
    return savedAt
  }
  return null
}

export function clearHeatmap12Cache(glpiBaseUrl) {
  removeItem(heatmap12CacheKey(glpiBaseUrl))
}

/* Aucun rafraîchissement automatique : la mise à jour des 12 mois est uniquement manuelle (bouton dashboard). */
