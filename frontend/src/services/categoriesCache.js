/**
 * Cache persistant des catégories ITIL + compteurs (localStorage), indexé par URL GLPI.
 * Objectif : afficher tout de suite une vue exploitable au rechargement, puis rafraîchir via l’API.
 * Les jetons API ne sont jamais stockés ici — uniquement les données métier déjà affichées.
 *
 * Accès disque centralisé : `browserLocalCache.js`.
 */

import { readJson, writeJson, removeItem } from './browserLocalCache'

const STORAGE_VERSION = 1
const KEY_PREFIX = 'categorie_manager_dashboard_v'

/**
 * Clé stable pour une instance GLPI (normalisation du chemin d’URL).
 * @param {string} glpiBaseUrl — retour de useAuthStore().getApiUrl()
 */
export function categoriesCacheKey(glpiBaseUrl) {
  const u = (glpiBaseUrl || '').trim().replace(/\/$/, '')
  return `${KEY_PREFIX}${STORAGE_VERSION}_${encodeURIComponent(u)}`
}

/**
 * @returns {{ savedAt: string, categories: Array<Object> } | null}
 */
export function readCategoriesCache(glpiBaseUrl) {
  const parsed = readJson(categoriesCacheKey(glpiBaseUrl))
  if (!parsed || parsed.schemaVersion !== STORAGE_VERSION || !Array.isArray(parsed.categories)) {
    return null
  }
  return {
    savedAt: typeof parsed.savedAt === 'string' ? parsed.savedAt : null,
    categories: parsed.categories
  }
}

/**
 * Sérialise la liste courante (champs nécessaires à l’UI : ids, noms, parents, compteurs, niveaux).
 * @returns {string|null} horodatage ISO enregistré, ou null si échec
 */
export function writeCategoriesCache(glpiBaseUrl, categories) {
  const savedAt = new Date().toISOString()
  const payload = {
    schemaVersion: STORAGE_VERSION,
    savedAt,
    categories: categories.map((c) => ({
      id: c.id,
      name: c.name,
      itilcategories_id: c.itilcategories_id,
      ticketCount: c.ticketCount,
      totalTicketCount: c.totalTicketCount,
      level: c.level
    }))
  }
  if (writeJson(categoriesCacheKey(glpiBaseUrl), payload, { logLabel: 'categoriesCache' })) {
    return savedAt
  }
  return null
}

/** Supprime le cache pour cette instance (déconnexion). */
export function clearCategoriesCache(glpiBaseUrl) {
  removeItem(categoriesCacheKey(glpiBaseUrl))
}

/**
 * Durée après laquelle on affiche un rappel « mise à jour recommandée » (ms).
 * Ici : 30 jours ≈ 1 mois — pas avant.
 */
export const CACHE_STALE_AFTER_MS = 30 * 24 * 60 * 60 * 1000
