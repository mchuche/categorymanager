import { defineStore } from 'pinia'

/**
 * Clé stable pour les caches localStorage (même valeur que VITE_GLPI_PUBLIC_BASE_URL sans slash final).
 * En mode plugin GLPI, les caches sont isolés par instance via cette clé (« default » si non définie).
 */
export function getInstanceCacheKey() {
  return (import.meta.env.VITE_GLPI_PUBLIC_BASE_URL || 'default').replace(/\/$/, '')
}

/**
 * Store minimal : fournit l’identifiant d’instance pour les caches navigateur (catégories, heatmaps, etc.).
 * L’authentification est gérée par la session GLPI (plugin) ou FastAPI (dev).
 */
export const useAuthStore = defineStore('auth', () => {
  function getApiUrl() {
    return getInstanceCacheKey()
  }

  return {
    getApiUrl,
  }
})
