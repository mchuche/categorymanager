/**
 * Cache localStorage pour la heatmap « tickets résolus/fermés par groupe assigné » (12 mois glissants).
 * Clé d’invalidation : même fenêtre temporelle + même ensemble d’ids de groupes GLPI interrogés.
 *
 * Persistance via `browserLocalCache.js`.
 */

import { readJson, writeJson, removeItem } from './browserLocalCache'

const STORAGE_VERSION = 1
const KEY_PREFIX = 'categorie_manager_heatmap12_groups_v'

/**
 * @param {string} glpiBaseUrl
 */
export function heatmap12GroupsCacheKey(glpiBaseUrl) {
  const u = (glpiBaseUrl || '').trim().replace(/\/$/, '')
  return `${KEY_PREFIX}${STORAGE_VERSION}_${encodeURIComponent(u)}`
}

/**
 * Signature stable des ids de groupes (tous les groupes chargés depuis l’API pour les requêtes).
 * @param {number[]} groupIds
 */
export function heatmapGroupIdsKey(groupIds) {
  return [...groupIds]
    .map((id) => Number(id))
    .filter((id) => Number.isFinite(id) && id > 0)
    .sort((a, b) => a - b)
    .join(',')
}

/**
 * @param {string} glpiBaseUrl
 * @param {string} groupIdsKey
 * @param {string} windowKey — même convention que heatmap12 (bornes des 12 mois)
 * @returns {{ savedAt: string, matrix: object, groupIdsKey: string, windowKey: string } | null}
 */
export function readHeatmap12GroupsCache(glpiBaseUrl, groupIdsKey, windowKey) {
  const parsed = readJson(heatmap12GroupsCacheKey(glpiBaseUrl))
  if (!parsed || parsed.schemaVersion !== STORAGE_VERSION || !parsed.matrix) return null
  if (parsed.groupIdsKey !== groupIdsKey || parsed.windowKey !== windowKey) return null
  return {
    savedAt: typeof parsed.savedAt === 'string' ? parsed.savedAt : null,
    matrix: parsed.matrix,
    groupIdsKey: parsed.groupIdsKey,
    windowKey: parsed.windowKey
  }
}

/**
 * @param {object} matrix — sortie de buildGroupHeatmapMatrix
 * @returns {string|null} savedAt ISO
 */
export function writeHeatmap12GroupsCache(glpiBaseUrl, matrix, groupIdsKey, windowKey) {
  const savedAt = new Date().toISOString()
  const payload = {
    schemaVersion: STORAGE_VERSION,
    savedAt,
    groupIdsKey,
    windowKey,
    matrix
  }
  if (writeJson(heatmap12GroupsCacheKey(glpiBaseUrl), payload, { logLabel: 'heatmap12GroupsCache' })) {
    return savedAt
  }
  return null
}

export function clearHeatmap12GroupsCache(glpiBaseUrl) {
  removeItem(heatmap12GroupsCacheKey(glpiBaseUrl))
}
