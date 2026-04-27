/**
 * Paliers de période pour le Sunburst en mode Tickets uniquement (boutons ou liste).
 * Le tableau / l’arbre utilisent toujours les compteurs historiques (découplage).
 */

/** @typedef {{ id: string, shortLabel: string, hint: string }} SunburstPeriodStep */

/** @type {SunburstPeriodStep[]} */
export const SUNBURST_PERIOD_STEPS = [
  { id: 'all', shortLabel: 'Tout', hint: 'Historique complet (identique au tableau)' },
  { id: '90d', shortLabel: '90 j.', hint: 'Fenêtre glissante 90 jours' },
  { id: '6m', shortLabel: '6 mois', hint: 'Fenêtre glissante 6 mois' },
  { id: '1y', shortLabel: '1 an', hint: 'Fenêtre glissante 1 an' },
  { id: '2y', shortLabel: '2 ans', hint: 'Fenêtre glissante 2 ans' },
  { id: '3y', shortLabel: '3 ans', hint: 'Fenêtre glissante 3 ans' }
]

/**
 * @param {number} index — index du palier (0 à SUNBURST_PERIOD_STEPS.length - 1)
 * @returns {string} id de période (ex. 'all', '90d')
 */
export function sunburstPeriodIdFromIndex(index) {
  const i = Number(index)
  if (!Number.isFinite(i) || i < 0 || i >= SUNBURST_PERIOD_STEPS.length) {
    return 'all'
  }
  return SUNBURST_PERIOD_STEPS[i].id
}
