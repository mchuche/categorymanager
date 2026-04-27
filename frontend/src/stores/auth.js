import { defineStore } from 'pinia'
import { computed } from 'vue'

/**
 * Clé stable pour les caches localStorage (même valeur que VITE_GLPI_PUBLIC_BASE_URL sans slash final).
 * Doit correspondre à l’instance GLPI documentée côté serveur (une URL publique, pas un secret).
 */
export function getInstanceCacheKey() {
  return (import.meta.env.VITE_GLPI_PUBLIC_BASE_URL || 'default').replace(/\/$/, '')
}

/**
 * État minimal : plus de jetons GLPI dans le navigateur (gérés par le backend FastAPI).
 * isAuthenticated reste true pour les écrans protégés par le réseau (intranet).
 */
export const useAuthStore = defineStore('auth', () => {
  const isAuthenticated = computed(() => true)

  function getApiUrl() {
    return getInstanceCacheKey()
  }

  /**
   * Ferme la session GLPI côté serveur et vide les caches locaux (appelant Dashboard).
   */
  async function logout() {
    try {
      // Plugin natif : pas de session REST à fermer
      if (typeof window !== 'undefined' && window.__CM_NATIVE_API__) {
        return
      }
      await fetch('/api/glpi/killSession', { method: 'GET' })
    } catch (_) {
      /* ignore */
    }
  }

  return {
    isAuthenticated,
    getApiUrl,
    logout
  }
})
