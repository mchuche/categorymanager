/**
 * Traductions CategoryManager injectées par PHP ({@see PluginCategorymanagerI18n})
 * dans window.__CM_I18N__ selon la langue GLPI active.
 */

/**
 * Chaîne traduite pour une clé stable (fallback : clé affichée).
 *
 * @param {string} key
 * @returns {string}
 */
export function cmT(key) {
  const d =
    typeof window !== 'undefined' &&
    window.__CM_I18N__ &&
    typeof window.__CM_I18N__ === 'object'
      ? window.__CM_I18N__
      : {}
  const v = d[key]
  return typeof v === 'string' && v !== '' ? v : key
}

/**
 * Chaîne gettext avec placeholders %s (substitution gauche à droite).
 *
 * @param {string} key
 * @param {...string} replacements
 * @returns {string}
 */
export function cmTf(key, ...replacements) {
  let s = cmT(key)
  for (const r of replacements) {
    s = s.replace('%s', String(r))
  }
  return s
}
