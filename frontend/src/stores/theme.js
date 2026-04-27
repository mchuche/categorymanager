import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getString, setString } from '../services/browserLocalCache'

/** Clé localStorage pour persister le choix utilisateur (survit aux rechargements). Lecture/écriture via `browserLocalCache`. */
const STORAGE_KEY = 'categorie-manager-theme'

/**
 * Applique immédiatement le thème sur <html> (attribut data-theme + color-scheme).
 * Exportée pour être réutilisée depuis main.js avant le premier rendu (évite un flash clair).
 *
 * @param {boolean} dark - true = mode sombre
 */
export function applyThemeToDocument(dark) {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
}

/**
 * Déduit le thème initial : préférence sauvegardée, sinon préférence système (prefers-color-scheme).
 * @returns {boolean}
 */
function readInitialDark() {
  const stored = getString(STORAGE_KEY)
  if (stored === 'dark') return true
  if (stored === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/**
 * Lit le thème initial et met à jour le document sans attendre Pinia (appel depuis main.js).
 */
export function initThemeBeforeApp() {
  const dark = readInitialDark()
  applyThemeToDocument(dark)
  return dark
}

/**
 * Store Pinia : mode sombre / clair, persistance et application sur document.documentElement.
 */
export const useThemeStore = defineStore('theme', () => {
  /** true = interface en mode sombre */
  const isDark = ref(false)

  /**
   * Synchronise le store avec la valeur déjà appliquée au chargement (main.js) ou relit le stockage.
   */
  function init() {
    isDark.value = readInitialDark()
    applyThemeToDocument(isDark.value)
  }

  /**
   * Bascule clair ↔ sombre et enregistre le choix.
   */
  function toggle() {
    isDark.value = !isDark.value
    setString(STORAGE_KEY, isDark.value ? 'dark' : 'light')
    applyThemeToDocument(isDark.value)
  }

  /**
   * Force un état (usage rare, tests).
   * @param {boolean} dark
   */
  function setDark(dark) {
    isDark.value = !!dark
    setString(STORAGE_KEY, isDark.value ? 'dark' : 'light')
    applyThemeToDocument(isDark.value)
  }

  return { isDark, init, toggle, setDark }
})
