/**
 * Ordre des paliers Sunburst « Tickets » (IDs stables ; libellés via gettext côté PHP → window.__CM_I18N__).
 */

/** @typedef {{ id: string, shortLabel: string, hint: string }} SunburstPeriodStep */

/** Identifiants dans l’ordre affiché (boutons chips). */
export const SUNBURST_PERIOD_IDS = ['all', '90d', '6m', '1y', '2y', '3y']

/**
 * @param {number} index — index du palier (0 à SUNBURST_PERIOD_IDS.length - 1)
 * @returns {string} id de période (ex. 'all', '90d')
 */
export function sunburstPeriodIdFromIndex(index) {
  const i = Number(index)
  if (!Number.isFinite(i) || i < 0 || i >= SUNBURST_PERIOD_IDS.length) {
    return 'all'
  }
  return SUNBURST_PERIOD_IDS[i]
}
