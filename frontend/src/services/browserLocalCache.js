/**
 * Couche unique pour la persistance côté navigateur (API Web Storage).
 *
 * Deux magasins distincts :
 * - `localStorage` : survit aux fermetures d’onglet / redémarrages (caches métier, thème).
 * - `sessionStorage` : limité à l’onglet / session courante (auth API, préférences légères par onglet).
 *
 * Tous les modules métier passent par ces fonctions pour :
 * - éviter la duplication de try/catch et de logs ;
 * - appliquer une limite de taille sur le JSON (les chaînes JS sont en UTF-16 : `length` est une
 *   approximation pratique du « poids » ; le quota navigateur est exprimé différemment selon les
 *   implémentations, mais on évite les blobs énormes de la même façon).
 *
 * Ce n’est pas une base de données : clé → valeur (souvent une chaîne JSON).
 */

/** Limite par défaut (~4,5 Mo en caractères) pour les payloads JSON — évite de saturer le quota */
export const DEFAULT_MAX_JSON_BYTES = 4_500_000

// ---------------------------------------------------------------------------
// Implémentation partagée (localStorage et sessionStorage ont la même interface Storage)
// ---------------------------------------------------------------------------

/**
 * Lit une chaîne puis parse en JSON.
 * @param {Storage} storage
 * @param {string} key
 * @returns {any|null}
 */
function readJsonFrom(storage, key) {
  try {
    const raw = storage.getItem(key)
    if (raw == null || raw === '') return null
    return JSON.parse(raw)
  } catch (e) {
    console.warn('[browserLocalCache] readJson impossible', key, e)
    return null
  }
}

/**
 * Sérialise en JSON et enregistre si la taille reste sous le plafond.
 * @param {Storage} storage
 * @param {string} key
 * @param {any} payload — tout ce que JSON.stringify accepte
 * @param {{ maxBytes?: number, logLabel?: string }} [opts]
 */
function writeJsonTo(storage, key, payload, opts = {}) {
  const maxBytes = opts.maxBytes ?? DEFAULT_MAX_JSON_BYTES
  const label = opts.logLabel ?? key
  try {
    const str = JSON.stringify(payload)
    if (str.length > maxBytes) {
      console.warn('[browserLocalCache] volume trop important, écriture ignorée', label)
      return false
    }
    storage.setItem(key, str)
    return true
  } catch (e) {
    console.warn('[browserLocalCache] writeJson impossible', label, e)
    return false
  }
}

/**
 * @param {Storage} storage
 * @param {string} key
 */
function removeFrom(storage, key) {
  try {
    storage.removeItem(key)
  } catch (_) {
    /* quota / accès refusé : on ignore pour ne pas casser l’UI */
  }
}

/**
 * @param {Storage} storage
 * @param {string} key
 * @returns {string|null}
 */
function getStringFrom(storage, key) {
  try {
    return storage.getItem(key)
  } catch (_) {
    return null
  }
}

/**
 * @param {Storage} storage
 * @param {string} key
 * @param {string} value
 * @returns {boolean}
 */
function setStringTo(storage, key, value) {
  try {
    storage.setItem(key, value)
    return true
  } catch (_) {
    return false
  }
}

// ---------------------------------------------------------------------------
// localStorage — caches longue durée
// ---------------------------------------------------------------------------

/**
 * Lit et parse du JSON sous une clé `localStorage`.
 * @param {string} key
 * @returns {any|null} objet parsé, ou null si absent / invalide
 */
export function readJson(key) {
  return readJsonFrom(localStorage, key)
}

/**
 * Enregistre une valeur JSON sous une clé `localStorage`.
 * @param {string} key
 * @param {any} payload
 * @param {{ maxBytes?: number, logLabel?: string }} [opts]
 * @returns {boolean} true si écriture OK
 */
export function writeJson(key, payload, opts = {}) {
  return writeJsonTo(localStorage, key, payload, opts)
}

/**
 * Supprime une clé `localStorage` (invalidation, déconnexion des caches métier, etc.).
 * @param {string} key
 */
export function removeItem(key) {
  removeFrom(localStorage, key)
}

/**
 * Chaîne brute sans JSON (ex. thème « dark » / « light »).
 * @param {string} key
 * @returns {string|null}
 */
export function getString(key) {
  return getStringFrom(localStorage, key)
}

/**
 * @param {string} key
 * @param {string} value
 * @returns {boolean} false si écriture impossible (quota, mode privé strict, etc.)
 */
export function setString(key, value) {
  return setStringTo(localStorage, key, value)
}

// ---------------------------------------------------------------------------
// sessionStorage — données de session (onglet)
// ---------------------------------------------------------------------------

/**
 * Lit et parse du JSON sous une clé `sessionStorage`.
 * @param {string} key
 * @returns {any|null}
 */
export function readJsonSession(key) {
  return readJsonFrom(sessionStorage, key)
}

/**
 * Enregistre une valeur JSON sous une clé `sessionStorage`.
 * @param {string} key
 * @param {any} payload
 * @param {{ maxBytes?: number, logLabel?: string }} [opts]
 * @returns {boolean}
 */
export function writeJsonSession(key, payload, opts = {}) {
  return writeJsonTo(sessionStorage, key, payload, opts)
}

/**
 * Supprime une clé `sessionStorage`.
 * @param {string} key
 */
export function removeSessionItem(key) {
  removeFrom(sessionStorage, key)
}

/**
 * Chaîne brute en `sessionStorage` (ex. index numérique stocké en texte).
 * @param {string} key
 * @returns {string|null}
 */
export function getSessionString(key) {
  return getStringFrom(sessionStorage, key)
}

/**
 * @param {string} key
 * @param {string} value
 * @returns {boolean}
 */
export function setSessionString(key, value) {
  return setStringTo(sessionStorage, key, value)
}
