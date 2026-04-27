/**
 * Cache localStorage des compteurs tickets filtrés par période (Sunburst uniquement).
 * Pas d’expiration temporelle : les données restent jusqu’à changement de contexte (ids catégories, autre période)
 * ou rafraîchissement manuel (« Rafraîchir les compteurs ») qui relance l’API.
 *
 * Clé d’entrée : période (90d, 1y, …) + signature des ids catégories (comme la heatmap).
 *
 * Persistance via `browserLocalCache.js` (lecture/écriture du blob `entries` en une fois).
 */

import { heatmapCategoryIdsKey } from './heatmap12Cache'
import { readJson, writeJson, removeItem } from './browserLocalCache'

const STORAGE_VERSION = 1
const KEY_PREFIX = 'categorie_manager_sunburst_counts_v'

/** Nombre max d’entrées conservées (période × jeu d’ids) pour limiter la taille localStorage */
const MAX_ENTRIES = 12

/**
 * @param {string} glpiBaseUrl
 */
function storageKey(glpiBaseUrl) {
  const u = (glpiBaseUrl || '').trim().replace(/\/$/, '')
  return `${KEY_PREFIX}${STORAGE_VERSION}_${encodeURIComponent(u)}`
}

/**
 * @param {string} periodId
 * @param {string} categoryIdsKeyStr
 */
function entryKey(periodId, categoryIdsKeyStr) {
  return `${periodId}::${categoryIdsKeyStr}`
}

/**
 * @param {number[]} categoryIds
 */
export function sunburstCategoryIdsKey(categoryIds) {
  return heatmapCategoryIdsKey(categoryIds)
}

/**
 * @returns {{ counts: Record<number, number>, savedAt: string } | null}
 */
export function readSunburstCountsCache(glpiBaseUrl, periodId, categoryIdsKeyStr) {
  if (periodId === 'all' || !categoryIdsKeyStr) return null
  const parsed = readJson(storageKey(glpiBaseUrl))
  if (!parsed || parsed.schemaVersion !== STORAGE_VERSION || !parsed.entries || typeof parsed.entries !== 'object') {
    return null
  }
  const k = entryKey(periodId, categoryIdsKeyStr)
  const entry = parsed.entries[k]
  if (!entry || !entry.counts || !entry.savedAt) return null
  return {
    counts: entry.counts,
    savedAt: entry.savedAt
  }
}

/**
 * @param {Record<number, number>} counts
 */
export function writeSunburstCountsCache(glpiBaseUrl, periodId, categoryIdsKeyStr, counts) {
  if (periodId === 'all' || !categoryIdsKeyStr) return null
  const key = storageKey(glpiBaseUrl)
  /** Repartir d’un objet vide ou fusionner les entrées déjà stockées pour ne pas écraser les autres périodes/ids */
  let parsed = { schemaVersion: STORAGE_VERSION, entries: {} }
  const existing = readJson(key)
  if (existing && existing.schemaVersion === STORAGE_VERSION && existing.entries && typeof existing.entries === 'object') {
    parsed.entries = { ...existing.entries }
  }

  const savedAt = new Date().toISOString()
  const k = entryKey(periodId, categoryIdsKeyStr)
  parsed.entries[k] = { savedAt, counts }

  /** Retire les entrées les plus anciennes si dépassement */
  const keys = Object.keys(parsed.entries)
  if (keys.length > MAX_ENTRIES) {
    keys.sort((a, b) => {
      const ta = new Date(parsed.entries[a].savedAt || 0).getTime()
      const tb = new Date(parsed.entries[b].savedAt || 0).getTime()
      return ta - tb
    })
    while (Object.keys(parsed.entries).length > MAX_ENTRIES) {
      delete parsed.entries[keys.shift()]
    }
  }

  if (writeJson(key, parsed, { logLabel: 'sunburstCountsCache' })) {
    return savedAt
  }
  return null
}

export function clearSunburstCountsCache(glpiBaseUrl) {
  removeItem(storageKey(glpiBaseUrl))
}
